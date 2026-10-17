import pytest
from datetime import datetime, time, date, timedelta, timezone
from src.Execution.Services.market_session_engine import (
    MarketSessionEngine,
    MarketState,
    CalendarSourcePrecedence,
    SessionInterval,
    HolidayEvent,
    TPFeasibilityAssessment,
    MarketSessionValidationResult
)
from src.Execution.Services.session_execution_manager import SessionExecutionManager

class TestMarketSessionEngine:

    def setup_method(self):
        self.engine = MarketSessionEngine()
        self.now_utc = datetime(2026, 3, 23, 10, 0, 0, tzinfo=timezone.utc) # Monday 10:00 UTC

    def test_forex_normal_session_validation(self):
        interval = SessionInterval(
            session_id="XAUUSD_MON",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59),
            utc_start=datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 23, 59, 59, tzinfo=timezone.utc),
            source=CalendarSourcePrecedence.LIVE_BROKER_MT5
        )
        self.engine.register_session_interval(interval)

        res = self.engine.validate_pre_entry(
            symbol="XAUUSD",
            current_equity=10000.0, current_time=self.now_utc
        )

        assert res.allowed is True
        assert res.market_state == MarketState.OPEN
        assert res.rejection_reason is None
        assert res.remaining_session_seconds > 121.0

    def test_pre_entry_120s_threshold_boundary_matrix(self):
        session_start = datetime(2026, 3, 23, 9, 50, 0, tzinfo=timezone.utc)
        session_end = datetime(2026, 3, 23, 10, 2, 0, tzinfo=timezone.utc) # 120s from 10:00:00
        interval = SessionInterval(
            session_id="XAUUSD_SHORT",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(9, 50),
            session_end=time(10, 2),
            utc_start=session_start,
            utc_end=session_end,
            source=CalendarSourcePrecedence.LIVE_BROKER_MT5
        )
        self.engine.register_session_interval(interval)

        # Exact 120s remaining (at 10:00:00) -> REJECT
        res_120 = self.engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, current_time=self.now_utc)
        assert res_120.allowed is False
        assert res_120.rejection_reason == "INSUFFICIENT_SESSION_TIME"

        # 119.999s remaining -> REJECT
        t_119 = datetime(2026, 3, 23, 10, 0, 0, 1000, tzinfo=timezone.utc)
        res_119 = self.engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, current_time=t_119)
        assert res_119.allowed is False
        assert res_119.rejection_reason == "INSUFFICIENT_SESSION_TIME"

        # 121.001s remaining -> ACCEPT
        t_121 = session_end - timedelta(seconds=121.001)
        res_121 = self.engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, current_time=t_121)
        assert res_121.allowed is True
        assert res_121.rejection_reason is None

    def test_crypto_saturday_multiple_intervals(self):
        # Saturday multiple sessions: 08:00-12:00, 13:00-17:00
        sat_date = "2026-03-28"
        i1 = SessionInterval(
            session_id="BTC_SAT_1",
            broker="DEFAULT",
            symbol="BTCUSD",
            market="CRYPTO",
            date_str=sat_date,
            weekday=5,
            session_start=time(8, 0),
            session_end=time(12, 0),
            utc_start=datetime(2026, 3, 28, 8, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
        )
        i2 = SessionInterval(
            session_id="BTC_SAT_2",
            broker="DEFAULT",
            symbol="BTCUSD",
            market="CRYPTO",
            date_str=sat_date,
            weekday=5,
            session_start=time(13, 0),
            session_end=time(17, 0),
            utc_start=datetime(2026, 3, 28, 13, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 28, 17, 0, 0, tzinfo=timezone.utc)
        )
        self.engine.register_session_interval(i1)
        self.engine.register_session_interval(i2)

        # 09:00 -> Inside interval 1 -> OPEN
        t_09 = datetime(2026, 3, 28, 9, 0, 0, tzinfo=timezone.utc)
        res_09 = self.engine.validate_pre_entry(symbol="BTCUSD", current_equity=10000.0, current_time=t_09)
        assert res_09.allowed is True

        # 12:30 -> In break between interval 1 & 2 -> CLOSED
        t_1230 = datetime(2026, 3, 28, 12, 30, 0, tzinfo=timezone.utc)
        res_1230 = self.engine.validate_pre_entry(symbol="BTCUSD", current_equity=10000.0, current_time=t_1230)
        assert res_1230.allowed is False
        assert res_1230.rejection_reason == "MARKET_CLOSED"

        # 14:00 -> Inside interval 2 -> OPEN
        t_14 = datetime(2026, 3, 28, 14, 0, 0, tzinfo=timezone.utc)
        res_14 = self.engine.validate_pre_entry(symbol="BTCUSD", current_equity=10000.0, current_time=t_14)
        assert res_14.allowed is True

    def test_pre_entry_tp_time_feasibility_matrix(self):
        interval = SessionInterval(
            session_id="XAUUSD_MAIN",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(10, 0),
            session_end=time(10, 10),  # 600 seconds session
            utc_start=datetime(2026, 3, 23, 10, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 10, 10, 0, tzinfo=timezone.utc)
        )
        self.engine.register_session_interval(interval)

        # Scenario 1: TP estimated time 70 seconds -> REJECT (too fast, violates >120s hold rule)
        res_fast = self.engine.validate_pre_entry(
            symbol="XAUUSD",
            distance_to_tp=70.0,
            current_volatility_atr=1.0,
            historical_mfe_speed=1.0,
            current_equity=10000.0, current_time=self.now_utc
        )
        assert res_fast.allowed is False
        assert res_fast.rejection_reason == "TP_TIME_TOO_FAST_BELOW_MIN_HOLD_120S"

        # Scenario 2: TP estimated time 180 seconds, remaining session 600s -> ACCEPT
        res_valid = self.engine.validate_pre_entry(
            symbol="XAUUSD",
            distance_to_tp=180.0,
            current_volatility_atr=1.0,
            historical_mfe_speed=1.0,
            current_equity=10000.0, current_time=self.now_utc
        )
        assert res_valid.allowed is True
        assert res_valid.rejection_reason is None

        # Scenario 3: TP estimated time 700 seconds, remaining session 600s -> REJECT (exceeds remaining session)
        res_slow = self.engine.validate_pre_entry(
            symbol="XAUUSD",
            distance_to_tp=700.0,
            current_volatility_atr=1.0,
            historical_mfe_speed=1.0,
            current_equity=10000.0, current_time=self.now_utc
        )
        assert res_slow.allowed is False
        assert res_slow.rejection_reason == "TP_TIME_EXCEEDS_REMAINING_SESSION"

    def test_forexfactory_advisory_enrichment_precedence(self):
        # ForexFactory advisory event does NOT close live broker session unless Bank Holiday override
        self.engine.enrich_from_forexfactory([
            {
                "id": "ff_001",
                "title": "US NFP Payrolls",
                "currency": "USD",
                "impact": "HIGH",
                "date": "2026-03-23"
            }
        ])

        interval = SessionInterval(
            session_id="XAUUSD_MAIN",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59),
            utc_start=datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 23, 59, 59, tzinfo=timezone.utc),
            source=CalendarSourcePrecedence.LIVE_BROKER_MT5
        )
        self.engine.register_session_interval(interval)

        res = self.engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, current_time=self.now_utc)
        assert res.allowed is True
        assert res.source_authority == CalendarSourcePrecedence.LIVE_BROKER_MT5
        assert len(self.engine.forexfactory_enrichment) == 1

    def test_holiday_bank_holiday_closure(self):
        hol = HolidayEvent(
            event_id="hol_christmas",
            name="Christmas Bank Holiday",
            date_str="2026-03-23",
            currency_or_market="XAUUSD",
            impact="BANK_HOLIDAY",
            source=CalendarSourcePrecedence.BROKER_HOLIDAY_SCHEDULE
        )
        self.engine.register_holiday_event(hol)

        interval = SessionInterval(
            session_id="XAUUSD_MAIN",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59),
            utc_start=datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 23, 59, 59, tzinfo=timezone.utc)
        )
        self.engine.register_session_interval(interval)

        res = self.engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, current_time=self.now_utc)
        assert res.allowed is False
        assert res.market_state == MarketState.HOLIDAY_CLOSED
        assert res.rejection_reason == "HOLIDAY_CLOSED"

    def test_failure_injection_unknown_broker_schedule_fails_closed(self):
        # Empty engine without registered symbol schedule
        res = self.engine.validate_pre_entry(symbol="UNKNOWN_SYMBOL", current_equity=10000.0, current_time=self.now_utc)
        assert res.allowed is False
        assert res.market_state == MarketState.UNKNOWN
        assert res.rejection_reason == "UNKNOWN_BROKER_SCHEDULE"

    def test_daily_loss_gate_fails_closed_without_authoritative_equity(self):
        interval = SessionInterval(
            session_id="XAUUSD_MAIN",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59),
            utc_start=datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 23, 59, 59, tzinfo=timezone.utc),
            source=CalendarSourcePrecedence.LIVE_BROKER_MT5
        )
        self.engine.register_session_interval(interval)
        res = self.engine.validate_pre_entry(symbol="XAUUSD", current_time=self.now_utc)
        assert res.allowed is False
        assert res.rejection_reason == "ACCOUNT_EQUITY_UNAVAILABLE"

    def test_session_execution_manager_integration(self):
        interval = SessionInterval(
            session_id="XAUUSD_MAIN",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59),
            utc_start=datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc),
            utc_end=datetime(2026, 3, 23, 23, 59, 59, tzinfo=timezone.utc)
        )
        self.engine.register_session_interval(interval)

        manager = SessionExecutionManager(market_session_engine=self.engine)

        perm = manager.evaluate_entry_permission(
            trading_style="BASE_HIERARCHY",
            remaining_session_seconds=5000.0,
            symbol="XAUUSD",
            distance_to_tp=180.0,
            current_volatility_atr=1.0,
            current_equity=10000.0, current_time=self.now_utc
        )

        assert perm["allowed"] is True
        assert perm["rejection_reason"] is None

    def test_session_execution_manager_exit_permission_strict_120s(self):
        manager = SessionExecutionManager(market_session_engine=self.engine)

        # 120.000s -> REJECT
        res_120 = manager.evaluate_exit_permission(holding_duration_seconds=120.000, exit_reason="NORMAL_TAKE_PROFIT")
        assert res_120["allowed"] is False
        assert res_120["rejection_reason"] == "EARLY_EXIT_BLOCKED_MIN_HOLD_120S"

        # 120.001s -> ACCEPT
        res_120_1 = manager.evaluate_exit_permission(holding_duration_seconds=120.001, exit_reason="NORMAL_TAKE_PROFIT")
        assert res_120_1["allowed"] is True
        assert res_120_1["rejection_reason"] is None

    def test_session_interval_provenance_hash(self):
        interval = SessionInterval(
            session_id="XAUUSD_HASH_TEST",
            broker="ALPARI",
            symbol="XAUUSD",
            market="FOREX",
            date_str="2026-03-23",
            weekday=0,
            session_start=time(0, 0),
            session_end=time(23, 59, 59)
        )
        h = interval.compute_hash()
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 length


