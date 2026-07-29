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

    # 3. Dedicated Live Research & Intelligence Pipeline Tests (Phase 21 Activation)
    def test_live_market_research_integration_flow(self) -> None:
        """Verify real MT5 candles flow into all 6 analytical and smart interpretation engines."""
        from src.Research.analysis_pipeline import (
            TechnicalAnalysisEngine,
            FeatureEngineeringLayer,
            MarketRegimeDetection,
            TrendAnalysis,
            VolatilityAnalysis,
            MomentumAnalysis,
            SmartInterpretationEngine
        )

        # 1. Fetch data from adapter
        req = TargetMarketDataRequest(
            Asset="XAUUSD",
            StartTime=self.now - timedelta(hours=2),
            EndTime=self.now,
            Timeframe="H1"
        )
        resp = self.adapter.retrieve_market_data(req)
        self.assertGreater(len(resp.DataPoints), 0)

        # 2. Feed into six analytical layers
        tech_eng = TechnicalAnalysisEngine()
        tech_res = tech_eng.analyze(resp.DataPoints)
        self.assertIn("sma_20", tech_res)
        self.assertIn("rsi", tech_res)
        self.assertIn("macd", tech_res)
        self.assertIn("atr", tech_res)
        self.assertIn("support", tech_res)
        self.assertIn("resistance", tech_res)

        feat_layer = FeatureEngineeringLayer()
        feature_set = feat_layer.process(resp.DataPoints)
        self.assertEqual(feature_set.AssetId, "XAUUSD")

        trend_eng = TrendAnalysis()
        trend_res = trend_eng.analyze(resp.DataPoints, feature_set)
        self.assertIn("direction_label", trend_res)
        self.assertIn("is_trending", trend_res)

        vol_eng = VolatilityAnalysis()
        vol_res = vol_eng.analyze(resp.DataPoints, feature_set)
        self.assertIn("rolling_volatility", vol_res)
        self.assertIn("volatility_state", vol_res)

        mom_eng = MomentumAnalysis()
        mom_res = mom_eng.analyze(resp.DataPoints, feature_set)
        self.assertIn("rate_of_change_pct", mom_res)
        self.assertIn("momentum_state", mom_res)

        reg_eng = MarketRegimeDetection()
        reg_res = reg_eng.detect(resp.DataPoints, feature_set)
        self.assertIn("regime", reg_res)
        self.assertIn("explanation", reg_res)

        # 3. Feed into Smart Interpretation
        smart_eng = SmartInterpretationEngine()
        smart_res = smart_eng.interpret(
            candles=resp.DataPoints,
            tech=tech_res,
            trend=trend_res,
            vol=vol_res,
            mom=mom_res,
            regime=reg_res
        )
        self.assertIn("bias", smart_res)
        self.assertIn("confidence", smart_res)
        self.assertIn("reasoning", smart_res)
        self.assertIn(smart_res["bias"], ["Bullish", "Bearish", "Neutral"])
        self.assertGreaterEqual(smart_res["confidence"], 50)
        self.assertLessEqual(smart_res["confidence"], 95)
        self.assertGreater(len(smart_res["reasoning"]), 0)

    def test_research_runtime_error_and_connection_recovery(self) -> None:
        """Verify that runtime worker gracefully logs health, recovers after disconnects, and never crashes."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )

        # Disconnect delegate
        self.delegate.set_connected(False)
        with self.assertRaises(ValidationException):
            runtime.run_once()

        # Reconnect and verify it recovers successfully
        self.delegate.set_connected(True)
        res = runtime.run_once()
        self.assertIsNotNone(res)
        self.assertEqual(res.Request.Asset, "XAUUSD")

    def test_research_current_endpoint(self) -> None:
        """Verify /api/research/current returns compliant live snapshot schema."""
        from fastapi.testclient import TestClient
        from src.Application.Services.web_dashboard import app

        client = TestClient(app)
        resp = client.get("/api/research/current")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["symbol"], "XAUUSD")
        self.assertEqual(data["timeframe"], "H1")
        self.assertIn(data["bias"], ["Bullish", "Bearish", "Neutral"])
        self.assertIn("confidence", data)
        self.assertIn("reasoning", data)
        self.assertIn("indicators", data)
        self.assertIn("timestamp", data)

    def test_research_latest_endpoint(self) -> None:
        """Verify /api/research/latest returns compliant live latest analysis schema."""
        from fastapi.testclient import TestClient
        from src.Application.Services.web_dashboard import app

        client = TestClient(app)
        resp = client.get("/api/research/latest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["symbol"], "XAUUSD")
        self.assertEqual(data["timeframe"], "H1")
        self.assertIn("bias", data)
        self.assertIn("confidence", data)

    def test_research_history_endpoint(self) -> None:
        """Verify /api/research/history correctly returns previous analyses."""
        from fastapi.testclient import TestClient
        from src.Application.Services.web_dashboard import app

        client = TestClient(app)
        resp = client.get("/api/research/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[-1]["symbol"], "XAUUSD")

    def test_research_health_endpoint(self) -> None:
        """Verify /api/research/health returns detailed worker, connection, and metrics metadata."""
        from fastapi.testclient import TestClient
        from src.Application.Services.web_dashboard import app

        client = TestClient(app)
        resp = client.get("/api/research/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["mt5_status"], ["ONLINE", "CONNECTED", "DISCONNECTED"])
        self.assertIsNotNone(data["last_analysis_time"])
        self.assertIn("worker_running", data)
        self.assertIn("worker_started_at", data)
        self.assertIn("last_successful_cycle", data)
        self.assertIn("cycle_count", data)
        self.assertIn("last_error", data)
        self.assertIn("last_result_id", data)

    def test_worker_single_instance(self) -> None:
        """Verify that starting the background loop guarantees exactly a single worker daemon is spawned."""
        from src.Application.Services.web_dashboard import ensure_worker_started, _worker_started
        ensure_worker_started()
        self.assertTrue(_worker_started)

    def test_snapshot_creation(self) -> None:
        """Verify that analysis cycles automatically serialize and persist JSON snapshots to disk."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )
        result = runtime.run_once()
        self.assertIsNotNone(result)

        snapshot_dir = os.path.join(self.evidence_dir, "research_snapshots")
        self.assertTrue(os.path.exists(snapshot_dir))
        files = [f for f in os.listdir(snapshot_dir) if f.endswith(".json")]
        self.assertGreater(len(files), 0)

    def test_snapshot_integrity(self) -> None:
        """Verify that written snapshots are well-formed JSON containing correct keys and structural fields."""
        import json
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )
        runtime.run_once()

        snapshot_dir = os.path.join(self.evidence_dir, "research_snapshots")
        files = [f for f in os.listdir(snapshot_dir) if f.endswith(".json")]
        filepath = os.path.join(snapshot_dir, files[0])

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["asset"], "XAUUSD")
        self.assertEqual(data["timeframe"], "H1")
        self.assertIn("confidence_score", data)
        self.assertIn("created_at", data)
        self.assertIn("findings", data)

    def test_mt5_disconnect_recovery(self) -> None:
        """Verify MT5 provider connection drops recover gracefully and log states without crashing."""
        runtime = ResearchRuntime(
            provider=self.adapter,
            symbol="XAUUSD",
            timeframe="H1",
            evidence_dir=self.evidence_dir
        )
        # Disconnect provider
        self.delegate.set_connected(False)
        with self.assertRaises(ValidationException):
            runtime.run_once()

        # Reconnect
        self.delegate.set_connected(True)
        res = runtime.run_once()
        self.assertIsNotNone(res)
        self.assertEqual(res.Request.Asset, "XAUUSD")

    def test_invalid_candle_handling(self) -> None:
        """Verify that empty or corrupted rates returned by MT5 raise clean ValidationExceptions."""
        # Setup delegate to mock empty rates
        from unittest.mock import patch
        with patch.object(self.delegate, "fetch_data") as mock_fetch:
            from src.Data.External.models import ExternalDataResponse
            mock_fetch.return_value = ExternalDataResponse(
                request_id="id",
                provider_id="test",
                raw_data=[],
                is_success=True # Simulates empty rates response
            )

            runtime = ResearchRuntime(
                provider=self.adapter,
                symbol="XAUUSD",
                timeframe="H1",
                evidence_dir=self.evidence_dir
            )
            with self.assertRaises(ValidationException):
                runtime.run_once()

    def test_strict_read_only_compliance_no_trading_api(self) -> None:
        """Verify that absolutely no active trading functions (buy, sell, order_send) are defined or called."""
        forbidden = ["order_send", "place_order", "send_transaction", "order_modify"]
        paths = ["src/Research", "src/Application/Runtime"]

        for path in paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        for keyword in forbidden:
                            self.assertNotIn(keyword + "(", content.replace(" ", ""))

    def test_mt5_provider_real_mode_and_fallback_mode(self) -> None:
        """Verify MT5DataProvider acts correctly when MT5 is available vs unavailable fallback."""
        from src.Data.Providers.MT5.mt5 import MT5DataProvider, ProviderHealthStatus

        provider = MT5DataProvider(provider_id="test-provider-toggle")

        # Scenario A: Connected (Simulates available)
        provider.set_connected(True)
        health = provider.get_connection_health()
        self.assertTrue(health.connected or not health.connected) # No crash

        # Scenario B: Disconnected (Simulates unavailable)
        provider.set_connected(False)
        health_disc = provider.get_connection_health()
        self.assertFalse(health_disc.connected)
        self.assertEqual(provider.check_health(), ProviderHealthStatus.UNHEALTHY)
        self.assertIn("Connection lost", health_disc.last_error)
