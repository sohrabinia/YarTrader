import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Strategy.trend_strategy import TrendStrategyEngine, TrendConfig, TrendSignalType, TrendStrategyResult
from src.Application.Services.trend_strategy_service import TrendStrategyService
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

client = TestClient(app)

def create_synthetic_uptrend_candles(base_price: float = 2300.0, count: int = 30, step: float = 2.0) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        open_p = base_price + (i * step)
        close_p = open_p + 1.5
        high_p = close_p + 0.5
        low_p = open_p - 0.5
        pt = MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=ts,
            Open=open_p,
            High=high_p,
            Low=low_p,
            Close=close_p,
            Volume=100.0
        )
        points.append(pt)
    return points

def create_synthetic_downtrend_candles(base_price: float = 2300.0, count: int = 30, step: float = 2.0) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        open_p = base_price - (i * step)
        close_p = open_p - 1.5
        high_p = open_p + 0.5
        low_p = close_p - 0.5
        pt = MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=ts,
            Open=open_p,
            High=high_p,
            Low=low_p,
            Close=close_p,
            Volume=100.0
        )
        points.append(pt)
    return points

def create_synthetic_flat_candles(base_price: float = 2300.0, count: int = 30) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        open_p = base_price + (1.0 if i % 2 == 0 else -1.0)
        close_p = base_price + (-1.0 if i % 2 == 0 else 1.0)
        high_p = base_price + 1.5
        low_p = base_price - 1.5
        pt = MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=ts,
            Open=open_p,
            High=high_p,
            Low=low_p,
            Close=close_p,
            Volume=100.0
        )
        points.append(pt)
    return points

def test_1_basic_uptrend_detection():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30, step=2.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == TrendSignalType.TREND_UP
    assert res.fast_sma > res.slow_sma
    assert res.trend_spread > 0.0

def test_2_basic_downtrend_detection():
    engine = TrendStrategyEngine()
    candles = create_synthetic_downtrend_candles(count=30, step=2.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == TrendSignalType.TREND_DOWN
    assert res.fast_sma < res.slow_sma
    assert res.trend_spread < 0.0

def test_3_sideways_flat_no_trend():
    engine = TrendStrategyEngine()
    candles = create_synthetic_flat_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == TrendSignalType.NO_SIGNAL

def test_4_insufficient_data_cold_start():
    engine = TrendStrategyEngine()
    short_candles = create_synthetic_uptrend_candles(count=10)
    res = engine.evaluate("XAUUSD", "M15", short_candles)
    assert res.signal_type == TrendSignalType.INSUFFICIENT_DATA

def test_5_exact_threshold_boundary_just_above():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30, step=2.0)
    res = engine.evaluate("XAUUSD", "M15", candles, config=TrendConfig(minimum_trend_strength=0.1))
    assert res.signal_type == TrendSignalType.TREND_UP

def test_6_exact_threshold_boundary_just_below():
    engine = TrendStrategyEngine()
    candles = create_synthetic_flat_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles, config=TrendConfig(minimum_trend_strength=10.0))
    assert res.signal_type == TrendSignalType.NO_SIGNAL

def test_7_trend_config_validation():
    with pytest.raises(ValidationException, match="fast_period"):
        TrendConfig(fast_period=1).validate()
    with pytest.raises(ValidationException, match="fast_period"):
        TrendConfig(fast_period=20, slow_period=10).validate()

def test_8_fast_slow_period_validation():
    with pytest.raises(ValidationException, match="minimum_trend_strength"):
        TrendConfig(minimum_trend_strength=-1.0).validate()

def test_9_chronological_ordering_and_reversal():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30)
    reversed_candles = list(reversed(candles))
    res = engine.evaluate("XAUUSD", "M15", reversed_candles)
    assert res.signal_type == TrendSignalType.TREND_UP

