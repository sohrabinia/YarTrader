import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Backtest.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestStrategyType,
    BacktestResult,
    BacktestSummary,
    BacktestEvaluation
)
from src.Application.Services.backtest_service import BacktestService
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


# 1. Configuration validation
def test_1_config_validation():
    cfg = BacktestConfig(symbol="XAUUSD", interval="M15", min_history_bars=25)
    cfg.validate()
    assert cfg.min_history_bars == 25

    with pytest.raises(ValidationException):
        BacktestConfig(symbol="", interval="M15").validate()

    with pytest.raises(ValidationException):
        BacktestConfig(symbol="XAUUSD", min_history_bars=1).validate()


# 2. Valid backtest execution over trend series
def test_2_trend_strategy_backtest_execution():
    engine = BacktestEngine()
    candles = generate_candle_series(50, trend=1.0)
    cfg = BacktestConfig(symbol="XAUUSD", interval="M15", strategy_type=BacktestStrategyType.TREND, min_history_bars=21)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)

    assert isinstance(res, BacktestResult)
    assert res.strategy_type == BacktestStrategyType.TREND
    assert res.summary.total_evaluations == 30  # 50 - 21 + 1
    assert res.summary.valid_evaluations == 30
    assert len(res.evaluations) == 30


# 3. Spike strategy backtest execution
def test_3_spike_strategy_backtest_execution():
    engine = BacktestEngine()
    candles = generate_candle_series(40, trend=0.1)
    cfg = BacktestConfig(symbol="XAUUSD", interval="M15", strategy_type=BacktestStrategyType.SPIKE, min_history_bars=15)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)

    assert res.strategy_type == BacktestStrategyType.SPIKE
    assert res.summary.total_evaluations == 26  # 40 - 15 + 1
    assert len(res.evaluations) == 26


# 4. Range strategy backtest execution
def test_4_range_strategy_backtest_execution():
    engine = BacktestEngine()
    candles = generate_candle_series(40, trend=0.0)  # flat market
    cfg = BacktestConfig(symbol="XAUUSD", interval="M15", strategy_type=BacktestStrategyType.RANGE, min_history_bars=21)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)

    assert res.strategy_type == BacktestStrategyType.RANGE
    assert res.summary.total_evaluations == 20  # 40 - 21 + 1
    assert res.summary.signal_counts.get("RANGE", 0) > 0


# 5. Invalid strategy type rejection
def test_5_invalid_strategy_type_rejection():
    svc = BacktestService()
    with pytest.raises(ValidationException, match="Invalid backtest strategy type"):
        svc.run_historical_backtest(symbol="XAUUSD", strategy="NON_EXISTENT")


# 6. Chronological ordering handling
def test_6_chronological_ordering():
    engine = BacktestEngine()
    candles = generate_candle_series(30)
    reversed_candles = list(reversed(candles))

    res_normal = engine.run_backtest("XAUUSD", "M15", candles)
    res_reversed = engine.run_backtest("XAUUSD", "M15", reversed_candles)

    assert res_normal.summary.total_evaluations == res_reversed.summary.total_evaluations
    assert [e.timestamp for e in res_normal.evaluations] == [e.timestamp for e in res_reversed.evaluations]


# 7. Duplicate timestamps handling
def test_7_duplicate_timestamps_handling():
    engine = BacktestEngine()
    candles = generate_candle_series(30)
    # Duplicate the 5th candle
    candles_with_dups = candles[:5] + [candles[4]] + candles[5:]

    res_clean = engine.run_backtest("XAUUSD", "M15", candles)
    res_dups = engine.run_backtest("XAUUSD", "M15", candles_with_dups)

    assert res_clean.summary.total_evaluations == res_dups.summary.total_evaluations


# 8. Insufficient history cold start
def test_8_insufficient_history_cold_start():
    engine = BacktestEngine()
    short_candles = generate_candle_series(10)
    cfg = BacktestConfig(min_history_bars=21)
    res = engine.run_backtest("XAUUSD", "M15", short_candles, cfg)

    assert res.summary.total_evaluations == 0
    assert len(res.evaluations) == 0


# 9. Empty dataset handling
def test_9_empty_dataset_handling():
    engine = BacktestEngine()
    res = engine.run_backtest("XAUUSD", "M15", [])

    assert res.summary.total_evaluations == 0
    assert res.summary.valid_evaluations == 0
    assert res.evaluations == []


# 10. Deterministic repeated execution
def test_10_deterministic_repeated_execution():
    engine = BacktestEngine()
    candles = generate_candle_series(40)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.TREND)

    res1 = engine.run_backtest("XAUUSD", "M15", candles, cfg).to_dict()
    res2 = engine.run_backtest("XAUUSD", "M15", candles, cfg).to_dict()

    # Remove dynamic execution timestamp before strict comparison
    res1.pop("executed_at", None)
    res2.pop("executed_at", None)
    assert res1 == res2


# 11. Spike strategy reuse verification
def test_11_spike_strategy_reuse():
    engine = BacktestEngine()
    assert hasattr(engine.spike_engine, "evaluate")
    candles = generate_candle_series(25)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.SPIKE, min_history_bars=15)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)
    assert "spike_ratio" in res.evaluations[0].metrics


# 12. Range strategy reuse verification
def test_12_range_strategy_reuse():
    engine = BacktestEngine()
    assert hasattr(engine.range_engine, "evaluate")
    candles = generate_candle_series(25)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.RANGE, min_history_bars=21)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)
    assert "range_width" in res.evaluations[0].metrics


# 13. Trend strategy reuse verification
def test_13_trend_strategy_reuse():
    engine = BacktestEngine()
    assert hasattr(engine.trend_engine, "evaluate")
    candles = generate_candle_series(25)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.TREND, min_history_bars=21)
    res = engine.run_backtest("XAUUSD", "M15", candles, cfg)
    assert "fast_sma" in res.evaluations[0].metrics


