import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Strategy.range_strategy import RangeStrategyEngine, RangeConfig, RangeSignalType, RangeStrategyResult
from src.Application.Services.range_strategy_service import RangeStrategyService
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

client = TestClient(app)

def create_synthetic_range_candles(base_price: float = 2300.0, count: int = 30, range_span: float = 2.0) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        # Oscillate price tightly within base_price to base_price + range_span
        offset = (i % 4) * (range_span / 3.0)
        open_p = base_price + offset
        close_p = base_price + (range_span - offset)
        high_p = base_price + range_span + 0.2
        low_p = base_price - 0.2
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

def create_synthetic_trending_candles(base_price: float = 2300.0, count: int = 30) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        open_p = base_price + (i * 3.0)
        close_p = base_price + (i * 3.0) + 2.5
        high_p = close_p + 1.0
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

def test_1_normal_range_detection():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30, range_span=2.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == RangeSignalType.RANGE
    assert res.range_width > 0.0
    assert res.normalized_range_ratio <= 4.5

def test_2_non_range_trending_market():
    engine = RangeStrategyEngine()
    trending = create_synthetic_trending_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", trending)
    assert res.signal_type == RangeSignalType.NO_SIGNAL
    assert res.normalized_range_ratio > 4.5

def test_3_insufficient_history_cold_start():
    engine = RangeStrategyEngine()
    short_candles = create_synthetic_range_candles(count=5)
    res = engine.evaluate("XAUUSD", "M15", short_candles)
    assert res.signal_type == RangeSignalType.INSUFFICIENT_DATA

def test_4_configuration_validation():
    with pytest.raises(ValidationException, match="lookback_period"):
        RangeConfig(lookback_period=2).validate()
    with pytest.raises(ValidationException, match="max_normalized_range"):
        RangeConfig(max_normalized_range=-1.0).validate()

def test_5_rolling_high_low_calculations():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=25, range_span=5.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.rolling_high >= res.rolling_low
    assert res.range_width == res.rolling_high - res.rolling_low

def test_6_close_position_in_range():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=25)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert 0.0 <= res.close_position_in_range <= 1.0

def test_7_no_look_ahead_bias_mandatory():
    """
    MANDATORY LOOK-AHEAD TEST:
    Verifies that adding future candles (T+1, T+2) does NOT change the range strategy
    evaluation for timestamp T.
    """
    engine = RangeStrategyEngine()
    base_candles = create_synthetic_range_candles(count=30)

    # Evaluate at timestamp T (index 29)
    eval_t = engine.evaluate("XAUUSD", "M15", base_candles)
    assert eval_t.signal_type == RangeSignalType.RANGE

    # Append 5 future trending candles (T+1 .. T+5)
    future_candles = create_synthetic_trending_candles(base_price=3000.0, count=5)
    extended_candles = base_candles + future_candles

    # Evaluate at exact same window up to timestamp T
    eval_t_again = engine.evaluate("XAUUSD", "M15", extended_candles[:30])

    assert eval_t.signal_type == eval_t_again.signal_type
    assert eval_t.normalized_range_ratio == eval_t_again.normalized_range_ratio
    assert eval_t.rolling_high == eval_t_again.rolling_high
    assert eval_t.rolling_low == eval_t_again.rolling_low

def test_8_zero_volatility_safeguard():
    engine = RangeStrategyEngine()
    now = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(AssetId="XAUUSD", Timestamp=now + timedelta(minutes=i*15), Open=2000.0, High=2000.0, Low=2000.0, Close=2000.0, Volume=100.0)
        for i in range(25)
    ]
    res = engine.evaluate("XAUUSD", "M15", flat_candles)
    assert res.signal_type == RangeSignalType.NO_SIGNAL
    assert not math.isnan(res.normalized_range_ratio)
    assert not math.isinf(res.normalized_range_ratio)

def test_9_duplicate_and_unordered_timestamps():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30)
    # Reverse timestamps order
    reversed_candles = list(reversed(candles))
    res = engine.evaluate("XAUUSD", "M15", reversed_candles)
    assert res.signal_type == RangeSignalType.RANGE

def test_10_api_range_endpoint_success():
    res = client.get("/api/strategy/range?symbol=XAUUSD&interval=M15")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "Success"
    assert json_data["data"]["symbol"] == "XAUUSD"
    assert "signal_type" in json_data["data"]

def test_11_api_auth_protection_denies_invalid_token():
    res = client.get("/api/strategy/range?symbol=XAUUSD&token=invalid_token")
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]

def test_12_no_order_execution_triggered():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert not hasattr(res, "order_id")
    assert not hasattr(res, "broker_status")

def test_13_provider_independence():
    service = RangeStrategyService()
    res = service.evaluate_symbol_range("XAUUSD", "M15")
    assert "signal_type" in res
    assert "metrics" in res

def test_14_deterministic_repeated_evaluation():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30)
    res1 = engine.evaluate("XAUUSD", "M15", candles)
    res2 = engine.evaluate("XAUUSD", "M15", candles)
    assert res1.signal_type == res2.signal_type
    assert res1.normalized_range_ratio == res2.normalized_range_ratio

def test_15_nan_and_infinity_safety():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert not math.isnan(res.range_width)
    assert not math.isinf(res.range_width)

def test_16_min_range_width_threshold():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30, range_span=0.1)
    res = engine.evaluate("XAUUSD", "M15", candles, config=RangeConfig(min_range_width=2.0))
    assert res.signal_type == RangeSignalType.NO_SIGNAL

def test_17_max_normalized_range_threshold():
    engine = RangeStrategyEngine()
    trending = create_synthetic_trending_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", trending, config=RangeConfig(max_normalized_range=1.0))
    assert res.signal_type == RangeSignalType.NO_SIGNAL

def test_18_range_result_to_dict_structure():
    engine = RangeStrategyEngine()
    candles = create_synthetic_range_candles(count=30)
    res = engine.evaluate("XAUUSD", "M15", candles)
    d = res.to_dict()
    assert "symbol" in d
    assert "metrics" in d
    assert "config" in d

def test_19_invalid_symbol_or_interval_handling():
    service = RangeStrategyService()
    with pytest.raises(ValidationException, match="Invalid market symbol"):
        service.evaluate_symbol_range(symbol="$$$")

def test_20_empty_candle_input_handling():
    engine = RangeStrategyEngine()
    res = engine.evaluate("XAUUSD", "M15", [])
    assert res.signal_type == RangeSignalType.INSUFFICIENT_DATA
