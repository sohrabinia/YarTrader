"""Deterministic, causal market-regime policy shared by signal and execution callers.

Uses only supplied closed OHLC bars. This is a rule-based baseline, not a trained
predictor; thresholds must be validated with walk-forward tests before live use.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import math

@dataclass(frozen=True)
class MarketBehavior:
    regime: str
    direction: str
    atr: float
    channel_low: float
    channel_high: float
    entry_zone_low: float
    entry_zone_high: float
    spike_target_distance: float
    confidence: float
    reason: str
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MarketBehaviorPolicy:
    """Classify RANGE/TREND/SPIKE/TRANSITION/UNCERTAIN and give risk levels."""
    def __init__(self, lookback: int = 20) -> None:
        self.lookback = max(10, int(lookback))

    def evaluate(self, candles: List[Dict[str, Any]]) -> MarketBehavior:
        bars = candles[-(self.lookback + 1):]
        if len(bars) < self.lookback:
            return MarketBehavior("UNCERTAIN", "WAIT", 0, 0, 0, 0, 0, 0, 0, "insufficient_closed_bars")
        try:
            vals = [[float(b[k]) for k in ("open", "high", "low", "close")] for b in bars]
        except (KeyError, TypeError, ValueError):
            return MarketBehavior("UNCERTAIN", "WAIT", 0, 0, 0, 0, 0, 0, 0, "malformed_ohlc")
        if any(not all(math.isfinite(v) for v in row) or row[2] <= 0 or row[1] < row[2] or not(row[2] <= row[0] <= row[1]) or not(row[2] <= row[3] <= row[1]) for row in vals):
            return MarketBehavior("UNCERTAIN", "WAIT", 0, 0, 0, 0, 0, 0, 0, "invalid_ohlc_geometry")
        highs = [r[1] for r in vals]; lows = [r[2] for r in vals]; closes = [r[3] for r in vals]
        trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(vals))]
        atr = sum(trs[-14:]) / len(trs[-14:])
        if atr <= 0 or not math.isfinite(atr):
            return MarketBehavior("UNCERTAIN", "WAIT", 0, min(lows), max(highs), 0, 0, 0, 0, "zero_atr")
        recent_high, recent_low = max(highs[-self.lookback:-1]), min(lows[-self.lookback:-1])
        last = vals[-1]; move = closes[-1] - closes[max(0, len(closes)-6)]
        efficiency = abs(move) / max(sum(abs(closes[i]-closes[i-1]) for i in range(max(1,len(closes)-5),len(closes))), atr)
        last_range = last[1] - last[2]
        # Spike uses only a fully closed candle and prior-bar range; target is set before entry.
        if last_range >= 2.2*atr and (last[3] > recent_high or last[3] < recent_low):
            direction = "BUY" if last[3] > recent_high else "SELL"
            return MarketBehavior("SPIKE", direction, atr, recent_low, recent_high, recent_low, recent_high, 2.5*atr, 0.75, "closed_bar_range_expansion_breakout; precomputed_target=2.5_ATR")
        width = recent_high - recent_low
        if width <= 4.5*atr and efficiency < 0.55:
            pos = (closes[-1]-recent_low)/width if width > 0 else 0.5
            direction = "BUY" if pos <= 0.25 else "SELL" if pos >= 0.75 else "WAIT"
            return MarketBehavior("RANGE", direction, atr, recent_low, recent_high, recent_low+0.2*width, recent_high-0.2*width, 0, 0.65, "mean_reversion_only_near_range_edges")
        if efficiency >= 0.58 and abs(move) >= 1.2*atr:
            direction = "BUY" if move > 0 else "SELL"
            # Prefer pullbacks near the channel edge; do not counter-trend blindly.
            return MarketBehavior("TREND_UP" if move > 0 else "TREND_DOWN", direction, atr, recent_low, recent_high, recent_low, recent_high, 0, min(0.9, 0.55+efficiency*0.3), "directional_efficiency; wait_for_pullback_not_chase")
        return MarketBehavior("TRANSITION", "WAIT", atr, recent_low, recent_high, recent_low, recent_high, 0, 0.35, "regime_not_clear")