class TestRecurringLiveMarketCalendar:
    def test_live_calendar_closes_fx_weekend_and_rollover(self):
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        assert not MarketSessionEngine.live_activity_status("XAUUSD", datetime(2026, 10, 18, 16, 0, tzinfo=ny))["allowed"]
        assert MarketSessionEngine.live_activity_status("XAUUSD", datetime(2026, 10, 18, 18, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("XAUUSD", datetime(2026, 10, 16, 17, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("EURUSD", datetime(2026, 10, 19, 17, 2, tzinfo=ny))["allowed"]
        assert MarketSessionEngine.live_activity_status("EURUSD", datetime(2026, 10, 19, 17, 6, tzinfo=ny))["allowed"]

    def test_live_calendar_closes_major_fx_holidays_and_configured_holidays(self, monkeypatch):
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        christmas = datetime(2026, 12, 25, 10, 0, tzinfo=ny)
        assert MarketSessionEngine.live_activity_status("XAUUSD", christmas)["reason"] == "MARKET_HOLIDAY"
        monkeypatch.setenv("YARTRADER_MARKET_HOLIDAYS", "XAUUSD:2026-10-21,EURUSD:2026-10-22")
        assert not MarketSessionEngine.live_activity_status("XAUUSD", datetime(2026, 10, 21, 10, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("EURUSD", datetime(2026, 10, 22, 10, 0, tzinfo=ny))["allowed"]
        assert MarketSessionEngine.live_activity_status("EURUSD", datetime(2026, 10, 21, 10, 0, tzinfo=ny))["allowed"]

    def test_us_equity_hours_holidays_and_early_close(self):
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        assert MarketSessionEngine.live_activity_status("AAPL", datetime(2026, 10, 19, 10, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("AAPL", datetime(2026, 10, 19, 8, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("AAPL", datetime(2026, 11, 26, 10, 0, tzinfo=ny))["allowed"]
        assert not MarketSessionEngine.live_activity_status("AAPL", datetime(2026, 11, 27, 14, 0, tzinfo=ny))["allowed"]

    def test_unknown_market_calendar_fails_closed_and_backtest_remains_allowed(self):
        result = MarketSessionEngine.live_activity_status("UNLISTED_ASSET", datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc))
        assert not result["allowed"]
        assert result["reason"] == "UNSUPPORTED_MARKET_CALENDAR"
        assert result["backtest_allowed"] is True

    def test_registered_calendar_fallback_uses_recurring_session(self):
        engine = MarketSessionEngine()
        now = datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc)
        state, interval, source = engine.get_market_state("XAUUSD", current_time=now)
        assert state == MarketState.OPEN
        assert interval is not None and interval.utc_end is not None
        assert interval.utc_end > now

    def test_market_hours_are_configurable(self, monkeypatch):
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        monkeypatch.setenv("YARTRADER_FX_SUNDAY_OPEN", "18:00")
        assert not MarketSessionEngine.live_activity_status("XAUUSD", datetime(2026, 10, 18, 17, 30, tzinfo=ny))["allowed"]
        monkeypatch.setenv("YARTRADER_EQUITY_OPEN", "10:00")
        assert not MarketSessionEngine.live_activity_status("AAPL", datetime(2026, 10, 19, 9, 45, tzinfo=ny))["allowed"]
