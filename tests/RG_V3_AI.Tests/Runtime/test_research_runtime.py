import os
import unittest
from datetime import datetime, timedelta
from typing import Optional, List
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import (
    MarketDataRequest as TargetMarketDataRequest,
    MarketDataResponse as TargetMarketDataResponse,
    MarketDataPoint as TargetMarketDataPoint
)
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine

class TestResearchRuntimeAndAdapter(unittest.TestCase):
    """
    Unit and integration tests for the Phase 21 Live Research Runtime & MT5 Adapter.
    Validates correct data translation, runtime polling execution, and evidence compilation.
    """

    def setUp(self) -> None:
        self.evidence_dir = "test_runtime_logs"
        # Reset logging target directory
        if os.path.exists(self.evidence_dir):
            for file in os.listdir(self.evidence_dir):
                try:
                    os.remove(os.path.join(self.evidence_dir, file))
                except OSError:
                    pass
            try:
                os.rmdir(self.evidence_dir)
            except OSError:
                pass

        # Build mock-ready delegate
        self.delegate = MT5DataProvider(provider_id="test-mt5-del", server="Demo-Server")
        self.adapter = MetaTrader5Provider(delegate=self.delegate)
        self.now = datetime.now()

    def tearDown(self) -> None:
        # Clean up test directories
        if os.path.exists(self.evidence_dir):
            for file in os.listdir(self.evidence_dir):
                try:
                    os.remove(os.path.join(self.evidence_dir, file))
                except OSError:
                    pass
            try:
                os.rmdir(self.evidence_dir)
            except OSError:
                pass

    # 1. MetaTrader5Provider Adapter Tests
    def test_adapter_initialization_defaults(self) -> None:
        """Verify the adapter instantiates correctly with delegate properties."""
        p = MetaTrader5Provider()
        self.assertIsNotNone(p.delegate)
        self.assertEqual(p.delegate.metadata.provider_id, "mt5-marketdata-provider")

    def test_adapter_successful_mapping_and_retrieval(self) -> None:
        """Verify standard TargetMarketDataRequest is translated, fetched from MT5, and returned as MarketDataPoints."""
        req = TargetMarketDataRequest(
            Asset="EURUSD",
            StartTime=self.now - timedelta(hours=1),
            EndTime=self.now,
            Timeframe="M15"
        )
        resp = self.adapter.retrieve_market_data(req)
        self.assertEqual(resp.Request, req)
        self.assertGreater(len(resp.DataPoints), 0)

        # Verify first point properties
        first_point = resp.DataPoints[0]
        self.assertEqual(first_point.AssetId, "EURUSD")
        self.assertEqual(first_point.Open, 1.1000)
        self.assertGreater(first_point.Volume, 0.0)

    def test_adapter_unsuccessful_delegate_rejection(self) -> None:
        """Verify that adapter raises ValidationException when the delegate fails."""
        # Set delegate to offline
        self.delegate.set_connected(False)
        req = TargetMarketDataRequest(
            Asset="EURUSD",
            StartTime=self.now - timedelta(hours=1),
            EndTime=self.now,
            Timeframe="M15"
        )
        with self.assertRaises(ValidationException):
            self.adapter.retrieve_market_data(req)

    # 2. ResearchRuntime Engine Integration Tests
    def test_runtime_initialization(self) -> None:
        """Verify that ResearchRuntime initializes with appropriate parameter configs."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )
        self.assertEqual(runtime.symbol, "XAUUSD")
        self.assertEqual(runtime.timeframe, "H1")
        self.assertIs(runtime.provider, self.adapter)

    def test_runtime_single_cycle_run_once(self) -> None:
        """Verify that a single research execution loop completes successfully and generates correct findings and files."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )

        result = runtime.run_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.Request.Asset, "XAUUSD")
        self.assertIn("feature_set", result.Findings)
        self.assertIn("observation_summary", result.Findings)
        self.assertEqual(len(runtime.history), 1)

        # Confirm evidence file creation
        evidence_file = os.path.join(self.evidence_dir, "research_runtime_evidence.log")
        self.assertTrue(os.path.exists(evidence_file))

        # Verify contents of evidence logs matches the requested evidence pattern
        with open(evidence_file, "r") as f:
            content = f.read()
        self.assertIn("MT5 Connected", content)
        self.assertIn("Symbol: XAUUSD", content)
        self.assertIn("Timeframe: H1", content)
        self.assertIn("Candles Received:", content)
        self.assertIn("Features Generated: true", content)
        self.assertIn("Research Completed: true", content)

    def test_runtime_polling_loop_lifecycle(self) -> None:
        """Verify that start_polling_loop executes requested cycle limits and terminates gracefully."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )

        # Run 2 cycles with short interval
        runtime.start_polling_loop(interval_seconds=0.01, limit_cycles=2)
        self.assertEqual(len(runtime.history), 2)

        # Stop check
        runtime.stop()
        self.assertFalse(runtime._is_running)
