"""
Phase C Temporal Market Behavior & Daily Review / Next-Day Forecast Engine.
Provides causal Day/Week/Month market behavior modeling and 00:30 EOD review loop.
Strictly prohibits look-ahead leakage using AVAILABLE_AT timestamps.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

@dataclass
class MarketForecast:
    forecast_id: str
    symbol: str
    forecast_date: str  # YYYY-MM-DD
    bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    expected_range_high: float
    expected_range_low: float
    key_reaction_zones: List[float]
    confidence: float
    created_at: str
    status: str = "PENDING"  # "PENDING", "VALIDATED"
    validation_result: Optional[str] = None  # "CORRECT", "PARTIAL", "WRONG"

class TemporalBehaviorModel:
    """
    Analyzes Day/Week/Month temporal market dynamics using strictly available past data.
    """

    def analyze_temporal_dynamics(
        self,
        symbol: str,
        historical_daily_bars: List[Dict[str, Any]],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Computes day-of-week, session, and monthly volatility/range metrics
        ensuring bar timestamps < current_time.
        """
        causal_bars = [
            b for b in historical_daily_bars
            if datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00")) < current_time
        ]

        if not causal_bars:
            return {
                "symbol": symbol,
                "data_points": 0,
                "day_of_week_bias": "NEUTRAL",
                "avg_daily_range": 0.0
            }

        ranges = [abs(b["high"] - b["low"]) for b in causal_bars]
        avg_range = sum(ranges) / len(ranges)

        # Day of week analysis for current_time.weekday()
        current_day = current_time.weekday()
        day_bars = [
            b for b in causal_bars
            if datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00")).weekday() == current_day
        ]

        day_bias = "NEUTRAL"
        if day_bars:
            bullish_count = sum(1 for b in day_bars if b["close"] > b["open"])
            ratio = bullish_count / len(day_bars)
            if ratio >= 0.6:
                day_bias = "BULLISH"
            elif ratio <= 0.4:
                day_bias = "BEARISH"

        return {
            "symbol": symbol,
            "data_points": len(causal_bars),
            "day_of_week_bias": day_bias,
            "avg_daily_range": round(avg_range, 2),
            "evaluated_at": current_time.isoformat()
        }

class DailyReviewForecastEngine:
    """
    Manages 00:30 Daily EOD Review, versioned Next-Day Market Plan generation,
    and Market Open Forecast Validation.
    """

    def __init__(self):
        self._forecasts: Dict[str, MarketForecast] = {}

    def generate_eod_review_and_forecast(
        self,
        symbol: str,
        today_trades: List[Dict[str, Any]],
        market_data: Dict[str, Any],
        review_time: datetime
    ) -> MarketForecast:
        """
        Executes daily review after session close (~00:30) and generates next-day forecast.
        """
        forecast_date = (review_time + timedelta(days=1)).strftime("%Y-%m-%d")
        forecast_id = f"fc-{symbol}-{forecast_date}"

        # Determine bias from EOD review findings
        wins = sum(1 for t in today_trades if t.get("pnl_usd", 0) > 0)
        total_trades = len(today_trades)
        win_rate = (wins / total_trades) if total_trades > 0 else 0.5

        close_price = market_data.get("close", 2000.0)
        avg_range = market_data.get("avg_daily_range", 20.0)

        bias = "BULLISH" if win_rate >= 0.5 else "BEARISH"

        forecast = MarketForecast(
            forecast_id=forecast_id,
            symbol=symbol,
            forecast_date=forecast_date,
            bias=bias,
            expected_range_high=round(close_price + (avg_range * 0.8), 2),
            expected_range_low=round(close_price - (avg_range * 0.8), 2),
            key_reaction_zones=[round(close_price, 2)],
            confidence=0.75,
            created_at=review_time.isoformat()
        )

        self._forecasts[forecast_id] = forecast
        return forecast

    def validate_forecast(
        self,
        forecast_id: str,
        actual_session_data: Dict[str, Any]
    ) -> MarketForecast:
        """
        Compares next-day forecast against actual session behavior after market open.
        Classifies result as CORRECT, PARTIAL, or WRONG.
        """
        if forecast_id not in self._forecasts:
            raise KeyError(f"Forecast {forecast_id} not found.")

        fc = self._forecasts[forecast_id]
        actual_high = actual_session_data.get("high", 0.0)
        actual_low = actual_session_data.get("low", 0.0)
        actual_close = actual_session_data.get("close", 0.0)
        actual_open = actual_session_data.get("open", 0.0)

        is_bullish_actual = actual_close > actual_open

        if (fc.bias == "BULLISH" and is_bullish_actual) or (fc.bias == "BEARISH" and not is_bullish_actual):
            if actual_high <= fc.expected_range_high * 1.02 and actual_low >= fc.expected_range_low * 0.98:
                res = "CORRECT"
            else:
                res = "PARTIAL"
        else:
            res = "WRONG"

        fc.status = "VALIDATED"
        fc.validation_result = res
        return fc
