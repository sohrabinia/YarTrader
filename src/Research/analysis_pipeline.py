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

        # 1. Moving Averages
        sma_20 = sum(closes[-20:]) / min(n, 20) if n > 0 else 0.0
        sma_50 = sum(closes[-50:]) / min(n, 50) if n > 0 else 0.0

        def calculate_ema(prices: List[float], period: int) -> List[float]:
            if not prices:
                return []
            ema = []
            multiplier = 2 / (period + 1)
            current_ema = sum(prices[:period]) / min(len(prices), period)
            for i, price in enumerate(prices):
                if i < period:
                    ema.append(current_ema)
                else:
                    current_ema = (price - current_ema) * multiplier + current_ema
                    ema.append(current_ema)
            return ema

        ema_12_list = calculate_ema(closes, 12)
        ema_26_list = calculate_ema(closes, 26)

        # 2. MACD Calculation
        macd_line = 0.0
        signal_line = 0.0
        histogram = 0.0
        if len(ema_12_list) == len(closes) and len(ema_26_list) == len(closes) and n >= 26:
            macd_series = [e12 - e26 for e12, e26 in zip(ema_12_list, ema_26_list)]
            macd_line = macd_series[-1]
            signal_series = calculate_ema(macd_series, 9)
            if signal_series:
                signal_line = signal_series[-1]
                histogram = macd_line - signal_line

        # 3. RSI Calculation
        rsi = 50.0
        if n >= 15:
            gains = []
            losses = []
            for i in range(1, n):
                diff = closes[i] - closes[i-1]
                gains.append(max(diff, 0.0))
                losses.append(max(-diff, 0.0))

            avg_gain = sum(gains[:14]) / 14
            avg_loss = sum(losses[:14]) / 14
            for i in range(14, len(gains)):
                avg_gain = (avg_gain * 13 + gains[i]) / 14
                avg_loss = (avg_loss * 13 + losses[i]) / 14

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100.0 if avg_gain > 0 else 50.0

        # 4. ATR Calculation
        atr = 0.0
        if n >= 2:
            tr_list = []
            for i in range(1, n):
                h = highs[i]
                l = lows[i]
                c_prev = closes[i-1]
                tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
                tr_list.append(tr)

            if tr_list:
                period = min(len(tr_list), 14)
                atr = sum(tr_list[-period:]) / period

        # 5. Support & Resistance Detection
        support = min(lows[-20:]) if n >= 20 else (min(lows) if lows else 0.0)
        resistance = max(highs[-20:]) if n >= 20 else (max(highs) if highs else 0.0)

        # 6. Basic Moving Average Bands
        mean = sum(closes) / n if n > 0 else 0.0
        variance = sum((c - mean) ** 2 for c in closes) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)
        upper_band = mean + 2 * std_dev
        lower_band = mean - 2 * std_dev

        return {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "ema_12": ema_12_list[-1] if ema_12_list else 0.0,
            "ema_26": ema_26_list[-1] if ema_26_list else 0.0,
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
            "rsi": rsi,
            "atr": atr,
            "support": support,
            "resistance": resistance,
            "mean": mean,
            "std_dev": std_dev,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "highest_high": max(highs) if highs else 0.0,
            "lowest_low": min(lows) if lows else 0.0
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
        sma_20 = tech.get("sma_20", latest_close)
        rsi = tech.get("rsi", 50.0)
        macd = tech.get("macd", 0.0)
        trend_lbl = trend.get("direction_label", "Neutral")
        mom_state = mom.get("momentum_state", "Neutral")

        reasoning = []
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # 1. Price vs. SMA 20
        if latest_close > sma_20:
            reasoning.append("Price is trading above the SMA20 short-term trend line.")
            bullish_signals += 1
        else:
            reasoning.append("Price is trading below the SMA20 short-term trend line.")
            bearish_signals += 1
        total_signals += 1

        # 2. RSI Checks
        if rsi > 70.0:
            reasoning.append("RSI is overbought (>70), suggesting potential short-term exhaustion.")
            bearish_signals += 1
            total_signals += 1
        elif rsi < 30.0:
            reasoning.append("RSI is oversold (<30), indicating potential demand-side exhaustion.")
            bullish_signals += 1
            total_signals += 1
        elif rsi > 50.0:
            reasoning.append("RSI is in bullish territory (>50) with positive buying pressure.")
            bullish_signals += 0.5
            total_signals += 0.5
        else:
            reasoning.append("RSI is in bearish territory (<50) with active selling pressure.")
            bearish_signals += 0.5
            total_signals += 0.5

        # 3. MACD
        if macd > 0:
            reasoning.append("MACD histogram remains above zero, confirming upward momentum.")
            bullish_signals += 1
        else:
            reasoning.append("MACD histogram remains below zero, confirming downward momentum.")
            bearish_signals += 1
        total_signals += 1

        # 4. Trend Direction
        if trend_lbl == "Bullish":
            reasoning.append("Trend direction classification indicates sustained bullish flow.")
            bullish_signals += 1.5
            total_signals += 1.5
        elif trend_lbl == "Bearish":
            reasoning.append("Trend direction classification indicates sustained bearish flow.")
            bearish_signals += 1.5
            total_signals += 1.5

        # 5. Momentum Condition
        if "Bullish" in mom_state:
            reasoning.append("Rate of Return (ROC) velocity exhibits expanding bullish acceleration.")
            bullish_signals += 1
            total_signals += 1
        elif "Bearish" in mom_state:
            reasoning.append("Rate of Return (ROC) velocity exhibits expanding bearish acceleration.")
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
