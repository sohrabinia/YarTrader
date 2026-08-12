import unittest
from datetime import datetime, timedelta
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.Market.models import MarketInstrument, MarketDataRequest
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.Providers.Economic.economic import EconomicDataProvider
from src.Data.Providers.News.news import NewsDataProvider
from src.Data.Simulation.simulation import SimulationDataProvider
from src.Data.connector import ExternalDataPipelineConnector
from src.Infrastructure.exceptions import ValidationException


class TestDataFlowAndGatewayIntegration(unittest.TestCase):
    """
    Test suite verifying dynamic gateway routing, latency checks,
    simulation scenario variations, and End-to-End integration layers. (25 unit/integration tests)
    """

    def setUp(self) -> None:
        self.connector = ExternalDataPipelineConnector()
        self.now = datetime.now()
        self.instrument = MarketInstrument("EURUSD", "FX")

    # 1. Pipeline Connectivity Tests (8 tests)
    def test_pipeline_1_fetch_mt5_valid_market_data(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now - timedelta(hours=2), self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(len(resp.candles), 9)

        # Confirm reliability metrics recorded: latency and availability scored
        report = self.connector.reliability_tracker.generate_health_report("mt5-provider")
        self.assertTrue(report["is_connected"])
        self.assertEqual(report["provider_availability_score"], 1.0)
        self.assertGreaterEqual(report["average_latency_ms"], 0.0)

    def test_pipeline_2_fetch_economic_events(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.connector.retrieve_economic_events(req)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].record.event_id, "ev-us-cpi-1")

        report = self.connector.reliability_tracker.generate_health_report("economic-provider")
        self.assertTrue(report["is_connected"])

    def test_pipeline_3_fetch_news_records(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.connector.retrieve_news_records(req)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].article_id, "news-fomc-1")

        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertTrue(report["is_connected"])

    def test_pipeline_4_mt5_offline_reports_connection_unhealthy_and_fails(self) -> None:
        self.connector.mt5_provider.set_connected(False)
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertFalse(resp.is_success)

        report = self.connector.reliability_tracker.generate_health_report("mt5-provider")
        self.assertFalse(report["is_connected"])
        self.assertEqual(report["provider_availability_score"], 0.0)
        self.assertEqual(report["error_rate"], 1.0)

    def test_pipeline_5_economic_offline_scores_down_reliability(self) -> None:
        self.connector.economic_provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.connector.retrieve_economic_events(req)
        self.assertEqual(len(events), 0)

        report = self.connector.reliability_tracker.generate_health_report("economic-provider")
        self.assertEqual(report["provider_availability_score"], 0.0)

    def test_pipeline_6_news_offline_scores_down_reliability(self) -> None:
        self.connector.news_provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.connector.retrieve_news_records(req)
        self.assertEqual(len(records), 0)

        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertEqual(report["provider_availability_score"], 0.0)

    def test_pipeline_7_latency_recorded_for_economic_provider(self) -> None:
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        self.connector.retrieve_economic_events(req)
        report = self.connector.reliability_tracker.generate_health_report("economic-provider")
        self.assertGreaterEqual(report["average_latency_ms"], 0.0)

    def test_pipeline_8_latency_recorded_for_news_provider(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        self.connector.retrieve_news_records(req)
        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertGreaterEqual(report["average_latency_ms"], 0.0)

    # 2. Simulation Scenario Compatibility (10 tests)
    def test_simulation_1_mt5_unavailable_safe_degradation(self) -> None:
        sim_p = SimulationDataProvider()
        # Register simulation provider instead
        connector = ExternalDataPipelineConnector()
        connector.gateway.registry.register_provider(sim_p)

        req = ExternalDataRequest("EURUSD", "M15", self.now, self.now, parameters={"scenario": "MT5_UNAVAILABLE"})
        records, report = connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_simulation_2_economic_api_failure_safe_degradation(self) -> None:
        sim_p = SimulationDataProvider()
        connector = ExternalDataPipelineConnector()
        connector.gateway.registry.register_provider(sim_p)

        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now, parameters={"scenario": "ECONOMIC_API_FAILURE"})
        records, report = connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_simulation_3_news_provider_timeout_fails_safely(self) -> None:
        sim_p = SimulationDataProvider()
        connector = ExternalDataPipelineConnector()
        connector.gateway.registry.register_provider(sim_p)

        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now, parameters={"scenario": "NEWS_PROVIDER_TIMEOUT"})
        records, report = connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_simulation_4_corrupted_market_data_rejected(self) -> None:
        sim_p = SimulationDataProvider()
        connector = ExternalDataPipelineConnector()
        connector.gateway.registry.unregister_provider("mt5-provider")
        connector.gateway.registry.register_provider(sim_p)

        req = ExternalDataRequest("EURUSD", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "CORRUPTED_MARKET_DATA"})
        records, report = connector.retrieve_and_process(req)
        self.assertEqual(len(records), 0)
        self.assertFalse(report.is_acceptable)

    def test_simulation_5_delayed_data_response_success_with_higher_latency(self) -> None:
        sim_p = SimulationDataProvider()
        connector = ExternalDataPipelineConnector()
        # Unregister existing to make sure sim_p is resolved
        connector.gateway.registry.unregister_provider("mt5-provider")
        connector.gateway.registry.register_provider(sim_p)

        req = ExternalDataRequest("EURUSD", "M15", self.now - timedelta(hours=2), self.now, parameters={"scenario": "DELAYED_DATA_RESPONSE"})
        records, report = connector.retrieve_and_process(req)
        self.assertTrue(report.is_acceptable)

        health_rep = connector.reliability_tracker.generate_health_report(sim_p.metadata.provider_id)
        # Latency should be recorded
        self.assertGreaterEqual(health_rep["average_latency_ms"], 10.0) # sleep 0.01 is ~10ms

    def test_simulation_6_health_report_includes_failure_logs_count(self) -> None:
        # Generate 2 failures
        self.connector.reliability_tracker.record_metrics("news-provider", 0.0, 1.0, 0.0, 0.0, error_msg="Timeout happened.")
        self.connector.reliability_tracker.record_metrics("news-provider", 0.0, 1.0, 0.0, 0.0, error_msg="Second crash.")
        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertEqual(report["failure_history_count"], 2)
        self.assertEqual(len(report["failure_logs"]), 2)

    def test_simulation_7_health_report_unregistered_defaults(self) -> None:
        report = self.connector.reliability_tracker.generate_health_report("unknown")
        self.assertEqual(report["provider_availability_score"], 1.0)
        self.assertEqual(report["average_latency_ms"], 0.0)

    def test_simulation_8_availability_score_is_correct(self) -> None:
        # 1 success, 1 fail
        self.connector.reliability_tracker.record_metrics("news-provider", 1.0, 0.0, 1.0, 1.0)
        self.connector.reliability_tracker.record_metrics("news-provider", 0.0, 1.0, 0.0, 0.0)
        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertEqual(report["provider_availability_score"], 0.5)

    def test_simulation_9_failure_history_capped_in_report(self) -> None:
        # record 15 errors
        for i in range(15):
            self.connector.reliability_tracker.record_metrics("news-provider", 0.0, 1.0, 0.0, 0.0, error_msg=f"Error {i}")
        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertEqual(len(report["failure_logs"]), 10) # last 10 logs

    def test_simulation_10_clear_resets_health_metrics(self) -> None:
        self.connector.reliability_tracker.record_metrics("news-provider", 1.0, 0.0, 1.0, 1.0, latency_ms=10.0, error_msg="Error")
        self.connector.reliability_tracker.clear()
        report = self.connector.reliability_tracker.generate_health_report("news-provider")
        self.assertEqual(report["failure_history_count"], 0)
        self.assertEqual(report["average_latency_ms"], 0.0)

    # 3. End-to-End Scenarios (7 tests)
    def test_e2e_1_normal_market_success(self) -> None:
        req = MarketDataRequest(self.instrument, "M15", self.now - timedelta(hours=2), self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(len(resp.candles), 9)

    def test_e2e_2_volatile_market_scrutiny(self) -> None:
        # In highly volatile markets, prices could wider but should still pass low <= high limits
        req = MarketDataRequest(self.instrument, "M15", self.now - timedelta(hours=2), self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertTrue(resp.is_success)

    def test_e2e_3_provider_failure_degrades_safely(self) -> None:
        self.connector.mt5_provider.set_connected(False)
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertFalse(resp.is_success)

    def test_e2e_4_corrupted_dataset_rejected(self) -> None:
        class CorruptedMT5Provider(MT5DataProvider):
            def fetch_data(self, r):
                # Low price 10.0 > High price 5.0 -> Corrupted!
                return ExternalDataResponse("id", "mt5", [{"time": 1600000000, "open": 5.0, "high": 5.0, "low": 10.0, "close": 5.0}])

        self.connector.mt5_provider = CorruptedMT5Provider()
        req = MarketDataRequest(self.instrument, "M15", self.now, self.now)
        resp = self.connector.retrieve_market_data(req)
        self.assertFalse(resp.is_success)
        self.assertIn("Validation of received candles failed", resp.error_message)

    def test_e2e_5_news_timeout_handled_safely(self) -> None:
        self.connector.news_provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.connector.retrieve_news_records(req)
        self.assertEqual(len(records), 0)

    def test_e2e_6_economic_api_failure_handled_safely(self) -> None:
        self.connector.economic_provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        events = self.connector.retrieve_economic_events(req)
        self.assertEqual(len(events), 0)

    def test_e2e_7_multiple_scenarios_accumulation(self) -> None:
        # Accumulate metrics
        req = ExternalDataRequest("US_CPI", "M15", self.now, self.now)
        self.connector.retrieve_economic_events(req)
        self.connector.economic_provider.set_health(ProviderHealthStatus.UNHEALTHY)
        self.connector.retrieve_economic_events(req)
        avg = self.connector.reliability_tracker.get_average_scores("economic-provider")
        self.assertEqual(avg["availability"], 0.5)
