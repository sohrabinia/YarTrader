import pytest
from src.Research.Brain.range_regime_engine import RangeRegimeEngine, RangeRegimeResult

def build_sample_candles(start_price=2000.0, trend="UP", count=30):
    candles = []
    curr = start_price
    for i in range(count):
        if trend == "UP":
            curr += 0.5
        elif trend == "DOWN":
            curr -= 0.5
        else:
            curr += (0.2 if i % 2 == 0 else -0.2)
        candles.append({
            "open": curr - 0.1,
            "high": curr + 0.3,
            "low": curr - 0.3,
            "close": curr,
            "volume": 100
        })
    return candles

def test_case_1_pullback_classification():
    """CASE 1: HTF bullish + M5 temporary pull down -> PULLBACK (not RANGE or REVERSAL)."""
    engine = RangeRegimeEngine()
    candles = build_sample_candles(start_price=2000.0, trend="DOWN", count=30)
    res = engine.evaluate_regime(candles=candles, hurst_val=0.40, htf_bias="BULLISH", atr_val=1.0)
    assert res.regime == "PULLBACK"
    assert res.trade_candidate == "NONE"

def test_case_2_range_classification():
    """CASE 2: HTF neutral + bounded price action -> RANGE."""
    engine = RangeRegimeEngine()
    candles = build_sample_candles(start_price=2000.0, trend="FLAT", count=30)
    res = engine.evaluate_regime(candles=candles, hurst_val=0.42, fractal_dim=1.45, htf_bias="NEUTRAL", atr_val=2.0)
    assert res.regime == "RANGE"

def test_case_3_range_lower_boundary_rejection_long():
    """CASE 3: RANGE + lower boundary rejection -> LONG candidate."""
    engine = RangeRegimeEngine()
    candles = build_sample_candles(start_price=2000.0, trend="FLAT", count=30)
    # Force last candle to close near lower boundary but above low
    candles[-1]["close"] = 1996.0
    candles[-1]["low"] = 1995.0
    res = engine.evaluate_regime(candles=candles, hurst_val=0.40, fractal_dim=1.50, htf_bias="NEUTRAL", atr_val=2.0)
    assert res.regime == "RANGE"
    assert res.trade_candidate == "BUY"
    assert res.target_price is not None

def test_case_4_range_upper_boundary_rejection_short():
    """CASE 4: RANGE + upper boundary rejection -> SHORT candidate."""
    engine = RangeRegimeEngine()
    candles = build_sample_candles(start_price=2000.0, trend="FLAT", count=30)
    # Force last candle to close near upper boundary
    candles[-1]["close"] = 2004.0
    candles[-1]["high"] = 2005.0
    res = engine.evaluate_regime(candles=candles, hurst_val=0.40, fractal_dim=1.50, htf_bias="NEUTRAL", atr_val=2.0)
    assert res.regime == "RANGE"
    assert res.trade_candidate == "SELL"
    assert res.target_price is not None

def test_case_5_breakout_transition():
    """CASE 5: RANGE + strong breakout expansion -> TRANSITION."""
    engine = RangeRegimeEngine()
    candles = build_sample_candles(start_price=2000.0, trend="UP", count=30)
    res = engine.evaluate_regime(candles=candles, hurst_val=0.75, fractal_dim=1.20, htf_bias="NEUTRAL", atr_val=0.5)
    assert res.regime in ["TRANSITION", "TREND_UP"]

def test_case_6_insufficient_data():
    """CASE 6: Insufficient data fails closed as NO_TRADE."""
    engine = RangeRegimeEngine()
    res = engine.evaluate_regime(candles=[])
    assert res.regime == "NO_TRADE"
    assert res.confidence == 0.0
