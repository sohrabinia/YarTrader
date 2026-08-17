import os
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Features.models import MarketFeatureSet, FeatureValue
from src.Research.Features.pipeline import FeaturePipeline

class TechnicalAnalysisEngine:
    """Analyzes mathematical, moving average and statistical indicators of input candles."""

    def analyze(self, candles: List[MarketDataPoint]) -> Dict[str, Any]:
        if not candles:
            return {}
        closes = [c.Close for c in candles]
        highs = [c.High for c in candles]
        lows = [c.Low for c in candles]
        n = len(closes)

        # Price Action & Market Structure analysis (Indicator-Free)
        recent_highs = highs[-20:] if n >= 20 else highs
        recent_lows = lows[-20:] if n >= 20 else lows

        highest_high = max(highs) if highs else 0.0
        lowest_low = min(lows) if lows else 0.0
        support = min(recent_lows) if recent_lows else 0.0
        resistance = max(recent_highs) if recent_highs else 0.0

        # Structural swing points
        swing_highs = [highs[i] for i in range(1, len(highs) - 1) if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
        swing_lows = [lows[i] for i in range(1, len(lows) - 1) if lows[i] < lows[i-1] and lows[i] < lows[i+1]]

        # Price Action Range & Variance
        mean_price = sum(closes) / n if n > 0 else 0.0
        variance = sum((c - mean_price) ** 2 for c in closes) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        return {
            "support": support,
            "resistance": resistance,
            "highest_high": highest_high,
            "lowest_low": lowest_low,
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "mean": mean_price,
            "std_dev": std_dev,
            "sma_20": mean_price,  # Retained for backwards schema compatibility
            "sma_50": mean_price,
            "ema_12": mean_price,
            "ema_26": mean_price,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_histogram": 0.0,
            "rsi": 50.0,
            "atr": (resistance - support) / 14 if n >= 14 else 0.0,
            "upper_band": resistance,
            "lower_band": support
        }

class FeatureEngineeringLayer:
    """Orchestrates standard feature pipeline to produce a rich MarketFeatureSet."""
    def __init__(self, pipeline: Optional[FeaturePipeline] = None) -> None:
        self.pipeline = pipeline or FeaturePipeline()

    def process(self, candles: List[MarketDataPoint]) -> MarketFeatureSet:
        return self.pipeline.execute(data_points=candles)

class MarketRegimeDetection:
    """Identifies and classifies current structural market regimes."""
    def detect(self, candles: List[MarketDataPoint], feature_set: MarketFeatureSet) -> Dict[str, Any]:
        vol_state_feat = feature_set.Features.get("volatility_state")
        trend_strength_feat = feature_set.Features.get("trend_strength_classification")
        range_expansion_feat = feature_set.Features.get("range_expansion")

        vol_state = vol_state_feat.Value if vol_state_feat else "low"
        trend_strength = trend_strength_feat.Value if trend_strength_feat else "neutral"
        range_expansion = range_expansion_feat.Value if range_expansion_feat else 1.0

        regime = "Quiet Range-Bound"
        explanation = "Low volatility and range compression indicate standard mean-reverting behavior."

        if vol_state == "high" and range_expansion > 1.2:
            regime = "High Volatility Breakout/Expansion"
            explanation = "Coincidence of high volatility and range expansion indicates structural breakout regime."
        elif "strong" in str(trend_strength):
            regime = "Strong Trending"
            explanation = "Stable and persistent trend strength indicates a strong directional trending regime."
        elif vol_state == "medium":
            regime = "Normal Volatility"
            explanation = "Baseline volatility with no active extreme breakout or compression conditions."

        return {
            "regime": regime,
            "explanation": explanation,
            "vol_state": vol_state,
            "trend_strength": trend_strength,
            "range_expansion": range_expansion
        }

class TrendAnalysis:
    """Analyzes trend directions and classifications."""
    def analyze(self, candles: List[MarketDataPoint], feature_set: MarketFeatureSet) -> Dict[str, Any]:
        dir_mvmt_feat = feature_set.Features.get("directional_movement")
        trend_strength_feat = feature_set.Features.get("trend_strength_classification")

        direction = dir_mvmt_feat.Value if dir_mvmt_feat else 0.0
        strength = trend_strength_feat.Value if trend_strength_feat else "neutral"

        direction_lbl = "Bullish" if direction > 0 else ("Bearish" if direction < 0 else "Neutral")

        return {
            "direction": direction,
            "direction_label": direction_lbl,
            "strength": strength,
            "is_trending": "strong" in str(strength) or "weak" in str(strength)
        }

class VolatilityAnalysis:
    """Analyzes price variance and standard deviation bands."""
    def analyze(self, candles: List[MarketDataPoint], feature_set: MarketFeatureSet) -> Dict[str, Any]:
        rolling_vol_feat = feature_set.Features.get("rolling_volatility")
        vol_state_feat = feature_set.Features.get("volatility_state")
        range_expansion_feat = feature_set.Features.get("range_expansion")

        rolling_vol = rolling_vol_feat.Value if rolling_vol_feat else 0.0
        vol_state = vol_state_feat.Value if vol_state_feat else "low"
        range_expansion = range_expansion_feat.Value if range_expansion_feat else 1.0

        return {
            "rolling_volatility": rolling_vol,
            "volatility_state": vol_state,
            "range_expansion": range_expansion
        }

class MomentumAnalysis:
    """Analyzes mathematical momentum, velocity, and rate of return indicators."""
    def analyze(self, candles: List[MarketDataPoint], feature_set: MarketFeatureSet) -> Dict[str, Any]:
        price_change_feat = feature_set.Features.get("price_change")
        pct_return_feat = feature_set.Features.get("percentage_return")

        price_change = price_change_feat.Value if price_change_feat else 0.0
        pct_return = pct_return_feat.Value if pct_return_feat else 0.0

        roc = pct_return * 100.0
        velocity = price_change / len(candles) if candles else 0.0

        momentum_state = "Neutral"
        if roc > 2.0:
            momentum_state = "Overbought / Extremely Strong Bullish Momentum"
        elif roc > 0.5:
            momentum_state = "Strong Bullish Momentum"
        elif roc < -2.0:
            momentum_state = "Oversold / Extremely Strong Bearish Momentum"
        elif roc < -0.5:
            momentum_state = "Strong Bearish Momentum"

        return {
            "rate_of_change_pct": roc,
            "price_velocity": velocity,
            "momentum_state": momentum_state
        }

class SmartInterpretationEngine:
    """Generates directional bias, confidence score, and qualitative reasoning array."""

    def interpret(
        self,
        candles: List[MarketDataPoint],
        tech: Dict[str, Any],
        trend: Dict[str, Any],
        vol: Dict[str, Any],
        mom: Dict[str, Any],
        regime: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not candles:
            return {
                "bias": "Neutral",
                "confidence": 50,
                "reasoning": ["No market data available."]
            }

        latest_close = candles[-1].Close
        support = tech.get("support", latest_close)
        resistance = tech.get("resistance", latest_close)
        trend_lbl = trend.get("direction_label", "Neutral")
        mom_state = mom.get("momentum_state", "Neutral")

        reasoning = []
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # 1. Pure Price Action relative to Market Support & Resistance
        if resistance > support:
            pos = (latest_close - support) / (resistance - support)
            if pos > 0.8:
                reasoning.append("Price action pressing against structural resistance zone (Liquidity sweep risk).")
                bearish_signals += 1
            elif pos < 0.2:
                reasoning.append("Price action retesting key structural support zone with potential demand reaction.")
                bullish_signals += 1
            else:
                reasoning.append("Price action oscillating within fair-value market equilibrium.")
                bullish_signals += 0.5
                bearish_signals += 0.5
            total_signals += 1

        # 2. Market Structure Trend Classification
        if trend_lbl == "Bullish":
            reasoning.append("Price structure exhibits Higher Highs and Higher Lows (Bullish Structure).")
            bullish_signals += 1.5
            total_signals += 1.5
        elif trend_lbl == "Bearish":
            reasoning.append("Price structure exhibits Lower Highs and Lower Lows (Bearish Structure).")
            bearish_signals += 1.5
            total_signals += 1.5

        # 3. Pure Price Action Momentum & Velocity
        if "Bullish" in mom_state:
            reasoning.append("Pure price velocity demonstrates bullish directional momentum.")
            bullish_signals += 1
            total_signals += 1
        elif "Bearish" in mom_state:
            reasoning.append("Pure price velocity demonstrates bearish directional momentum.")
            bearish_signals += 1
            total_signals += 1

        # Calculate final confidence score and bias
        bias = "Neutral"
        confidence = 50

        if total_signals > 0:
            bull_pct = bullish_signals / total_signals
            bear_pct = bearish_signals / total_signals

            if bull_pct > 0.6:
                bias = "Bullish"
                confidence = int(50 + (bull_pct - 0.5) * 100)
            elif bear_pct > 0.6:
                bias = "Bearish"
                confidence = int(50 + (bear_pct - 0.5) * 100)
            else:
                bias = "Neutral"
                confidence = int(50 + abs(bull_pct - bear_pct) * 50)

        confidence = min(max(confidence, 50), 95)

        return {
            "bias": bias,
            "confidence": confidence,
            "reasoning": reasoning
        }
