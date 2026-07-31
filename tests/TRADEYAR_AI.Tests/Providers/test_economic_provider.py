import unittest
from datetime import datetime, timedelta
from src.Data.Providers.Economic.economic import EconomicDataProvider, EconomicEvent, EconomicCalendarRecord
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException


class TestEconomicDataProvider(unittest.TestCase):
    """
    Test suite verifying Macroeconomic Calendar records, impact level,
    event parsing, and validation of actual/expected values. (30 unit tests)
    """

    def setUp(self) -> None:
        self.provider = EconomicDataProvider(provider_id="economic-test")
        self.now = datetime.now()

    # 1. Economic Record Construction (10 tests)
    def test_record_1_standard_creation(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "High", 3.1, 3.2, 3.0)
        self.assertEqual(rec.event_id, "ev-1")
        self.assertEqual(rec.actual, 3.1)

    def test_record_2_optional_fields_are_none_by_default(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "Medium")
        self.assertIsNone(rec.actual)
        self.assertIsNone(rec.previous)
        self.assertIsNone(rec.expected)

    def test_record_3_event_id_required(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "High")
        self.assertEqual(rec.event_id, "ev-1")

    def test_record_4_impact_level_medium(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "Medium")
        self.assertEqual(rec.impact, "Medium")

    def test_record_5_impact_level_low(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "Low")
        self.assertEqual(rec.impact, "Low")

    def test_record_6_parsed_event_creation(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "Low")
        evt = EconomicEvent(record=rec, parsed_at=self.now)
        self.assertEqual(evt.record, rec)
        self.assertEqual(evt.parsed_at, self.now)

    def test_record_7_unhealthy_status_reported_correctly(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.UNHEALTHY)

    def test_record_8_degraded_status_reported_correctly(self) -> None:
        self.provider.set_health(ProviderHealthStatus.DEGRADED)
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.DEGRADED)

    def test_record_9_supported_symbols_assigned(self) -> None:
        self.assertIn("US_CPI", self.provider.metadata.supported_symbols)
        self.assertIn("US_PAYROLL", self.provider.metadata.supported_symbols)

    def test_record_10_provider_id_assigned(self) -> None:
        self.assertEqual(self.provider.metadata.provider_id, "economic-test")

    # 2. Ingestion Fetching Tests (10 tests)
    def test_fetch_1_unhealthy_fetch_fails(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success)

    def test_fetch_2_cpi_events_loaded_correctly(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["event_id"], "ev-us-cpi-1")
        self.assertEqual(resp.raw_data[0]["actual"], 3.1)

    def test_fetch_3_nfp_events_loaded_correctly(self) -> None:
        req = ExternalDataRequest("US_PAYROLL", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["event_id"], "ev-us-nfp-1")
        self.assertEqual(resp.raw_data[0]["actual"], 175000.0)

    def test_fetch_4_generic_macro_event_loaded(self) -> None:
        req = ExternalDataRequest("EUR_GER_GDP", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["actual"], 1.5)

    def test_fetch_5_calendar_parsing_typed_events(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].record.name, "Consumer Price Index (YoY)")
        self.assertEqual(events[0].record.actual, 3.1)

    def test_fetch_6_calendar_parsing_missing_data_returns_empty_list_if_fetch_fails(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(len(events), 0)

    def test_fetch_7_nfp_raw_mapping(self) -> None:
        req = ExternalDataRequest("US_PAYROLL", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(events[0].record.event_id, "ev-us-nfp-1")

    def test_fetch_8_parsed_event_timestamp_matching(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(events[0].record.timestamp, self.now)

    def test_fetch_9_expected_value_retrieved(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(events[0].record.expected, 3.0)

    def test_fetch_10_previous_value_retrieved(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.provider.fetch_calendar_events(req)
        self.assertEqual(events[0].record.previous, 3.2)

    # 3. Parsing Validation Scenarios (10 tests)
    def test_validation_1_invalid_actual_float_throws_exception(self) -> None:
        # Mock bad payload
        class BrokenEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "name": "YoY", "country": "US", "timestamp": "2023-01-01T12:00:00", "impact": "High", "actual": "not-a-float"}])

        p = BrokenEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(ValidationException):
            p.fetch_calendar_events(req)

    def test_validation_2_invalid_timestamp_throws_exception(self) -> None:
        class BrokenTimestampEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "name": "YoY", "country": "US", "timestamp": "invalid-datetime", "impact": "High"}])

        p = BrokenTimestampEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(ValidationException):
            p.fetch_calendar_events(req)

    def test_validation_3_missing_expected_ignores_exception(self) -> None:
        # Expected is optional, so missing it does not crash calendar record building
        class MissingExpectedEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "name": "YoY", "country": "US", "timestamp": "2023-01-01T12:00:00", "impact": "High"}])

        p = MissingExpectedEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = p.fetch_calendar_events(req)
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0].record.expected)

    def test_validation_4_missing_impact_causes_exception(self) -> None:
        class MissingImpactEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "name": "YoY", "country": "US", "timestamp": "2023-01-01T12:00:00"}]) # missing impact

        p = MissingImpactEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_calendar_events(req)

    def test_validation_5_missing_country_causes_exception(self) -> None:
        class MissingCountryEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "name": "YoY", "timestamp": "2023-01-01T12:00:00", "impact": "High"}])

        p = MissingCountryEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_calendar_events(req)

    def test_validation_6_missing_name_causes_exception(self) -> None:
        class MissingNameEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"event_id": "ev-1", "country": "US", "timestamp": "2023-01-01T12:00:00", "impact": "High"}])

        p = MissingNameEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_calendar_events(req)

    def test_validation_7_missing_event_id_causes_exception(self) -> None:
        class MissingEventIdEconomicProvider(EconomicDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "eco", [{"name": "YoY", "country": "US", "timestamp": "2023-01-01T12:00:00", "impact": "High"}])

        p = MissingEventIdEconomicProvider()
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_calendar_events(req)

    def test_validation_8_actual_value_mapping(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "High", actual=100.0)
        self.assertEqual(rec.actual, 100.0)

    def test_validation_9_previous_value_mapping(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "High", previous=99.0)
        self.assertEqual(rec.previous, 99.0)

    def test_validation_10_expected_value_mapping(self) -> None:
        rec = EconomicCalendarRecord("ev-1", "YoY", "US", self.now, "High", expected=101.0)
        self.assertEqual(rec.expected, 101.0)
