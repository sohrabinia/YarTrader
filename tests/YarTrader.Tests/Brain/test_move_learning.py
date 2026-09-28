from datetime import datetime, timedelta

from src.Research.Brain.models import MarketObservation
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.discovery import PatternDiscoveryEngine


def _upward_observations(count=28):
    start = datetime(2026, 1, 1)
    rows = []
    price = 2000.0
    for i in range(count):
        close = price + 2.5
        rows.append(
            MarketObservation(
                symbol="XAUUSD",
                timeframe="H1",
                timestamp=start + timedelta(hours=i),
                high=close + 1.0,
                low=price - 0.5,
                open_price=price,
                close_price=close,
                volume=100.0,
                meta={"provider": "ControlledOfflineFixture"},
            )
        )
        price = close
    return rows


def test_research_learning_continues_after_minimum_target():
    sim = SimulationBrain("XAUUSD", "H1", spread_points=0.0, slippage_points=0.0,
                           commission_points=0.0, learning_horizon_candles=4)
    trade = sim.make_virtual_decision(
        action="BUY",
        entry_price=2000.0,
        timestamp=datetime(2026, 1, 1),
        stop_offset=100.0,
        target_offset=2.0,
    )
    assert trade is not None

    closed = []
    for obs in _upward_observations(5):
        closed.extend(sim.update_active_trades(obs))

    assert closed
    result = closed[-1]
    assert result.final_result == "WINDOW_COMPLETE"
    assert result.target_reached is True
    assert result.max_favorable_movement > 2.0
    assert result.learning_outcome["target_reached"] is True


def test_behavior_profile_uses_raw_price_action_without_regime_labels():
    engine = PatternDiscoveryEngine()
    profile = engine.extract_behavior_profile(_upward_observations(12))
    assert profile
    assert "directional_efficiency" in profile
    assert "range_expansion" in profile
    assert "reversal_frequency" in profile
    assert not any(key in profile for key in ("trend", "range", "spike"))
