import os
from datetime import datetime, timedelta
from src.Research.Brain.models import MarketObservation, MarketEvent
from src.Research.Brain.cognitive_loop import CognitiveReplayLoop
from src.Research.Brain.memory import MarketMemorySystem


def _observations(count=12):
    start = datetime(2026, 1, 1, 0, 0, 0)
    rows = []
    price = 2000.0
    for i in range(count):
        open_price = price
        close_price = price + (1.5 if i % 2 == 0 else -0.8)
        rows.append(
            MarketObservation(
                symbol="XAUUSD",
                timeframe="H1",
                timestamp=start + timedelta(hours=i),
                high=max(open_price, close_price) + 1.0,
                low=min(open_price, close_price) - 1.0,
                open_price=open_price,
                close_price=close_price,
                volume=100.0 + i,
                meta={"provider": "ControlledOfflineFixture"},
            )
        )
        price = close_price
    return rows


def test_live_cognitive_step_is_incremental_and_read_only(tmp_path):
    memory = MarketMemorySystem(storage_dir=str(tmp_path / "brain_memory"))
    observations = _observations()

    loop = CognitiveReplayLoop(
        symbol="XAUUSD",
        timeframe="H1",
        observations=observations,
        memory_system=memory,
    )

    first = loop.process_live_observation(observations)
    assert first is not None
    assert first.market_context["live_mode"] is True
    assert first.market_context["future_data_visible_at_decision"] is False
    assert len(memory.get_events()) > 0

    # Replaying the same candle must be idempotent.
    second = loop.process_live_observation(observations)
    assert second is None
    assert len(memory.get_events()) > 0

    # The cognitive loop only creates VirtualTrade records; it has no broker adapter.
    assert hasattr(loop.simulation_brain, "active_trades")
    assert not hasattr(loop.simulation_brain, "order_send")


def test_brain_event_memory_persists_and_scopes_deduplication_by_symbol(tmp_path):
    storage = str(tmp_path / "brain_memory")
    memory = MarketMemorySystem(storage_dir=storage)
    start = datetime(2026, 1, 1, 0, 0, 0)
    event_a = MarketEvent(
        symbol="XAUUSD", timeframe="H1", start_time=start, end_time=start + timedelta(hours=1),
        price_change=2.0, duration_candles=1, previous_sequence_len=3,
        reaction_type="extension", reaction_magnitude=1.0
    )
    event_b = MarketEvent(
        symbol="EURUSD", timeframe="H1", start_time=start, end_time=start + timedelta(hours=1),
        price_change=0.002, duration_candles=1, previous_sequence_len=3,
        reaction_type="extension", reaction_magnitude=0.001
    )
    memory.add_event(event_a)
    memory.add_event(event_a)
    memory.add_event(event_b)
    reloaded = MarketMemorySystem(storage_dir=storage)
    assert len(reloaded.get_events()) == 2
    assert reloaded.get_learning_statistics()["events_total"] == 2


def test_research_runtime_does_not_invoke_shadow_trading():
    """ResearchRuntime.run_once must not contain a Shadow execution call path."""
    import inspect
    from src.Application.Runtime.research_runtime import ResearchRuntime

    source = inspect.getsource(ResearchRuntime.run_once)
    assert "ShadowTradingEngine" not in source
    assert "handle_decision(" not in source
    assert "update_market_price(" not in source


def test_live_brain_exposes_pre_move_anticipation_state(tmp_path):
    """The canonical Brain must expose a pre-move state without execution authority."""
    observations = _observations()
    memory = MarketMemorySystem(storage_dir=str(tmp_path / "brain_memory"))
    loop = CognitiveReplayLoop(
        symbol="XAUUSD",
        timeframe="H1",
        observations=observations,
        memory_system=memory,
    )

    episode = loop.process_live_observation(observations)
    assert episode is not None
    hypothesis = episode.brain_hypothesis or {}
    anticipation = hypothesis.get("meta", {}).get("anticipation", {})
    assert anticipation.get("state") in {"PRE_MOVE", "NO_EDGE"}
    assert anticipation.get("future_data_visible_at_decision") is False
    assert anticipation.get("execution_trigger") == "NEXT_VALID_MARKET_TRIGGER"


def test_research_runtime_uses_brain_as_direction_authority():
    """Execution intelligence may enrich prices, but cannot replace Brain direction."""
    import inspect
    from src.Application.Runtime.research_runtime import ResearchRuntime

    source = inspect.getsource(ResearchRuntime.run_once)
    assert "CANONICAL_BRAIN" in source
    assert "brain_hypothesis.get(\"expected_direction\"" in source
    assert 'action = str(plan.get("action", "WAIT"))' not in source
