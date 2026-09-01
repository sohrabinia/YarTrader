"""
YarTrader Technical Indicators Mathematical Accuracy and Non-Degeneracy Tests
=============================================================================

Verifies that TechnicalAnalysisEngine computes mathematically accurate indicators
from chronological price series and exposes explicit insufficient_data states.
"""

from datetime import datetime, timezone
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.analysis_pipeline import TechnicalAnalysisEngine


def generate_synthetic_candles(prices):
    candles = []
    for i, p in enumerate(prices):
        candles.append(
            MarketDataPoint(
                AssetId="XAUUSD",
                Timestamp=datetime.now(timezone.utc),
                Open=p - 0.5,
                High=p + 1.0,
                Low=p - 1.0,
                Close=p,
                Volume=100.0
            )
        )
    return candles


def test_indicator_non_degeneracy_and_math_accuracy():
    engine = TechnicalAnalysisEngine()

    # Non-constant trending price series (50 bars)
    prices = [2000.0 + (i * 0.5) for i in range(50)]
    candles = generate_synthetic_candles(prices)

    res = engine.analyze(candles)

    assert res["insufficient_data"] is False
    assert res["sma_20"] is not None
    assert res["sma_50"] is not None
    assert res["ema_12"] is not None
    assert res["ema_26"] is not None

    # SMA 20 of last 20 prices [2015.0 .. 2024.5] is exactly 2019.75
    assert abs(res["sma_20"] - 2019.75) < 0.01

    # SMA 50 of all 50 prices [2000.0 .. 2024.5] should be 2012.25
    assert abs(res["sma_50"] - 2012.25) < 0.01

    # SMA20 and SMA50 must NOT be degenerate equal
    assert res["sma_20"] != res["sma_50"]

    # MACD line and RSI checks
    assert res["macd"] is not None
    assert res["macd_signal"] is not None
    assert res["macd_histogram"] is not None
    assert res["rsi"] is not None
    assert res["rsi"] > 50.0  # Strongly trending up -> RSI > 50

    # ATR and Bollinger Bands
    assert res["atr"] is not None
    assert res["upper_band"] is not None
    assert res["lower_band"] is not None
    assert res["upper_band"] > res["lower_band"]


def test_insufficient_history_explicit_state():
    engine = TechnicalAnalysisEngine()

    # Short history (10 bars)
    prices = [2000.0 + i for i in range(10)]
    candles = generate_synthetic_candles(prices)

    res = engine.analyze(candles)

    assert res["insufficient_data"] is True
    assert res["sma_20"] is None
    assert res["sma_50"] is None
    assert res["ema_12"] is None
    assert res["ema_26"] is None
    assert res["macd"] is None
    assert res["rsi"] is None
    assert res["atr"] is None


def test_oscillating_series_macd_and_rsi():
    engine = TechnicalAnalysisEngine()

    # Sine-like oscillating series
    import math
    prices = [2000.0 + 10.0 * math.sin(i * 0.2) for i in range(60)]
    candles = generate_synthetic_candles(prices)

    res = engine.analyze(candles)

    assert res["insufficient_data"] is False
    assert res["macd"] is not None
    assert res["macd_histogram"] is not None
    assert res["rsi"] is not None
    assert 0.0 <= res["rsi"] <= 100.0
