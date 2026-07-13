import math
from datetime import datetime
from typing import List
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Features.interfaces import IFeatureCalculator
from src.Research.Features.models import FeatureValue


class PriceFeatureCalculator(IFeatureCalculator):
    """Calculates price features: Price Change, Percentage Return, and Price Range."""

    def calculate(self, data_points: List[MarketDataPoint]) -> List[FeatureValue]:
        if not data_points:
            raise ValidationException("Validation Error: Cannot calculate price features on empty data.")

        latest = data_points[-1]
        older = data_points[0]
        timestamp = latest.Timestamp

        # 1. Price Change
        price_change = latest.Close - older.Close

        # 2. Percentage Return
        pct_return = 0.0
        if older.Close > 0:
            pct_return = (latest.Close - older.Close) / older.Close

        # 3. Price Range
        highs = [dp.High for dp in data_points]
        lows = [dp.Low for dp in data_points]
        price_range = max(highs) - min(lows)

        return [
            FeatureValue("price_change", price_change, timestamp, {"older_close": older.Close, "latest_close": latest.Close}),
            FeatureValue("percentage_return", pct_return, timestamp, {}),
            FeatureValue("price_range", price_range, timestamp, {"max_high": max(highs), "min_low": min(lows)})
        ]


class VolatilityFeatureCalculator(IFeatureCalculator):
    """Calculates volatility features: Annualized Volatility, Range Expansion, and Volatility State."""

    def calculate(self, data_points: List[MarketDataPoint]) -> List[FeatureValue]:
        if not data_points:
            raise ValidationException("Validation Error: Cannot calculate volatility features on empty data.")

        latest = data_points[-1]
        timestamp = latest.Timestamp

        # 1. Rolling Volatility (annualized return volatility)
        log_returns = []
        for i in range(1, len(data_points)):
            prev_close = data_points[i-1].Close
            curr_close = data_points[i].Close
            if prev_close > 0 and curr_close > 0:
                log_returns.append(math.log(curr_close / prev_close))
            else:
                log_returns.append(0.0)

        rolling_vol = 0.0
        if len(log_returns) >= 2:
            mean_ret = sum(log_returns) / len(log_returns)
            variance = sum((r - mean_ret) ** 2 for r in log_returns) / (len(log_returns) - 1)
            standard_deviation = math.sqrt(variance)
            rolling_vol = standard_deviation * math.sqrt(252)

        # 2. Range Expansion
        # Average high-low range of all points
        ranges = [dp.High - dp.Low for dp in data_points]
        avg_range = sum(ranges) / len(ranges) if ranges else 0.0
        latest_range = latest.High - latest.Low

        range_expansion = 0.0
        if avg_range > 0:
            range_expansion = latest_range / avg_range

        # 3. Volatility State
        vol_state = "low"
        if rolling_vol >= 0.30:
            vol_state = "high"
        elif rolling_vol >= 0.15:
            vol_state = "medium"

        return [
            FeatureValue("rolling_volatility", rolling_vol, timestamp, {}),
            FeatureValue("range_expansion", range_expansion, timestamp, {"latest_range": latest_range, "avg_range": avg_range}),
            FeatureValue("volatility_state", vol_state, timestamp, {})
        ]


class TrendFeatureCalculator(IFeatureCalculator):
    """Calculates trend features: Directional Movement and Trend Strength Classification."""

    def calculate(self, data_points: List[MarketDataPoint]) -> List[FeatureValue]:
        if not data_points:
            raise ValidationException("Validation Error: Cannot calculate trend features on empty data.")

        latest = data_points[-1]
        older = data_points[0]
        timestamp = latest.Timestamp

        # 1. Directional Movement
        direction = 0.0
        if latest.Close > older.Close:
            direction = 1.0
        elif latest.Close < older.Close:
            direction = -1.0

        # 2. Trend Strength Classification based on percentage returns
        pct_return = 0.0
        if older.Close > 0:
            pct_return = (latest.Close - older.Close) / older.Close

        trend_strength = "neutral"
        if pct_return >= 0.05:
            trend_strength = "strong_bullish"
        elif pct_return >= 0.01:
            trend_strength = "weak_bullish"
        elif pct_return <= -0.05:
            trend_strength = "strong_bearish"
        elif pct_return <= -0.01:
            trend_strength = "weak_bearish"

        return [
            FeatureValue("directional_movement", direction, timestamp, {}),
            FeatureValue("trend_strength_classification", trend_strength, timestamp, {"percentage_return": pct_return})
        ]


class StatisticalFeatureCalculator(IFeatureCalculator):
    """Calculates statistical properties of Close prices: Mean, Standard Deviation, and Skewness."""

    def calculate(self, data_points: List[MarketDataPoint]) -> List[FeatureValue]:
        if not data_points:
            raise ValidationException("Validation Error: Cannot calculate statistical features on empty data.")

        latest = data_points[-1]
        timestamp = latest.Timestamp
        closes = [dp.Close for dp in data_points]

        # 1. Mean
        n = len(closes)
        mean_val = sum(closes) / n

        # 2. Standard Deviation
        variance = 0.0
        if n >= 2:
            variance = sum((c - mean_val) ** 2 for c in closes) / (n - 1)
        std_dev = math.sqrt(variance)

        # 3. Skewness
        skewness = 0.0
        if n >= 3 and std_dev > 0:
            m3 = sum((c - mean_val) ** 3 for c in closes) / n
            # Fisher-Pearson coefficient of skewness
            skewness = m3 / (std_dev ** 3)

        return [
            FeatureValue("mean", mean_val, timestamp, {}),
            FeatureValue("standard_deviation", std_dev, timestamp, {}),
            FeatureValue("skewness", skewness, timestamp, {})
        ]