# 14. No duplicated strategy math
def test_14_no_duplicated_strategy_math():
    engine = BacktestEngine()
    # Confirm BacktestEngine holds instances of existing engines
    assert engine.spike_engine.__class__.__name__ == "SpikeStrategyEngine"
    assert engine.range_engine.__class__.__name__ == "RangeStrategyEngine"
    assert engine.trend_engine.__class__.__name__ == "TrendStrategyEngine"


# 15. Walk-forward evaluation verification
def test_15_walk_forward_evaluation():
    engine = BacktestEngine()
    candles = generate_candle_series(30)
    res = engine.run_backtest("XAUUSD", "M15", candles)

    # First evaluation at bar 21 must have timestamp of 21st candle
    assert res.evaluations[0].timestamp == candles[20].Timestamp
    # Last evaluation at bar 30 must have timestamp of 30th candle
    assert res.evaluations[-1].timestamp == candles[29].Timestamp


# 16. MANDATORY FUTURE-CANDLE INVARIANCE (NO LOOK-AHEAD BIAS)
def test_16_mandatory_future_candle_invariance():
    engine = BacktestEngine()
    candles_base = generate_candle_series(30)

    # Run backtest on base dataset of 30 candles
    res_base = engine.run_backtest("XAUUSD", "M15", candles_base)

    # Append 20 arbitrary future candles (total 50 candles)
    candles_extended = generate_candle_series(50)
    res_extended = engine.run_backtest("XAUUSD", "M15", candles_extended)

    # The first 10 evaluations (corresponding to bars 21..30) in res_extended
    # MUST be 100% identical to res_base evaluations
    base_eval_dicts = [e.to_dict() for e in res_base.evaluations]
    extended_prefix_eval_dicts = [e.to_dict() for e in res_extended.evaluations[:len(base_eval_dicts)]]

    assert base_eval_dicts == extended_prefix_eval_dicts


# Helper to create a valid session token for test endpoint calls
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 17. API authentication protection
def test_17_api_authentication():
    client = TestClient(app)
    # Unauthenticated request (no token) -> 401
    res_unauth = client.get("/api/backtest?symbol=XAUUSD&strategy=TREND")
    assert res_unauth.status_code == 401

    # Invalid token request -> 401
    res_invalid = client.get("/api/backtest?symbol=XAUUSD&strategy=TREND&token=invalid_token")
    assert res_invalid.status_code == 401

    # Valid token request -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/backtest?symbol=XAUUSD&strategy=TREND&token={tok}")
    assert res_valid.status_code == 200


# 18. API parameter validation
def test_18_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/backtest?symbol=XAUUSD&limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 19. API response shape
def test_19_api_response_shape():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/backtest?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "symbol" in data
    assert "interval" in data
    assert "strategy_type" in data
    assert "summary" in data
    assert "evaluations" in data
    assert "config" in data


# 20. Numerical safety (NaN / Infinity handling)
def test_20_numerical_safety():
    engine = BacktestEngine()
    base_time = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=base_time + timedelta(minutes=15 * i),
            Open=100.0, High=100.0, Low=100.0, Close=100.0, Volume=0.0
        )
        for i in range(30)
    ]
    res = engine.run_backtest("XAUUSD", "M15", flat_candles)
    assert res.summary.total_evaluations == 10
    for ev in res.evaluations:
        for val in ev.metrics.values():
            assert not (val != val)  # Not NaN


# 21. Flat market safety
def test_21_flat_market_safety():
    engine = BacktestEngine()
    base_time = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=base_time + timedelta(minutes=15 * i),
            Open=2000.0, High=2000.0, Low=2000.0, Close=2000.0, Volume=10.0
        )
        for i in range(30)
    ]
    res = engine.run_backtest("XAUUSD", "M15", flat_candles, BacktestConfig(strategy_type=BacktestStrategyType.TREND))
    assert res.summary.signal_counts.get("NO_SIGNAL", 0) == 10


# 22. Signal distribution counting
def test_22_signal_distribution_counting():
    summary = BacktestSummary(
        total_evaluations=100,
        signal_counts={"TREND_UP": 60, "NO_SIGNAL": 40},
        valid_evaluations=100,
        insufficient_data_count=0
    )
    s_dict = summary.to_dict()
    assert s_dict["total_evaluations"] == 100
    assert s_dict["signal_counts"]["TREND_UP"] == 60


# 23. Result aggregation structure
def test_23_result_aggregation_structure():
    svc = BacktestService()
    res_dict = svc.run_historical_backtest(symbol="XAUUSD", interval="M15", strategy="TREND", limit=50)

    assert res_dict["symbol"] == "XAUUSD"
    assert res_dict["interval"] == "M15"
    assert res_dict["strategy_type"] == "TREND"
    assert "total_evaluations" in res_dict["summary"]


# 24. Large input bounded behavior
def test_24_large_input_bounded_behavior():
    svc = BacktestService()
    with pytest.raises(ValidationException):
        svc.run_historical_backtest(symbol="XAUUSD", limit=0)

    with pytest.raises(ValidationException):
        svc.run_historical_backtest(symbol="XAUUSD", limit=1001)


# 25. Regression / Integration path (Zero execution leakage)
def test_25_zero_execution_leakage():
    svc = BacktestService()
    res_dict = svc.run_historical_backtest(symbol="XAUUSD", interval="M15", strategy="TREND", limit=40)

    assert "summary" in res_dict
    assert "evaluations" in res_dict
    assert "orders" not in res_dict
    assert "positions" not in res_dict
    assert "trades" not in res_dict