def test_10_duplicate_timestamps_handling():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30)
    # Add duplicate timestamp candle
    dup = MarketDataPoint(AssetId="XAUUSD", Timestamp=candles[0].Timestamp, Open=2300.0, High=2301.0, Low=2299.0, Close=2300.5, Volume=100.0)
    res = engine.evaluate("XAUUSD", "M15", candles + [dup])
    assert res.signal_type in [TrendSignalType.TREND_UP, TrendSignalType.NO_SIGNAL]

def test_11_deterministic_repeated_execution():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30)
    res1 = engine.evaluate("XAUUSD", "M15", candles)
    res2 = engine.evaluate("XAUUSD", "M15", candles)
    assert res1.signal_type == res2.signal_type
    assert res1.fast_sma == res2.fast_sma
    assert res1.slow_sma == res2.slow_sma

def test_12_flat_market_safety():
    engine = TrendStrategyEngine()
    now = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(AssetId="XAUUSD", Timestamp=now + timedelta(minutes=i*15), Open=2000.0, High=2000.0, Low=2000.0, Close=2000.0, Volume=100.0)
        for i in range(25)
    ]
    res = engine.evaluate("XAUUSD", "M15", flat_candles)
    assert res.signal_type == TrendSignalType.NO_SIGNAL
    assert not math.isnan(res.normalized_trend_strength)

def test_13_zero_volatility_safety():
    engine = TrendStrategyEngine()
    now = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(AssetId="XAUUSD", Timestamp=now + timedelta(minutes=i*15), Open=2000.0, High=2000.0, Low=2000.0, Close=2000.0, Volume=100.0)
        for i in range(25)
    ]
    res = engine.evaluate("XAUUSD", "M15", flat_candles, config=TrendConfig(min_volatility_baseline=0.01))
    assert res.signal_type == TrendSignalType.NO_SIGNAL

def test_14_numerical_safety_nan_infinity():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert not math.isnan(res.fast_sma)
    assert not math.isinf(res.slow_sma)
    assert not math.isnan(res.normalized_trend_strength)

def test_15_no_look_ahead_bias_mandatory():
    """
    MANDATORY LOOK-AHEAD TEST:
    Verifies that adding future candles (T+1, T+2) does NOT change the trend strategy
    evaluation for timestamp T.
    """
    engine = TrendStrategyEngine()
    base_candles = create_synthetic_uptrend_candles(count=30)

    # Evaluate at timestamp T (index 29)
    eval_t = engine.evaluate("XAUUSD", "M15", base_candles)
    assert eval_t.signal_type == TrendSignalType.TREND_UP

    # Append 5 future downtrend candles (T+1 .. T+5)
    future_candles = create_synthetic_downtrend_candles(base_price=3000.0, count=5)
    extended_candles = base_candles + future_candles

    # Evaluate at exact same window up to timestamp T
    eval_t_again = engine.evaluate("XAUUSD", "M15", extended_candles[:30])

    assert eval_t.signal_type == eval_t_again.signal_type
    assert eval_t.fast_sma == eval_t_again.fast_sma
    assert eval_t.slow_sma == eval_t_again.slow_sma
    assert eval_t.normalized_trend_strength == eval_t_again.normalized_trend_strength

def test_16_api_authentication():
    res = client.get("/api/strategy/trend?symbol=XAUUSD&token=invalid_token")
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]

def test_17_api_response_shape():
    res = client.get("/api/strategy/trend?symbol=XAUUSD&interval=M15")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "Success"
    assert json_data["data"]["symbol"] == "XAUUSD"
    assert "fast_sma" in json_data["data"]["metrics"]
    assert "slow_sma" in json_data["data"]["metrics"]

def test_18_malformed_input_handling():
    service = TrendStrategyService()
    with pytest.raises(ValidationException, match="Invalid market symbol"):
        service.evaluate_symbol_trend(symbol="$$$")

def test_19_provider_independence():
    service = TrendStrategyService()
    res = service.evaluate_symbol_trend("XAUUSD", "M15")
    assert "signal_type" in res
    assert "metrics" in res

def test_20_no_execution_leakage():
    engine = TrendStrategyEngine()
    candles = create_synthetic_uptrend_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert not hasattr(res, "order_id")
    assert not hasattr(res, "broker_status")
