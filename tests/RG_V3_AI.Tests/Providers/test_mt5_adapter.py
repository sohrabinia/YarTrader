import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import src.Data.Providers.MT5.mt5 as mt5_module
from src.Data.Market.models import MarketInstrument, MarketDataRequest
from src.Data.Providers.MT5.mt5 import MT5DataProvider, MT5ConnectionHealth, MT5DataMapper
from src.Data.External.models import ExternalDataRequest, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException

# Setup dynamic mocking for MetaTrader5 library
mock_mt5 = MagicMock()
mock_mt5.initialize.return_value = True

mock_term_info = MagicMock()
mock_term_info.connected = True
mock_mt5.terminal_info.return_value = mock_term_info

mock_mt5.symbols_get.return_value = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
mock_mt5.account_info.return_value = None  # to preserve original custom server name tests
mock_mt5.last_error.return_value = (0, "Success")

mock_mt5.TIMEFRAME_M1 = 1
mock_mt5.TIMEFRAME_M5 = 5
mock_mt5.TIMEFRAME_M15 = 15
mock_mt5.TIMEFRAME_M30 = 30
mock_mt5.TIMEFRAME_H1 = 16385
mock_mt5.TIMEFRAME_H4 = 16388
mock_mt5.TIMEFRAME_D1 = 16408

def mock_copy_rates_range(symbol, timeframe, date_from, date_to):
    base_price = 1.1000 if "JPY" not in symbol else 145.0
    if "XAU" in symbol:
        base_price = 1800.0
    increment = 0.0001 if "JPY" not in symbol and "XAU" not in symbol else 0.01

    rates = []
    curr = date_from
    for i in range(10):
        if curr > date_to:
            break
        rates.append({
            "time": int(curr.timestamp()),
            "open": base_price + i * increment,
            "high": base_price + (i + 2) * increment,
            "low": base_price + (i - 1) * increment,
            "close": base_price + (i + 1) * increment,
            "tick_volume": 150.0 + i * 10
        })
        curr += timedelta(minutes=15)
    return rates

mock_mt5.copy_rates_range.side_effect = mock_copy_rates_range

# Save original values to restore in tearDown if needed
ORIG_AVAILABLE = mt5_module.MT5_AVAILABLE
ORIG_MT5 = mt5_module.mt5

# Apply mock by default for tests
mt5_module.mt5 = mock_mt5
mt5_module.MT5_AVAILABLE = True


