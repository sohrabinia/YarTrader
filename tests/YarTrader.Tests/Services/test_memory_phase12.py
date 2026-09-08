import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Memory.memory_engine import MemoryRecord, MemoryStore
from src.Application.Services.memory_service import MemoryService
from src.Application.Services.learning_service import LearningService
from src.Application.Backtest.backtest_engine import BacktestEngine, BacktestStrategyType
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException


def generate_candle_series(count: int, start_price: float = 2300.0, trend: float = 0.5) -> list[MarketDataPoint]:
    base_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    for i in range(count):
        ts = base_time + timedelta(minutes=15 * i)
        c_open = start_price + i * trend
        c_high = c_open + 2.0
        c_low = c_open - 1.0
        c_close = c_open + 1.5
        candles.append(
            MarketDataPoint(
                AssetId="XAUUSD",
                Timestamp=ts,
                Open=c_open,
                High=c_high,
                Low=c_low,
                Close=c_close,
                Volume=100.0
            )
        )
    return candles


# 1. MemoryRecord validation
def test_1_memory_record_validation():
    rec = MemoryRecord(
        id="mem-1",
        timestamp=datetime.now(timezone.utc),
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_type="LEARNING_INSIGHT",
        metrics={"obs_count": 50},
        confidence=0.85
    )
    rec.validate()
    assert rec.id == "mem-1"
    assert rec.source_phase == "PHASE_11_LEARNING"


# 2. Immutable record behavior
def test_2_immutable_record_behavior():
    rec = MemoryRecord(
        id="mem-1",
        timestamp=datetime.now(timezone.utc),
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_type="LEARNING_INSIGHT",
        metrics={"obs_count": 50},
        confidence=0.85
    )
    with pytest.raises(AttributeError):
        rec.symbol = "BTCUSD"


# 3. UTC timestamp validation
def test_3_utc_timestamp_validation():
    naive_ts = datetime.now()
    rec = MemoryRecord(
        id="mem-1",
        timestamp=naive_ts,
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_type="LEARNING_INSIGHT",
        metrics={},
        confidence=0.85
    )
    with pytest.raises(ValidationException, match="must be in UTC timezone"):
        rec.validate()


# 4. MemoryStore add/retrieve
def test_4_store_add_retrieve():
    store = MemoryStore()
    rec = MemoryRecord(
        id="mem-1",
        timestamp=datetime.now(timezone.utc),
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_type="LEARNING_INSIGHT",
        metrics={},
        confidence=0.8
    )
    store.add_record(rec)
    assert store.count() == 1
    assert store.get_records()[0].id == "mem-1"


# 5. Symbol filtering
def test_5_symbol_filtering():
    store = MemoryStore()
    ts = datetime.now(timezone.utc)
    r1 = MemoryRecord("m1", ts, "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    r2 = MemoryRecord("m2", ts, "BTCUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    store.add_record(r1)
    store.add_record(r2)

    xau_recs = store.get_records(symbol="XAUUSD")
    assert len(xau_recs) == 1
    assert xau_recs[0].symbol == "XAUUSD"


# 6. Strategy filtering
def test_6_strategy_filtering():
    store = MemoryStore()
    ts = datetime.now(timezone.utc)
    r1 = MemoryRecord("m1", ts, "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    r2 = MemoryRecord("m2", ts, "XAUUSD", "M15", "SPIKE", "INSIGHT", {}, 0.8)
    store.add_record(r1)
    store.add_record(r2)

    spike_recs = store.get_records(strategy_type="SPIKE")
    assert len(spike_recs) == 1
    assert spike_recs[0].strategy_type == "SPIKE"


# 7. Date filtering
def test_7_date_filtering():
    store = MemoryStore()
    base_ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    r1 = MemoryRecord("m1", base_ts, "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    r2 = MemoryRecord("m2", base_ts + timedelta(days=2), "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    store.add_record(r1)
    store.add_record(r2)

    start_filter = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    filtered = store.get_records(start_time=start_filter)
    assert len(filtered) == 1
    assert filtered[0].id == "m2"


# 8. LearningService integration
def test_8_learning_service_integration():
    svc = MemoryService()
    res = svc.record_learning_insight(symbol="XAUUSD", interval="M15", strategy="TREND", limit=40)
    assert res["symbol"] == "XAUUSD"
    assert res["strategy_type"] == "TREND"
    assert res["source_phase"] == "PHASE_11_LEARNING"


# 9. Deterministic output repeatability
def test_9_deterministic_output_repeatability():
    store = MemoryStore()
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    r1 = MemoryRecord("m1", ts, "XAUUSD", "M15", "TREND", "INSIGHT", {"a": 1}, 0.8)
    store.add_record(r1)

    out1 = [r.to_dict() for r in store.get_records()]
    out2 = [r.to_dict() for r in store.get_records()]
    assert out1 == out2


# 10. Empty memory handling
def test_10_empty_memory_handling():
    svc = MemoryService()
    res = svc.get_historical_memory(symbol="NON_EXISTENT")
    assert res["total_records"] == 0
    assert res["records"] == []


# 11. Invalid data rejection
def test_11_invalid_data_rejection():
    store = MemoryStore()
    with pytest.raises(ValidationException):
        store.add_record(None)


# Helper for auth token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 12. Authentication protection
def test_12_authentication_protection():
    client = TestClient(app)
    # Unauthenticated request -> 401
    res_unauth = client.get("/api/memory")
    assert res_unauth.status_code == 401

    # Valid request -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/memory?token={tok}")
    assert res_valid.status_code == 200


# 13. Future data isolation
def test_13_future_data_isolation():
    store = MemoryStore()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)

    r1 = MemoryRecord("m1", t1, "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    r2 = MemoryRecord("m2", t2, "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)

    store.add_record(r1)
    store.add_record(r2)

    cutoff = datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc)
    isolated = store.get_records(end_time=cutoff)
    assert len(isolated) == 1
    assert isolated[0].id == "m1"


# 14. No strategy duplication
def test_14_no_strategy_duplication():
    # Confirm MemoryService does not hold or duplicate strategy calculation logic
    svc = MemoryService()
    assert not hasattr(svc, "evaluate_trend")
    assert not hasattr(svc, "evaluate_spike")


# 15. No execution leakage
def test_15_no_execution_leakage():
    svc = MemoryService()
    res = svc.get_historical_memory()
    forbidden_keys = ["orders", "positions", "broker_id", "live_account", "wallet_balance"]
    for k in forbidden_keys:
        assert k not in res
