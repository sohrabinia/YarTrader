from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from src.Data.MarketData.Models.models import MarketDataPoint

@dataclass
class MarketStructureState:
    trend: str  # "BULLISH", "BEARISH", "RANGE"
    structure_type: str  # "TRENDING_UP", "TRENDING_DOWN", "RANGE_BOUND", "BREAKOUT", "FALSE_BREAKOUT"
    swing_highs: List[float] = field(default_factory=list)
    swing_lows: List[float] = field(default_factory=list)
    key_support: float = 0.0
    key_resistance: float = 0.0
    market_structure_shift: bool = False
    liquidity_sweep: bool = False
    details: List[str] = field(default_factory=list)

class TradingKnowledgeBase:
    """
    Core Trading Education & Knowledge Base Layer for YarTrader V1.2.
    Evaluates pure price behavior, market structure, liquidity sweeps,
    and support/resistance without relying on technical indicators.
    """

    def analyze_market_structure(self, candles: List[MarketDataPoint]) -> MarketStructureState:
        if not candles or len(candles) < 5:
            return MarketStructureState(
                trend="RANGE",
                structure_type="RANGE_BOUND",
                details=["Insufficient market candles to establish structural trend."]
            )

        highs = [c.High for c in candles]
        lows = [c.Low for c in candles]
        closes = [c.Close for c in candles]
        n = len(candles)

        # 1. Swing Highs & Swing Lows (Pivot Detection)
        swing_highs = []
        swing_lows = []
        for i in range(2, n - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])

        # Key Support & Resistance from Price Behavior
        key_support = min(swing_lows[-3:]) if len(swing_lows) >= 3 else min(lows)
        key_resistance = max(swing_highs[-3:]) if len(swing_highs) >= 3 else max(highs)

        # 2. Trend & Structure Classification (HH/HL vs LH/LL)
        is_bullish = False
        is_bearish = False
        details = []

        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            hh = swing_highs[-1] > swing_highs[-2]
            hl = swing_lows[-1] > swing_lows[-2]
            lh = swing_highs[-1] < swing_highs[-2]
            ll = swing_lows[-1] < swing_lows[-2]

            if hh and hl:
                is_bullish = True
                details.append("Structure shows Higher Highs and Higher Lows.")
            elif lh and ll:
                is_bearish = True
                details.append("Structure shows Lower Highs and Lower Lows.")

        if not is_bullish and not is_bearish:
            # Fallback to recent candle direction comparison
            recent_delta = closes[-1] - closes[max(0, n - 10)]
            if recent_delta > 0:
                is_bullish = True
                details.append("Short-term price action exhibits upward momentum.")
            elif recent_delta < 0:
                is_bearish = True
                details.append("Short-term price action exhibits downward momentum.")
            else:
                details.append("Market is in a compressed range boundary.")

        trend = "BULLISH" if is_bullish else ("BEARISH" if is_bearish else "RANGE")

        # 3. Liquidity Sweep & False Breakout Detection
        liquidity_sweep = False
        latest_candle = candles[-1]
        latest_high = latest_candle.High
        latest_low = latest_candle.Low
        latest_close = latest_candle.Close

        # False breakout above resistance (Swept high then closed back inside range)
        if latest_high > key_resistance and latest_close < key_resistance:
            liquidity_sweep = True
            details.append("Liquidity sweep above key resistance detected (Bull trap).")
        # False breakout below support (Swept low then closed back inside range)
        elif latest_low < key_support and latest_close > key_support:
            liquidity_sweep = True
            details.append("Liquidity sweep below key support detected (Bear trap).")

        # 4. Market Structure Shift (MSS / ChoCh)
        mss = False
        if is_bullish and latest_close < (swing_lows[-1] if swing_lows else key_support):
            mss = True
            details.append("Market Structure Shift (ChoCh): Bullish structure invalidated by breakdown below recent swing low.")
        elif is_bearish and latest_close > (swing_highs[-1] if swing_highs else key_resistance):
            mss = True
            details.append("Market Structure Shift (ChoCh): Bearish structure invalidated by breakout above recent swing high.")

        structure_type = "TRENDING_UP" if is_bullish else ("TRENDING_DOWN" if is_bearish else "RANGE_BOUND")
        if mss:
            structure_type = "MARKET_STRUCTURE_SHIFT"
        elif liquidity_sweep:
            structure_type = "FALSE_BREAKOUT"

        return MarketStructureState(
            trend=trend,
            structure_type=structure_type,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            key_support=key_support,
            key_resistance=key_resistance,
            market_structure_shift=mss,
            liquidity_sweep=liquidity_sweep,
            details=details
        )
