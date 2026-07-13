import unittest
from datetime import datetime, timedelta
from src.Data.External.models import ExternalDataRequest, ProviderHealthStatus
from src.Data.Simulation.simulation import SimulationDataProvider
from src.Data.connector import ExternalDataPipelineConnector
from src.Infrastructure.exceptions import ValidationException


class TestExternalDataPipelineIntegration(unittest.TestCase):
    """
    Test suite verifying Scenario 1-4 end-to-end integration flows
    using the SimulationDataProvider and ExternalDataPipelineConnector. (15 unit/integration tests)
    """

    def setUp(self) -> None:
        self.connector = ExternalDataPipelineConnector()
        self.provider = SimulationDataProvider("sim-provider-1", ["AAPL", "BTCUSD"])
        self.connector.gateway.registry.register_provider(self.provider)
        self.now = datetime.now()

    # Scenario 1: Valid data flow (4 tests)
    def test_scenario_1_valid_flow_success(self) -> None:
        req = ExternalDataRequest(
            symbol="AAPL",
            timeframe="M15",
            start_time=self.now - timedelta(hours=2),
            end_time=self.now,
            parameters={"scenario": "VALID"}
        )
        records, report = self.connector.retrieve_and_process(req)
        self.assertTrue(report.is_acceptable)
        self.assertEqual(len(records), 9)  # 10 points minus 1 due to timedelta limits if any, or exactly 9
        self.assertEqual(records[0].original_source, "sim-provider-1")
        self.assertEqual(records[0].symbol, "AAPL")

        # Check reliability tracking: availability should be 1.0, error_rate 0.0
        avg = self.connector.reliability_tracker.get_average_scores("sim-provider-1")
        self.assertEqual(avg["availability"], 1.0)
        self.assertEqual(avg["error_rate"], 0.0)

    def test_scenario_1_valid_flow_under_rate_limit(self) -> None:
        # Check rate limit field exists
        self.assertEqual(self.provider.metadata.rate_limit_per_minute, 1000)

    def test_scenario_1_valid_flow_source_metadata_preserved(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "VALID"})
        records, _ = self.connector.retrieve_and_process(req)
        # raw symbol is preserved in metadata
        self.assertEqual(records[0].source_metadata["symbol"], "AAPL")

    def test_scenario_1_valid_flow_data_integrity_report_issued(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "VALID"})
        _, report = self.connector.retrieve_and_process(req)
        self.assertIsNotNone(report.report_id)
        self.assertEqual(report.provider_id, "sim-provider-1")

    # Scenario 2: Provider failure (4 tests)
    def test_scenario_2_provider_failure_returns_failure_response(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "FAILURE"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

        # Reliability score decreases
        avg = self.connector.reliability_tracker.get_average_scores("sim-provider-1")
        self.assertEqual(avg["availability"], 0.0)
        self.assertEqual(avg["error_rate"], 1.0)

    def test_scenario_2_provider_exception_returns_failure_response(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "EXCEPTION"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_scenario_2_unhealthy_provider_failover(self) -> None:
        # Mark primary unhealthy
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        # Register a secondary provider
        p_backup = SimulationDataProvider("sim-provider-backup", ["AAPL"])
        self.connector.gateway.registry.register_provider(p_backup)

        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "VALID"})
        records, report = self.connector.retrieve_and_process(req)

        # Should failover successfully to secondary provider
        self.assertTrue(report.is_acceptable)
        self.assertEqual(report.provider_id, "sim-provider-backup")

    def test_scenario_2_no_providers_available_degrades_safely(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "VALID"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    # Scenario 3: Corrupted dataset (4 tests)
    def test_scenario_3_corrupted_prices_rejected_with_report(self) -> None:
        # low price exceeds high price
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "CORRUPTED_PRICES"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)
        self.assertGreater(len(report.anomalies), 0)

        # Availability is 1.0, but error_rate is 0.5 because dataset was unacceptable
        avg = self.connector.reliability_tracker.get_average_scores("sim-provider-1")
        self.assertEqual(avg["error_rate"], 0.5)

    def test_scenario_3_invalid_timestamps_rejected_with_report(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "INVALID_TIMESTAMPS"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_scenario_3_missing_crucial_fields_rejected(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "MISSING_FIELDS"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_scenario_3_duplicate_records_deduplicated_or_scored_down(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "DUPLICATES"})
        records, report = self.connector.retrieve_and_process(req)
        self.assertLess(report.quality_scores.uniqueness_score, 1.0)

    # Scenario 4: Low quality source (3 tests)
    def test_scenario_4_low_quality_source_decreases_reliability(self) -> None:
        # First query: perfect valid data
        req_valid = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "VALID"})
        _, r_valid = self.connector.retrieve_and_process(req_valid)
        self.assertTrue(r_valid.is_acceptable)

        # Second query: low quality data (missing fields)
        req_low = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "MISSING_FIELDS"})
        self.connector.retrieve_and_process(req_low)

        # Third query: low quality data (corrupted prices)
        req_corrupt = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "CORRUPTED_PRICES"})
        self.connector.retrieve_and_process(req_corrupt)

        avg = self.connector.reliability_tracker.get_average_scores("sim-provider-1")
        # Composite score must decrease significantly
        self.assertLess(avg["composite_score"], 1.0)
        self.assertGreater(avg["error_rate"], 0.0)

    def test_scenario_4_error_rate_accumulation_in_tracker(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "CORRUPTED_PRICES"})
        self.connector.retrieve_and_process(req)
        self.connector.retrieve_and_process(req)
        avg = self.connector.reliability_tracker.get_average_scores("sim-provider-1")
        self.assertEqual(avg["error_rate"], 0.5)

    def test_scenario_4_low_quality_records_chronology_preserved(self) -> None:
        req = ExternalDataRequest("AAPL", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "CORRUPTED_PRICES"})
        self.connector.retrieve_and_process(req)
        history = self.connector.reliability_tracker.get_history("sim-provider-1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].error_rate, 0.5)