class TestMT5AdapterAndMapper(unittest.TestCase):
    """
    Test suite verifying the read-only MT5 Data Provider connection health,
    rates-to-candles mapping, and validation failure scenarios. (33 unit tests)
    """

    def setUp(self) -> None:
        # Reset mock state before each test
        mt5_module.mt5 = mock_mt5
        mt5_module.MT5_AVAILABLE = True
        mock_mt5.initialize.return_value = True
        mock_term_info.connected = True
        mock_mt5.terminal_info.return_value = mock_term_info
        mock_mt5.symbols_get.return_value = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        mock_mt5.account_info.return_value = None
        mock_mt5.last_error.return_value = (0, "Success")
        mock_mt5.copy_rates_range.side_effect = mock_copy_rates_range

        self.provider = MT5DataProvider(provider_id="mt5-test", server="Demo-Server")
        self.mapper = MT5DataMapper()
        self.instrument = MarketInstrument("EURUSD", "FX")
        self.now = datetime.now()

    def tearDown(self) -> None:
        # Restore original module states
        mt5_module.MT5_AVAILABLE = ORIG_AVAILABLE
        mt5_module.mt5 = ORIG_MT5

    # 1. Connection Health Tests (10 tests)
    def test_connection_1_default_state_healthy(self) -> None:
        health = self.provider.get_connection_health()
        self.assertTrue(health.connected)
        self.assertEqual(health.server, "Demo-Server")
        self.assertIsNone(health.last_error)

    def test_connection_2_offline_reported_unhealthy(self) -> None:
        self.provider.set_connected(False)
        health = self.provider.get_connection_health()
        self.assertFalse(health.connected)
        self.assertIsNotNone(health.last_error)
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.UNHEALTHY)

    def test_connection_3_check_health_status(self) -> None:
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.HEALTHY)

    def test_connection_4_metadata_correctness(self) -> None:
        meta = self.provider.metadata
        self.assertEqual(meta.provider_id, "mt5-test")
        self.assertIn("EURUSD", meta.supported_symbols)

    def test_connection_5_custom_server_name(self) -> None:
        p = MT5DataProvider(server="Live-Server")
        health = p.get_connection_health()
        self.assertEqual(health.server, "Live-Server")

    def test_connection_6_latency_reported_when_online(self) -> None:
        health = self.provider.get_connection_health()
        self.assertGreater(health.ping_ms, 0.0)

    def test_connection_7_latency_is_zero_when_offline(self) -> None:
        self.provider.set_connected(False)
        health = self.provider.get_connection_health()
        self.assertEqual(health.ping_ms, 0.0)

    def test_connection_8_degraded_on_high_ping(self) -> None:
        self.provider._ping = 150.0  # mock high ping
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.DEGRADED)

    def test_connection_9_supports_symbol_checks_FX(self) -> None:
        self.assertEqual(self.instrument.asset_class, "FX")

    def test_connection_10_instrument_default_parameters(self) -> None:
        self.assertEqual(self.instrument.digits, 5)
        self.assertEqual(self.instrument.contract_size, 100000.0)

    # 2. Data Mapper Tests (10 tests)
    def test_mapper_1_rates_mapping_to_candles_success(self) -> None:
        raw_rates = [
            {"time": 1600000000, "open": 1.1000, "high": 1.1020, "low": 1.0990, "close": 1.1010, "tick_volume": 100},
            {"timestamp": "2023-01-01T12:00:00", "open": 1.1010, "high": 1.1030, "low": 1.1000, "close": 1.1020, "volume": 120}
        ]
        candles = self.mapper.map_rates_to_candles(raw_rates)
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0].open, 1.1000)
        self.assertEqual(candles[0].volume, 100.0)
        self.assertEqual(candles[1].timestamp, datetime.fromisoformat("2023-01-01T12:00:00"))

    def test_mapper_2_missing_timestamp_skipped_silently(self) -> None:
        raw = [{"open": 1.1000, "high": 1.1020, "low": 1.0990, "close": 1.1010}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(len(candles), 0)

    def test_mapper_3_invalid_timestamp_skipped_silently(self) -> None:
        raw = [{"time": "not-valid", "open": 1.1}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(len(candles), 0)

    def test_mapper_4_missing_ohlcv_metric_raises_validation_exception(self) -> None:
        raw = [{"time": 1600000000, "open": "not-a-float"}]
        with self.assertRaises(ValidationException):
            self.mapper.map_rates_to_candles(raw)

    def test_mapper_5_none_metric_conversion_raises_validation_exception(self) -> None:
        raw = [{"time": 1600000000, "open": None, "high": 1.1}]
        with self.assertRaises(ValidationException):
            self.mapper.map_rates_to_candles(raw)

    def test_mapper_6_empty_list_mapping_returns_empty_candles(self) -> None:
        candles = self.mapper.map_rates_to_candles([])
        self.assertEqual(len(candles), 0)

    def test_mapper_7_float_volume_conversion_is_correct(self) -> None:
        raw = [{"time": 1600000000, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "tick_volume": "100"}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(candles[0].volume, 100.0)

    def test_mapper_8_tick_volume_preferred_over_volume(self) -> None:
        raw = [{"time": 1600000000, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "tick_volume": 10.0, "volume": 20.0}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(candles[0].volume, 10.0)

    def test_mapper_9_volume_fallback_when_tick_volume_missing(self) -> None:
        raw = [{"time": 1600000000, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "volume": 20.0}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(candles[0].volume, 20.0)

    def test_mapper_10_datetime_timestamp_mapped_directly(self) -> None:
        raw = [{"time": self.now, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1}]
        candles = self.mapper.map_rates_to_candles(raw)
        self.assertEqual(candles[0].timestamp, self.now)

    # 3. Validation & Failure Tests (10 tests)
    def test_failure_1_fetch_data_when_offline_fails(self) -> None:
        self.provider.set_connected(False)
        req = ExternalDataRequest("EURUSD", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success)
        self.assertIn("Connection lost to MT5 terminal", resp.error_message)

    def test_failure_2_fetch_market_data_when_offline_fails(self) -> None:
        self.provider.set_connected(False)
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertFalse(resp.is_success)
        self.assertIn("Connection lost to MT5 terminal", resp.error_message)

    def test_failure_3_fetch_market_data_unsuccessful_fetch_propagates_failure(self) -> None:
        # Simulate copy_rates_range and fallback copy_rates_from_pos both returning None
        mock_mt5.copy_rates_range.side_effect = None
        mock_mt5.copy_rates_range.return_value = None
        mock_mt5.copy_rates_from_pos.side_effect = None
        mock_mt5.copy_rates_from_pos.return_value = None
        mock_mt5.last_error.return_value = (-1, "Symbol not found")

        inst = MarketInstrument("EURUSD", "FX")
        req = MarketDataRequest(inst, "M15", self.now - timedelta(hours=1), self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertFalse(resp.is_success)
        self.assertIn("Symbol not found", resp.error_message)

    def test_failure_4_fetch_data_valid_simulates_rates(self) -> None:
        req = ExternalDataRequest("EURUSD", "M15", self.now - timedelta(hours=2), self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(len(resp.raw_data), 9)

    def test_failure_5_fetch_market_data_returns_typed_response(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now - timedelta(hours=2), self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(len(resp.candles), 9)
        self.assertEqual(resp.candles[0].open, 1.1000)

    def test_failure_6_metadata_timestamp_recorded(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertIsNotNone(resp.metadata.retrieved_at)

    def test_failure_7_latency_recorded_on_fetch_market_data(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertGreaterEqual(resp.metadata.latency_ms, 0.0)

    def test_failure_8_server_name_preserved_in_metadata(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertEqual(resp.metadata.additional_properties["server"], "Demo-Server")

    def test_failure_9_jpy_pairs_rates_pricing_scaled_correctly(self) -> None:
        inst = MarketInstrument("USDJPY", "FX")
        req = MarketDataRequest(inst, "M15", self.now - timedelta(hours=2), self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertEqual(resp.candles[0].open, 145.0)

    def test_failure_10_fetch_market_data_respects_end_time_limit(self) -> None:
        # short window
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now + timedelta(minutes=5))
        resp = self.provider.fetch_market_data(req)
        self.assertEqual(len(resp.candles), 1)

    # 4. New Phase 24 real MT5 Integration tests
    def test_new_1_mt5_initialization_health(self) -> None:
        """Test 1: Verify MT5 initialization health reports connected=True."""
        health = self.provider.get_connection_health()
        self.assertTrue(health.connected)
        self.assertIsNone(health.last_error)

    def test_new_2_xauusd_h1_retrieval(self) -> None:
        """Test 2: Verify XAUUSD H1 retrieval fetches and maps valid candles."""
        req = MarketDataRequest(
            instrument=MarketInstrument("XAUUSD", "Metals"),
            timeframe="H1",
            start_time=self.now - timedelta(hours=5),
            end_time=self.now
        )
        resp = self.provider.fetch_market_data(req)
        self.assertTrue(resp.is_success)
        self.assertGreater(len(resp.candles), 0)

        # Verify candle properties
        candle = resp.candles[0]
        self.assertGreater(candle.open, 0.0)
        self.assertGreater(candle.close, 0.0)
        self.assertGreater(candle.high, 0.0)
        self.assertGreater(candle.low, 0.0)

    def test_new_3_failure_handling_unavailable(self) -> None:
        """Test 3: Verify failure handling when MT5 package/terminal is simulated unavailable."""
        try:
            # Simulate MT5 unavailable
            mt5_module.MT5_AVAILABLE = False
            mt5_module.mt5 = None

            p = MT5DataProvider(provider_id="mt5-failed-test")
            health = p.get_connection_health()
            self.assertFalse(health.connected)

            req = MarketDataRequest(
                instrument=MarketInstrument("XAUUSD", "Metals"),
                timeframe="H1",
                start_time=self.now - timedelta(hours=5),
                end_time=self.now
            )
            resp = p.fetch_market_data(req)
            self.assertFalse(resp.is_success)
            self.assertIsNotNone(resp.error_message)
        finally:
            # Setup will restore, but let's be safe here
            mt5_module.MT5_AVAILABLE = True
            mt5_module.mt5 = mock_mt5

    # 5. Regression Tests for Timezone and Range Validation
    def test_regression_naive_datetime_input(self) -> None:
        """Verify naive datetimes get converted to UTC correctly."""
        from datetime import timezone
        start_naive = datetime(2026, 1, 1, 10, 0, 0)
        end_naive = datetime(2026, 1, 1, 12, 0, 0)

        # Hook mock to inspect parameters
        calls = []
        def inspect_copy_rates_range(symbol, tf, date_from, date_to):
            calls.append((date_from, date_to))
            return mock_copy_rates_range(symbol, tf, date_from, date_to)
        mock_mt5.copy_rates_range.side_effect = inspect_copy_rates_range

        req = ExternalDataRequest("XAUUSD", "H1", start_naive, end_naive)
        resp = self.provider.fetch_data(req)

        self.assertTrue(resp.is_success)
        self.assertEqual(len(calls), 1)
        p_start, p_end = calls[0]
        self.assertEqual(p_start.tzinfo, timezone.utc)
        self.assertEqual(p_end.tzinfo, timezone.utc)

    def test_regression_timezone_aware_datetime_input(self) -> None:
        """Verify timezone-aware datetimes preserve their timezone info."""
        from datetime import timezone, timedelta
        tz_east = timezone(timedelta(hours=3))
        start_aware = datetime(2026, 1, 1, 10, 0, 0, tzinfo=tz_east)
        end_aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=tz_east)

        calls = []
        def inspect_copy_rates_range(symbol, tf, date_from, date_to):
            calls.append((date_from, date_to))
            return mock_copy_rates_range(symbol, tf, date_from, date_to)
        mock_mt5.copy_rates_range.side_effect = inspect_copy_rates_range

        req = ExternalDataRequest("XAUUSD", "H1", start_aware, end_aware)
        resp = self.provider.fetch_data(req)

        self.assertTrue(resp.is_success)
        self.assertEqual(len(calls), 1)
        p_start, p_end = calls[0]
        self.assertEqual(p_start.tzinfo, tz_east)
        self.assertEqual(p_end.tzinfo, tz_east)

    def test_regression_iso_string_datetime_input(self) -> None:
        """Verify ISO datetime strings (naive and aware) are parsed correctly and UTC-normalized if naive."""
        from datetime import timezone
        start_str = "2026-01-01T10:00:00"
        end_str = "2026-01-01T15:00:00+04:00"

        calls = []
        def inspect_copy_rates_range(symbol, tf, date_from, date_to):
            calls.append((date_from, date_to))
            return mock_copy_rates_range(symbol, tf, date_from, date_to)
        mock_mt5.copy_rates_range.side_effect = inspect_copy_rates_range

        req = ExternalDataRequest("XAUUSD", "H1", start_str, end_str)
        resp = self.provider.fetch_data(req)

        self.assertTrue(resp.is_success)
        self.assertEqual(len(calls), 1)
        p_start, p_end = calls[0]
        self.assertEqual(p_start.tzinfo, timezone.utc)
        self.assertEqual(p_end.tzinfo, datetime.fromisoformat(end_str).tzinfo)

    def test_regression_invalid_reversed_date_range(self) -> None:
        """Verify invalid reversed date ranges are rejected early without calling MT5."""
        start_dt = datetime(2026, 1, 1, 12, 0, 0)
        end_dt = datetime(2026, 1, 1, 10, 0, 0) # end before start

        called = False
        def inspect_copy_rates_range(symbol, tf, date_from, date_to):
            nonlocal called
            called = True
            return []
        mock_mt5.copy_rates_range.side_effect = inspect_copy_rates_range

        req = ExternalDataRequest("XAUUSD", "H1", start_dt, end_dt)
        resp = self.provider.fetch_data(req)

        self.assertFalse(resp.is_success)
        self.assertFalse(called)
        self.assertIn("Invalid date range", resp.error_message)

    def test_regression_successful_copy_rates_range_retrieval_path(self) -> None:
        """Verify successful retrieval path executes cleanly and maps correctly."""
        start_dt = datetime(2026, 1, 1, 10, 0, 0)
        end_dt = datetime(2026, 1, 1, 12, 0, 0)

        req = MarketDataRequest(
            instrument=MarketInstrument("XAUUSD", "Metals"),
            timeframe="H1",
            start_time=start_dt,
            end_time=end_dt
        )
        resp = self.provider.fetch_market_data(req)
        self.assertTrue(resp.is_success)
        self.assertGreater(len(resp.candles), 0)
        self.assertEqual(resp.candles[0].open, 1800.0)

    def test_regression_future_range_rejection(self) -> None:
        """Verify ranges stretching into the future are rejected before calling MT5."""
        from datetime import timezone
        start_dt = datetime.now(timezone.utc) + timedelta(hours=5)
        end_dt = datetime.now(timezone.utc) + timedelta(hours=6)

        called = False
        def inspect_copy_rates_range(symbol, tf, date_from, date_to):
            nonlocal called
            called = True
            return []
        mock_mt5.copy_rates_range.side_effect = inspect_copy_rates_range

        req = ExternalDataRequest("XAUUSD", "H1", start_dt, end_dt)
        resp = self.provider.fetch_data(req)

        self.assertFalse(resp.is_success)
        self.assertFalse(called)
        self.assertIn("Rejected future date range", resp.error_message)

    def test_regression_copy_rates_from_pos_fallback(self) -> None:
        """Verify fallback to copy_rates_from_pos when copy_rates_range fails."""
        start_dt = datetime(2026, 1, 1, 10, 0, 0)
        end_dt = datetime(2026, 1, 1, 12, 0, 0)

        # Simulate copy_rates_range failure
        mock_mt5.copy_rates_range.side_effect = None
        mock_mt5.copy_rates_range.return_value = None
        mock_mt5.last_error.return_value = (-1, "Terminal call failed")

        called_fallback = False
        def inspect_copy_rates_from_pos(symbol, tf, start, count):
            nonlocal called_fallback
            called_fallback = True
            # Return a simple mock rates list directly to isolate the test cleanly
            return [{
                "time": 1600000000,
                "open": 1800.0,
                "high": 1810.0,
                "low": 1790.0,
                "close": 1805.0,
                "tick_volume": 100
            }]
        mock_mt5.copy_rates_from_pos.side_effect = inspect_copy_rates_from_pos

        req = ExternalDataRequest("XAUUSD", "H1", start_dt, end_dt)
        resp = self.provider.fetch_data(req)

        self.assertTrue(resp.is_success)
        self.assertTrue(called_fallback)
        self.assertGreater(len(resp.raw_data), 0)

    def test_regression_both_none_failure(self) -> None:
        """Verify failure returned when both range and pos return None."""
        start_dt = datetime(2026, 1, 1, 10, 0, 0)
        end_dt = datetime(2026, 1, 1, 12, 0, 0)

        mock_mt5.copy_rates_range.side_effect = None
        mock_mt5.copy_rates_range.return_value = None
        mock_mt5.copy_rates_from_pos.side_effect = None
        mock_mt5.copy_rates_from_pos.return_value = None
        mock_mt5.last_error.return_value = (-1, "Double failure")

        req = ExternalDataRequest("XAUUSD", "H1", start_dt, end_dt)
        resp = self.provider.fetch_data(req)

        self.assertFalse(resp.is_success)
        self.assertIn("MT5 copy_rates_range and copy_rates_from_pos both returned None", resp.error_message)
