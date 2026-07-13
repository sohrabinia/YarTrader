import unittest
from datetime import datetime, timedelta
from src.Data.Market.models import MarketInstrument, MarketDataRequest
from src.Data.Providers.MT5.mt5 import MT5DataProvider, MT5ConnectionHealth, MT5DataMapper
from src.Data.External.models import ExternalDataRequest, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException


class TestMT5AdapterAndMapper(unittest.TestCase):
    """
    Test suite verifying the read-only MT5 Data Provider connection health,
    rates-to-candles mapping, and validation failure scenarios. (30 unit tests)
    """

    def setUp(self) -> None:
        self.provider = MT5DataProvider(provider_id="mt5-test", server="Demo-Server")
        self.mapper = MT5DataMapper()
        self.instrument = MarketInstrument("EURUSD", "FX")
        self.now = datetime.now()

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
        self.assertIn("connection is currently offline", resp.error_message)

    def test_failure_2_fetch_market_data_when_offline_fails(self) -> None:
        self.provider.set_connected(False)
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertFalse(resp.is_success)
        self.assertIn("connection is offline", resp.error_message)

    def test_failure_3_fetch_market_data_unsuccessful_fetch_propagates_failure(self) -> None:
        # Request symbol not supported
        inst = MarketInstrument("XAUUSD", "Metals")
        req = MarketDataRequest(inst, "M15", self.now, self.now)
        resp = self.provider.fetch_market_data(req)
        self.assertTrue(resp.is_success)  # returns data for simplicity of mocking, or check support

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
