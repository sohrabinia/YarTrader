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

        # 1. Minimum Data Availability Check
        if n < 14:
            return {
                "support": support,
                "resistance": resistance,
                "highest_high": highest_high,
                "lowest_low": lowest_low,
                "swing_highs": swing_highs,
                "swing_lows": swing_lows,
                "mean": round(mean_price, 4),
                "std_dev": round(std_dev, 4),
                "insufficient_data": True,
                "sma_20": None,
                "sma_50": None,
                "ema_12": None,
                "ema_26": None,
                "macd": None,
                "macd_signal": None,
                "macd_histogram": None,
                "rsi": None,
                "atr": None,
                "upper_band": None,
                "lower_band": None
            }

        # 2. Moving Averages Calculation
        sma_20 = sum(closes[-20:]) / 20.0 if n >= 20 else None
        sma_50 = sum(closes[-50:]) / 50.0 if n >= 50 else None

        def calc_ema(series: List[float], period: int) -> Optional[float]:
            if len(series) < period:
                return None
            k = 2.0 / (period + 1.0)
            ema = sum(series[:period]) / float(period)
            for p in series[period:]:
                ema = (p * k) + (ema * (1.0 - k))
            return ema

        ema_12 = calc_ema(closes, 12)
        ema_26 = calc_ema(closes, 26)

        # 3. MACD Calculation (12, 26, 9)
        macd_val = None
        macd_sig = None
        macd_hist = None

        if len(closes) >= 35:  # 26 for EMA26 + 9 for signal
            ema12_series = []
            ema26_series = []
            k12 = 2.0 / (12 + 1)
            k26 = 2.0 / (26 + 1)

            e12 = sum(closes[:12]) / 12.0
            e26 = sum(closes[:26]) / 26.0

            for i in range(len(closes)):
                if i >= 12:
                    e12 = (closes[i] * k12) + (e12 * (1.0 - k12))
                if i >= 26:
                    e26 = (closes[i] * k26) + (e26 * (1.0 - k26))
                    macd_line = e12 - e26
                    ema12_series.append(macd_line)

            if len(ema12_series) >= 9:
                k9 = 2.0 / (9 + 1)
                macd_sig = sum(ema12_series[:9]) / 9.0
                for m_val in ema12_series[9:]:
                    macd_sig = (m_val * k9) + (macd_sig * (1.0 - k9))
                macd_val = ema12_series[-1]
                macd_hist = macd_val - macd_sig

        # 4. RSI Calculation (14-period Wilder)
        rsi_val = None
        if n >= 15:
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i - 1]
                gains.append(max(0.0, change))
                losses.append(max(0.0, -change))

            avg_gain = sum(gains[:14]) / 14.0
            avg_loss = sum(losses[:14]) / 14.0

            for i in range(14, len(gains)):
                avg_gain = (avg_gain * 13.0 + gains[i]) / 14.0
                avg_loss = (avg_loss * 13.0 + losses[i]) / 14.0

            if avg_loss == 0:
                rsi_val = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100.0 - (100.0 / (1.0 + rs))

        # 5. ATR Calculation (14-period)
        atr_val = None
        if n >= 15:
            tr_list = []
            for i in range(1, len(candles)):
                high = candles[i].High
                low = candles[i].Low
                prev_close = candles[i - 1].Close
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_list.append(tr)

            atr_val = sum(tr_list[:14]) / 14.0
            for tr in tr_list[14:]:
                atr_val = (atr_val * 13.0 + tr) / 14.0

        # 6. Bollinger Bands Calculation (20-period, 2-std-dev)
        upper_band = None
        lower_band = None
        if n >= 20:
            c20 = closes[-20:]
            m20 = sum(c20) / 20.0
            var20 = sum((x - m20) ** 2 for x in c20) / 20.0
            std20 = math.sqrt(var20)
            upper_band = m20 + (2.0 * std20)
            lower_band = m20 - (2.0 * std20)

        return {
            "support": round(support, 4),
            "resistance": round(resistance, 4),
            "highest_high": round(highest_high, 4),
            "lowest_low": round(lowest_low, 4),
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "mean": round(mean_price, 4),
            "std_dev": round(std_dev, 4),
            "insufficient_data": False if n >= 20 else True,
            "sma_20": round(sma_20, 4) if sma_20 is not None else None,
            "sma_50": round(sma_50, 4) if sma_50 is not None else None,
            "ema_12": round(ema_12, 4) if ema_12 is not None else None,
            "ema_26": round(ema_26, 4) if ema_26 is not None else None,
            "macd": round(macd_val, 4) if macd_val is not None else None,
            "macd_signal": round(macd_sig, 4) if macd_sig is not None else None,
            "macd_histogram": round(macd_hist, 4) if macd_hist is not None else None,
            "rsi": round(rsi_val, 4) if rsi_val is not None else None,
            "atr": round(atr_val, 4) if atr_val is not None else None,
            "upper_band": round(upper_band, 4) if upper_band is not None else None,
            "lower_band": round(lower_band, 4) if lower_band is not None else None
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
