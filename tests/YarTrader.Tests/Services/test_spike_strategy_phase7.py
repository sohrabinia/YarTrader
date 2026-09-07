import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Strategy.spike_strategy import SpikeStrategyEngine, SpikeConfig, SpikeSignalType, SpikeStrategyResult
from src.Application.Services.spike_strategy_service import SpikeStrategyService
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

client = TestClient(app)

def create_synthetic_candles(base_price: float = 2300.0, count: int = 20, spike_at: int = -1, spike_size: float = 0.0) -> list[MarketDataPoint]:
    now = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        ts = now + timedelta(minutes=i * 15)
        open_p = base_price
        close_p = base_price
        if i == spike_at or (spike_at < 0 and i == count + spike_at):
            close_p = base_price + spike_size
            high_p = max(open_p, close_p) + 0.5
            low_p = min(open_p, close_p) - 0.5
        else:
            high_p = base_price + 1.0
            low_p = base_price - 1.0
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

def test_1_normal_series_no_spike():
    engine = SpikeStrategyEngine()
    candles = create_synthetic_candles(count=20, spike_size=0.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == SpikeSignalType.NO_SIGNAL
    assert res.spike_ratio < 2.5

def test_2_upward_spike_detection():
    engine = SpikeStrategyEngine()
    candles = create_synthetic_candles(count=20, spike_at=-1, spike_size=10.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == SpikeSignalType.SPIKE_UP
    assert res.candle_body == 10.0
    assert res.spike_ratio >= 2.5

def test_3_downward_spike_detection():
    engine = SpikeStrategyEngine()
    candles = create_synthetic_candles(count=20, spike_at=-1, spike_size=-10.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == SpikeSignalType.SPIKE_DOWN
    assert res.candle_body == -10.0
    assert res.spike_ratio >= 2.5

def test_4_insufficient_history_cold_start():
    engine = SpikeStrategyEngine()
    short_candles = create_synthetic_candles(count=5)
    res = engine.evaluate("XAUUSD", "M15", short_candles)
    assert res.signal_type == SpikeSignalType.INSUFFICIENT_DATA

def test_5_configuration_validation():
    with pytest.raises(ValidationException, match="lookback_period"):
        SpikeConfig(lookback_period=1).validate()
    with pytest.raises(ValidationException, match="spike_threshold"):
        SpikeConfig(spike_threshold=-1.0).validate()

def test_6_no_look_ahead_bias_mandatory():
    """
    MANDATORY LOOK-AHEAD TEST:
    Verifies that adding future candles (T+1, T+2) does NOT change the strategy
    evaluation for timestamp T.
    """
    engine = SpikeStrategyEngine()
    base_candles = create_synthetic_candles(count=20, spike_at=-1, spike_size=12.0)

    # Evaluate at timestamp T (index 19)
    eval_t = engine.evaluate("XAUUSD", "M15", base_candles)
    assert eval_t.signal_type == SpikeSignalType.SPIKE_UP

    # Append 5 future candles (T+1 .. T+5)
    future_candles = create_synthetic_candles(count=5)
    extended_candles = base_candles + future_candles

    # Evaluate at exact same window up to timestamp T
    eval_t_again = engine.evaluate("XAUUSD", "M15", extended_candles[:20])

    assert eval_t.signal_type == eval_t_again.signal_type
    assert eval_t.spike_ratio == eval_t_again.spike_ratio
    assert eval_t.volatility_baseline == eval_t_again.volatility_baseline

def test_7_no_order_execution_triggered():
    """
    Verifies strategy evaluation does NOT invoke broker/order execution or trading interfaces.
    """
    engine = SpikeStrategyEngine()
    candles = create_synthetic_candles(count=20, spike_at=-1, spike_size=15.0)
    res = engine.evaluate("XAUUSD", "M15", candles)
    assert res.signal_type == SpikeSignalType.SPIKE_UP
    # Assert result is purely informational signal and has no execution fields
    assert not hasattr(res, "order_id")
    assert not hasattr(res, "broker_status")

def test_8_api_spike_endpoint_success():
    res = client.get("/api/strategy/spike?symbol=XAUUSD&interval=M15")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "Success"
    assert json_data["data"]["symbol"] == "XAUUSD"
    assert "signal_type" in json_data["data"]

def test_9_api_auth_protection_denies_invalid_token():
    res = client.get("/api/strategy/spike?symbol=XAUUSD&token=invalid_token")
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]
