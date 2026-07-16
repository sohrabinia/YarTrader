import unittest
from datetime import datetime, timedelta
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import MarketDataRequest
from src.Data.MarketData.Providers.mt5_provider import MetaTrader5MarketDataProvider
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Data.MarketData.Normalization.quality_checker import DataQualityChecker
from src.Research.MarketAnalysis.Repositories.repository import InMemoryResearchRepository


class TestResearchRuntimeSubsystems(unittest.TestCase):
    """
    Unit and integration tests for the Phase 40 Autonomous Market Research Runtime Foundation.
    Verifies MT5 provider initialization, rate conversion logic, empty response handling,
    data quality validation, and scheduler persistence.
    """

    def setUp(self) -> None:
        self.provider = MetaTrader5MarketDataProvider()
        self.provider.initialize()

    def tearDown(self) -> None:
        self.provider.shutdown()

    def test_provider_initialization_and_validation(self) -> None:
        """Verify that provider initializes and validates connection status correctly."""
        self.assertTrue(self.provider.connected)
        self.assertTrue(self.provider.validate_connection())

    def test_rate_conversion_and_symbol_handling(self) -> None:
        """Verify standard symbols (XAUUSD, EURUSD) and timeframe mappings return valid MarketDataPoint objects."""
        # 1. Gold asset check (XAUUSD)
        req = MarketDataRequest(
            Asset="XAUUSD",
            StartTime=datetime.now() - timedelta(hours=5),
            EndTime=datetime.now(),
            Timeframe="H1"
        )
        response = self.provider.retrieve_market_data(req)
        self.assertEqual(response.Request.Asset, "XAUUSD")
        self.assertGreater(len(response.DataPoints), 0)

        first_pt = response.DataPoints[0]
        self.assertEqual(first_pt.AssetId, "XAUUSD")
        self.assertGreater(first_pt.Open, 0.0)
        self.assertGreater(first_pt.High, 0.0)
        self.assertGreater(first_pt.Low, 0.0)
        self.assertGreater(first_pt.Close, 0.0)
        self.assertGreaterEqual(first_pt.Volume, 0.0)

    def test_timeframe_unsupported_exception(self) -> None:
        """Verify unsupported timeframes trigger ValidationException cleanly."""
        req = MarketDataRequest(
            Asset="XAUUSD",
            StartTime=datetime.now() - timedelta(hours=5),
            EndTime=datetime.now(),
            Timeframe="INVALID_TF"
        )
        with self.assertRaises(ValidationException) as context:
            self.provider.retrieve_market_data(req)
        self.assertIn("Unsupported timeframe", str(context.exception))

    def test_provider_retrieval_uninitialized_exception(self) -> None:
        """Verify retrieve_market_data raises ValidationException if provider is shutdown."""
        self.provider.shutdown()
        req = MarketDataRequest(
            Asset="XAUUSD",
            StartTime=datetime.now() - timedelta(hours=5),
            EndTime=datetime.now(),
            Timeframe="H1"
        )
        with self.assertRaises(ValidationException) as context:
            self.provider.retrieve_market_data(req)
        self.assertIn("Provider is not initialized", str(context.exception))

    def test_data_quality_and_validation_pipelines(self) -> None:
        """Verify structural validator and quality checkers correctly process retrieved rates."""
        req = MarketDataRequest(
            Asset="EURUSD",
            StartTime=datetime.now() - timedelta(hours=5),
            EndTime=datetime.now(),
            Timeframe="M30"
        )
        response = self.provider.retrieve_market_data(req)
        points = response.DataPoints

        # Validator checks
        validator = MarketDataValidator()
        self.assertTrue(validator.validate_market_data(points))

        # Quality Checker checks
        quality_checker = DataQualityChecker()
        report = quality_checker.check_quality(points)
        self.assertEqual(report.TotalRecords, len(points))
        self.assertEqual(report.ValidRecords, len(points))
        self.assertEqual(report.InvalidRecords, 0)
        self.assertEqual(len(report.Warnings), 0)

    def test_research_repository_persistence(self) -> None:
        """Verify InMemoryResearchRepository successfully stores and retrieves ResearchResult objects."""
        repo = InMemoryResearchRepository()
        self.assertEqual(len(repo.get_research_results("XAUUSD")), 0)

        # Create dummy result
        from src.Research.MarketAnalysis.Models.models import ResearchResult, ResearchRequest
        req = ResearchRequest("XAUUSD", datetime.now(), datetime.now(), {})
        dummy_res = ResearchResult(req, {"status": "completed"}, 0.85, datetime.now())

        repo.store_research_result(dummy_res)
        results = repo.get_research_results("XAUUSD")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ConfidenceScore, 0.85)
        self.assertEqual(results[0].Findings["status"], "completed")
