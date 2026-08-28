import pytest
from datetime import datetime, timezone, timedelta
from src.Research.Brain.temporal_forecast_engine import TemporalBehaviorModel, DailyReviewForecastEngine

class TestPhaseCTemporalForecast:
    def test_causal_temporal_behavior_no_lookahead(self):
        model = TemporalBehaviorModel()
        now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)

        bars = [
            {"timestamp": "2026-03-08T00:00:00+00:00", "open": 2000.0, "high": 2010.0, "low": 1990.0, "close": 2005.0},
            {"timestamp": "2026-03-09T00:00:00+00:00", "open": 2005.0, "high": 2020.0, "low": 2000.0, "close": 2015.0},
            {"timestamp": "2026-03-11T00:00:00+00:00", "open": 2015.0, "high": 2030.0, "low": 2010.0, "close": 2025.0}, # Future bar!
        ]

        res = model.analyze_temporal_dynamics("XAUUSD", bars, now)
        # Should only evaluate first 2 bars
        assert res["data_points"] == 2
        assert res["avg_daily_range"] == 20.0

    def test_eod_review_and_forecast_validation_cycle(self):
        engine = DailyReviewForecastEngine()
        review_time = datetime(2026, 3, 10, 0, 30, 0, tzinfo=timezone.utc)
        today_trades = [{"pnl_usd": 150.0}, {"pnl_usd": -50.0}, {"pnl_usd": 80.0}]
        market_data = {"close": 2020.0, "avg_daily_range": 25.0}

        forecast = engine.generate_eod_review_and_forecast("XAUUSD", today_trades, market_data, review_time)
        assert forecast.bias == "BULLISH"
        assert forecast.forecast_date == "2026-03-11"

        actual_session = {
            "open": 2020.0,
            "high": 2035.0,
            "low": 2010.0,
            "close": 2030.0
        }

        validated = engine.validate_forecast(forecast.forecast_id, actual_session)
        assert validated.status == "VALIDATED"
        assert validated.validation_result in ["CORRECT", "PARTIAL"]
