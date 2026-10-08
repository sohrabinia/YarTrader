from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.Research.Brain.brain_context import PointInTimeContextCache
from src.Research.Brain.models import MarketEvent, MarketObservation
from src.Research.Brain.memory import MarketMemorySystem


def _observation(i: int) -> MarketObservation:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
    price = 2000.0 + i
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=ts,
        open_price=price,
        high=price + 1.0,
        low=price - 1.0,
        close_price=price + 0.5,
        volume=100.0,
    )


def _event(i: int) -> MarketEvent:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
    end = start + timedelta(minutes=1)
    return MarketEvent(
        symbol="XAUUSD",
        timeframe="H1",
        start_time=start,
        end_time=end,
        price_change=0.5,
        duration_candles=1,
        previous_sequence_len=i,
        reaction_type="extension",
        reaction_magnitude=0.25,
        meta={"sequence_signature": [0.5, 0.25]},
    )


def test_context_window_comparison_250_vs_500_is_bounded_and_point_in_time():
    observations = [_observation(i) for i in range(600)]
    decision_time = observations[-1].timestamp

    cache_250 = PointInTimeContextCache(max_per_scope=250)
    cache_500 = PointInTimeContextCache(max_per_scope=500)
    for observation in observations:
        cache_250.add(observation)
        cache_500.add(observation)

    snap_250 = cache_250.snapshot_symbol("XAUUSD", decision_time)["H1"]
    snap_500 = cache_500.snapshot_symbol("XAUUSD", decision_time)["H1"]

    assert len(snap_250) == 250
    assert len(snap_500) == 500
    assert [o.timestamp for o in snap_250] == [o.timestamp for o in snap_500[-250:]]
    assert snap_250[-1].timestamp == decision_time

    future = _observation(601)
    cache_250.add(future)
    earlier_snapshot = cache_250.snapshot_symbol("XAUUSD", decision_time)["H1"]
    assert all(o.timestamp <= decision_time for o in earlier_snapshot)


def test_learning_persistence_batches_without_truncating_raw_history(tmp_path: Path):
    memory = MarketMemorySystem(storage_dir=str(tmp_path / "memory"))
    memory._artifact_store.put = lambda *args, **kwargs: {"id": "test-artifact"}
    saves = []
    original_save = memory._save_layer

    def counted_save(layer):
        saves.append(layer)
        original_save(layer)

    memory._save_layer = counted_save
    memory.configure_event_persistence(save_every=250)

    for i in range(300):
        memory.add_event(_event(i))

    assert len(memory.events) == 300
    assert saves.count("events") == 1

    memory.flush_event_persistence()
    assert saves.count("events") == 2

    restored = MarketMemorySystem(storage_dir=str(tmp_path / "memory"))
    restored._artifact_store.put = lambda *args, **kwargs: {"id": "test-artifact"}
    assert len(restored.get_events()) == 300
    timestamps = [event.start_time for event in restored.get_events()]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] < timestamps[-1]
