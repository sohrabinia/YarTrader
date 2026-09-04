import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class RangeRegimeResult:
    regime: str  # TREND_UP, TREND_DOWN, RANGE, PULLBACK, REVERSAL, TRANSITION, NO_TRADE
    confidence: float
    range_high: Optional[float] = None
    range_low: Optional[float] = None
    range_mid: Optional[float] = None
    range_width: Optional[float] = None
    breakout_probability: float = 0.0
    persistence: float = 0.5
    invalidation_reason: Optional[str] = None
    trade_candidate: Optional[str] = None  # BUY, SELL, NONE
    target_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    target_probability: float = 0.0

class RangeRegimeEngine:
    """
    Quantitative Range & Regime Engine for XAUUSD.
    Evaluates combined evidence from Hurst Exponent, Higuchi Fractal Dimension,
    ATR/volatility, swing/liquidity boundaries, and MTF alignment.
    Does NOT use simple Hurst < 0.5 rules alone.
    """
    def __init__(self, min_samples_required: int = 14) -> None:
        self.min_samples_required = min_samples_required

    def evaluate_regime(
        self,
        candles: List[Dict[str, Any]],
        hurst_val: Optional[float] = None,
        fractal_dim: Optional[float] = None,
        atr_val: Optional[float] = None,
        htf_bias: Optional[str] = None,
        mtf_structure: Optional[Dict[str, Any]] = None
    ) -> RangeRegimeResult:
        if not candles or len(candles) < self.min_samples_required:
            return RangeRegimeResult(
                regime="NO_TRADE",
                confidence=0.0,
                invalidation_reason="INSUFFICIENT_CANDLE_SAMPLES"
            )

        closes = [float(c["close"]) for c in candles if "close" in c and math.isfinite(float(c["close"]))]
        highs = [float(c["high"]) for c in candles if "high" in c and math.isfinite(float(c["high"]))]
        lows = [float(c["low"]) for c in candles if "low" in c and math.isfinite(float(c["low"]))]

        if len(closes) < self.min_samples_required:
            return RangeRegimeResult(
                regime="NO_TRADE",
                confidence=0.0,
                invalidation_reason="MALFORMED_CANDLE_PRICES"
            )

        current_close = closes[-1]
        recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        range_width = recent_high - recent_low
        range_mid = recent_low + (range_width / 2.0)

        # 1. Analyze Volatility & Range Expansion
        if atr_val is None or not math.isfinite(atr_val) or atr_val <= 0:
            tr_list = [highs[i] - lows[i] for i in range(len(highs))]
            atr_val = sum(tr_list[-14:]) / min(14, len(tr_list))

        atr_normalized_width = range_width / atr_val if atr_val > 0 else 0.0

        # 2. Evaluate Persistence & Fractal Complexity
        h_score = hurst_val if (hurst_val is not None and math.isfinite(hurst_val)) else 0.5
        d_score = fractal_dim if (fractal_dim is not None and math.isfinite(fractal_dim)) else 1.5

        # 3. Detect Range vs Pullback vs Trend
        # Check HTF alignment
        htf_up = htf_bias in ["BULLISH", "BUY", "TREND_UP"]
        htf_down = htf_bias in ["BEARISH", "SELL", "TREND_DOWN"]

        # Local slope
        start_close = closes[-10] if len(closes) >= 10 else closes[0]
        net_move = current_close - start_close
        abs_move = abs(net_move)

        is_bounded_geometrically = atr_normalized_width <= 6.0 and abs_move <= (2.5 * atr_val)

        # Breakout Probability Estimation
        dist_to_high = recent_high - current_close
        dist_to_low = current_close - recent_low
        near_upper = dist_to_high <= (0.25 * range_width)
        near_lower = dist_to_low <= (0.25 * range_width)

        breakout_prob = min(0.95, max(0.05, (h_score * 0.5) + (abs_move / (range_width + 1e-6)) * 0.5))

        # Regime State Machine Classification
        if htf_up and net_move < 0 and not is_bounded_geometrically:
            # HTF Bullish + M5 temporary pull down -> PULLBACK
            return RangeRegimeResult(
                regime="PULLBACK",
                confidence=min(95.0, max(50.0, (1.0 - h_score) * 100.0)),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                trade_candidate="NONE",
                invalidation_reason="NORMAL_TREND_PULLBACK"
            )
        elif htf_down and net_move > 0 and not is_bounded_geometrically:
            # HTF Bearish + M5 temporary pull up -> PULLBACK
            return RangeRegimeResult(
                regime="PULLBACK",
                confidence=min(95.0, max(50.0, (1.0 - h_score) * 100.0)),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                trade_candidate="NONE",
                invalidation_reason="NORMAL_TREND_PULLBACK"
            )

        if breakout_prob > 0.75 and (near_upper or near_lower):
            # High momentum expansion near boundaries -> TRANSITION
            target_reg = "TREND_UP" if near_upper else "TREND_DOWN"
            return RangeRegimeResult(
                regime="TRANSITION",
                confidence=round(breakout_prob * 100.0, 1),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                invalidation_reason=f"BREAKOUT_EXPANSION_TOWARDS_{target_reg}"
            )

        if is_bounded_geometrically or (h_score < 0.48 and d_score > 1.35):
            # Mean-Reversion RANGE Policy
            trade_candidate = "NONE"
            target_price = None
            inval_price = None
            target_prob = 0.0

            if near_lower and current_close > recent_low:
                # Rejection near lower boundary -> LONG candidate targeting range_mid/high
                trade_candidate = "BUY"
                target_price = range_mid
                inval_price = recent_low - (0.5 * atr_val)
                target_prob = round(max(0.1, 1.0 - breakout_prob) * 100.0, 1)
            elif near_upper and current_close < recent_high:
                # Rejection near upper boundary -> SHORT candidate targeting range_mid/low
                trade_candidate = "SELL"
                target_price = range_mid
                inval_price = recent_high + (0.5 * atr_val)
                target_prob = round(max(0.1, 1.0 - breakout_prob) * 100.0, 1)

            return RangeRegimeResult(
                regime="RANGE",
                confidence=round((1.0 - abs(h_score - 0.5)) * 100.0, 1),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                trade_candidate=trade_candidate,
                target_price=target_price,
                invalidation_price=inval_price,
                target_probability=target_prob
            )

        if net_move > (1.5 * atr_val) or (htf_up and h_score > 0.52):
            return RangeRegimeResult(
                regime="TREND_UP",
                confidence=round(h_score * 100.0, 1),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                trade_candidate="BUY" if htf_up else "NONE"
            )

        if net_move < -(1.5 * atr_val) or (htf_down and h_score > 0.52):
            return RangeRegimeResult(
                regime="TREND_DOWN",
                confidence=round(h_score * 100.0, 1),
                range_high=recent_high,
                range_low=recent_low,
                range_mid=range_mid,
                range_width=range_width,
                breakout_probability=breakout_prob,
                persistence=h_score,
                trade_candidate="SELL" if htf_down else "NONE"
            )

        return RangeRegimeResult(
            regime="NO_TRADE",
            confidence=0.0,
            invalidation_reason="UNCERTAIN_REGIME_CONDITIONS"
        )
