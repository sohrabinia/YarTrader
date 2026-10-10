from datetime import datetime, timedelta
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import MarketEvent


def test_raw_market_reaction_is_not_mislabeled_as_trade_success_or_failure(tmp_path):
    memory = MarketMemorySystem(storage_dir=str(tmp_path))
    event = MarketEvent(
        symbol="XAUUSD", timeframe="M15",
        start_time=datetime(2026, 1, 1, 10, 0),
        end_time=datetime(2026, 1, 1, 10, 15),
        price_change=5.0, duration_candles=3, previous_sequence_len=5,
        reaction_type="extension", reaction_magnitude=1.5,
        meta={"direction": "upward", "sequence_signature": [0.1, 0.2, 0.3]},
    )
    memory.add_event(event)
    promoted = memory.promote_raw_events_to_experiences("XAUUSD", "M15")
    assert len(promoted) == 1
    assert promoted[0].outcome_result == "UNLABELED"
    assert promoted[0].meta["is_observed_event_only"] is True
    assert promoted[0].meta["predicted_action"] is None
    assert memory.promote_experiences_to_patterns() == []
    assert memory.get_learning_statistics()["patterns_created"] == 0


def test_raw_event_with_explicit_resolved_decision_keeps_explicit_label(tmp_path):
    memory = MarketMemorySystem(storage_dir=str(tmp_path))
    event = MarketEvent(
        symbol="XAUUSD", timeframe="M15",
        start_time=datetime(2026, 1, 1, 10, 0),
        end_time=datetime(2026, 1, 1, 10, 15),
        price_change=5.0, duration_candles=3, previous_sequence_len=5,
        reaction_type="extension", reaction_magnitude=1.5,
        meta={"decision_action": "BUY", "predicted_action": "BUY", "outcome_result": "SUCCESS",
              "sequence_signature": [0.1, 0.2, 0.3]},
    )
    memory.add_event(event)
    promoted = memory.promote_raw_events_to_experiences("XAUUSD", "M15")
    assert promoted[0].outcome_result == "SUCCESS"
    assert promoted[0].meta["is_observed_event_only"] is False
