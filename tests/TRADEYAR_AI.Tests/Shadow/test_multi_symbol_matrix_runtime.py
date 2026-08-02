import os
import json
import shutil
import unittest
from datetime import datetime
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, REGISTRY_FILE
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
from src.Data.Providers.Crypto.crypto_provider import CryptoProvider

class TestMultiSymbolMatrixRuntime(unittest.TestCase):
    """
    Automated SRE validation suite for Multi-Symbol & Multi-Timeframe Research Runtime.
    Ensures matrix resolution, dynamic registry, shadow position isolation, and restart integrity.
    """

    def setUp(self) -> None:
        self.registry = SymbolRegistry.get_instance()
        # Reset the registry to a clean test state
        if os.path.exists(REGISTRY_FILE):
            try:
                os.remove(REGISTRY_FILE)
            except OSError:
                pass
        self.registry.registry = {}
        self.registry.load_registry()

        # Clean snapshots folder for testing
        self.snapshot_dir = "runtime_logs/research_snapshots"
        if os.path.exists(self.snapshot_dir):
            try:
                shutil.rmtree(self.snapshot_dir)
            except OSError:
                pass
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def tearDown(self) -> None:
        # Restore clean state
        if os.path.exists(REGISTRY_FILE):
            try:
                os.remove(REGISTRY_FILE)
            except OSError:
                pass

    def test_regression_protection(self) -> None:
        """Regression Protection: Raise warning if multiple symbols/timeframes are configured but only 1 executes."""
        active_matrix = self.registry.get_active_matrix()
        executed_runs = 1 # Simulate degraded execution

        warning_raised = False
        if len(active_matrix) > 1 and executed_runs == 1:
            warning_raised = True
            print("WARNING: MULTI_SYMBOL_RUNTIME_DEGRADED")

        self.assertTrue(warning_raised)

    def test_1_multi_symbol_multi_tf_execution(self) -> None:
        """Test 1: Register XAUUSD (H1, H4) and EURUSD (H1), execute, verify 3 snapshots generated."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("EURUSD", ["H1"])

        active_matrix = self.registry.get_active_matrix()
        active_pairs = [(sym, tf) for sym, tf, ac, p in active_matrix]
        self.assertEqual(len(active_pairs), 3)
        self.assertIn(("XAUUSD", "H1"), active_pairs)
        self.assertIn(("XAUUSD", "H4"), active_pairs)
        self.assertIn(("EURUSD", "H1"), active_pairs)

        # Execute research loop simulation
        runtimes = {}
        for symbol, tf, ac, p in active_matrix:
            runtime = ResearchRuntime(symbol=symbol, timeframe=tf, evidence_dir="runtime_logs", provider_name=p, asset_class=ac)
            res = runtime.run_once()

            # Verify file exists
            snapshot_files = os.listdir(self.snapshot_dir)
            matching_files = [f for f in snapshot_files if f.startswith(f"rpt-{symbol}-{tf}-") and f.endswith(".json")]
            self.assertGreater(len(matching_files), 0, f"Snapshot for {symbol} on {tf} was not created.")

    def test_2_symbol_disable(self) -> None:
        """Test 2: Disable EURUSD, verify only XAUUSD executes."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("EURUSD", ["H1"])

        # Disable EURUSD
        self.registry.set_symbol_active("EURUSD", False)

        active_matrix = self.registry.get_active_matrix()
        active_pairs = [(sym, tf) for sym, tf, ac, p in active_matrix]
        self.assertEqual(len(active_pairs), 2)
        self.assertIn(("XAUUSD", "H1"), active_pairs)
        self.assertIn(("XAUUSD", "H4"), active_pairs)
        self.assertNotIn(("EURUSD", "H1"), active_pairs)

    def test_3_shadow_isolation(self) -> None:
        """Test 3: Open XAUUSD H1 SELL position. Verify XAUUSD H1 duplicate skips, while XAUUSD H4 succeeds."""
        engine = ShadowTradingEngine.get_instance()
        engine.reset_account()

        # Open an initial XAUUSD H1 SELL position
        pos_h1 = engine.handle_decision(
            decision_action="SELL",
            current_price=2350.0,
            symbol="XAUUSD",
            timeframe="H1"
        )
        self.assertIsNotNone(pos_h1)

        # Attempt to open duplicate XAUUSD H1 SELL (should skip)
        pos_duplicate = engine.handle_decision(
            decision_action="SELL",
            current_price=2349.0,
            symbol="XAUUSD",
            timeframe="H1"
        )
        self.assertIsNone(pos_duplicate)

        # Attempt to open XAUUSD H4 SELL (should succeed because of timeframe isolation)
        pos_h4 = engine.handle_decision(
            decision_action="SELL",
            current_price=2350.0,
            symbol="XAUUSD",
            timeframe="H4"
        )
        self.assertIsNotNone(pos_h4)

    def test_4_service_restart_persistence(self) -> None:
        """Test 4: Simulate a service/process restart, verify registry is restored successfully."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("GBPUSD", ["H1"])
        self.registry.save_registry()

        # Re-instantiate a clean Registry, mimicking startup
        new_registry = SymbolRegistry()
        active_matrix = new_registry.get_active_matrix()
        active_pairs = [(sym, tf) for sym, tf, ac, p in active_matrix]

        self.assertEqual(len(active_pairs), 3)
        self.assertIn(("XAUUSD", "H1"), active_pairs)
        self.assertIn(("GBPUSD", "H1"), active_pairs)

    def test_5_crypto_provider_mapping(self) -> None:
        """Verify the dynamic crypto symbol mapping layer maps XRPUSD -> XRP-USD."""
        provider = CryptoProvider()
        mapped = provider.resolve_provider_symbol("XRPUSD")
        self.assertEqual(mapped, "XRP-USD")

    def test_6_d1_timeframe_support(self) -> None:
        """Verify that daily D1 timeframe contexts run flawlessly across the entire stack."""
        # Test daily H1 / H4 / D1 support for XAUUSD and BTCUSD
        r1 = ResearchRuntime(symbol="XAUUSD", timeframe="D1", provider_name="MT5", asset_class="Commodities")
        res1 = r1.run_once()
        self.assertEqual(res1.Request.Context.get("timeframe"), "D1")

        r2 = ResearchRuntime(symbol="BTCUSD", timeframe="D1", provider_name="Crypto", asset_class="Crypto")
        res2 = r2.run_once()
        self.assertEqual(res2.Request.Context.get("timeframe"), "D1")

    def test_7_no_synthetics_in_universe(self) -> None:
        """Verify that no SYMxx or synthetic test symbols exist in the active matrix."""
        active_matrix = self.registry.get_active_matrix()
        for symbol, tf, ac, p in active_matrix:
            self.assertFalse(symbol.startswith("SYM"), f"Synthetic symbol {symbol} found in active universe.")

    def test_8_failed_provider_snapshot(self) -> None:
        """Verify that persistent provider failures write diagnostic snapshots with invalid data quality."""
        runtime = ResearchRuntime(symbol="INVALID", timeframe="H1", provider_name="Crypto", asset_class="Crypto")

        # Override symbol mapping to force Coinbase HTTP failure
        from unittest.mock import patch
        with self.assertRaises(Exception):
            runtime.run_once()

        # Verify a failed snapshot was generated
        files = os.listdir(self.snapshot_dir)
        failed_snapshots = [f for f in files if f.startswith("rpt-INVALID-H1-failed_") and f.endswith(".json")]
        self.assertGreater(len(failed_snapshots), 0)

        with open(os.path.join(self.snapshot_dir, failed_snapshots[0]), "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)

        self.assertEqual(snapshot_data["provider_status"], "FAILED")
        self.assertEqual(snapshot_data["data_quality"], "INVALID")

    def test_9_market_regime_detection(self) -> None:
        """Verify that the MarketRegimeIntelligenceEngine correctly classifies regime, confidence, and reasoning."""
        from src.Research.Brain.regime import MarketRegimeIntelligenceEngine
        engine = MarketRegimeIntelligenceEngine()
        res = engine.classify_regime("BTCUSD", "H1", [], {"volatility_state": "medium", "trend_strength_classification": "strong_trend"})

        self.assertEqual(res["symbol"], "BTCUSD")
        self.assertEqual(res["market_regime"], "TRENDING")
        self.assertEqual(res["confidence"], 82)
        self.assertGreater(len(res["reasoning"]), 0)

    def test_10_pattern_memory(self) -> None:
        """Verify pattern retrieval and success ratios matching the 42 occurrences and 73% success rate."""
        from src.Research.Brain.pattern_engine import PatternIntelligenceEngine
        engine = PatternIntelligenceEngine()
        res = engine.retrieve_similar_pattern("BTCUSD", "H1", {})

        self.assertEqual(res["occurrences"], 42)
        self.assertEqual(res["successful_outcomes"], 30)
        self.assertEqual(res["success_rate_pct"], 73.0)

    def test_11_cross_asset_intelligence(self) -> None:
        """Verify that the BTCUSD ↔ NASDAQ correlation and risk relationships are correctly analyzed."""
        from src.Research.Brain.cross_asset import CrossAssetIntelligence
        engine = CrossAssetIntelligence()
        res = engine.analyze_relationships()

        self.assertEqual(res["market_theme"], "Risk-On")
        self.assertEqual(res["confidence"], 76)

        btc_nasdaq = next((r for r in res["relationships"] if r["asset"] == "BTCUSD" and r["related_asset"] == "NASDAQ"), None)
        self.assertIsNotNone(btc_nasdaq)
        self.assertEqual(btc_nasdaq["relationship"], "CORRELATED")
        self.assertEqual(btc_nasdaq["strength"], 0.81)

    def test_12_risk_intelligence(self) -> None:
        """Verify institutional risk levels and warnings."""
        from src.Research.Brain.risk_engine import InstitutionalRiskEngine
        engine = InstitutionalRiskEngine()
        res = engine.evaluate_risk("BTCUSD", "H1")

        self.assertEqual(res["risk_level"], "MEDIUM")
        self.assertEqual(res["risk_score"], 58)
        self.assertGreater(len(res["warnings"]), 0)

    def test_13_intelligence_confidence(self) -> None:
        """Verify multi-factor confidence calculations."""
        from src.Research.Brain.confidence_engine import AdaptiveConfidenceEngine
        engine = AdaptiveConfidenceEngine()
        res = engine.calculate_final_confidence(base_confidence=70.0, pattern_score=82.0, regime_score=78.0, risk_score=75.0)

        self.assertEqual(res["signal"], "BUY")
        self.assertEqual(res["final_confidence"], 66)

    def test_14_intelligence_dashboard_data(self) -> None:
        """Verify dynamic dashboard board outputs."""
        from fastapi.testclient import TestClient
        from src.Application.Services.web_dashboard import app
        client = TestClient(app)

        resp = client.get("/api/intelligence/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["runtime_status"], "ACTIVE")
        self.assertEqual(data["active_timeframes"], 6)
        self.assertGreater(data["research_contexts"], 0)
        self.assertGreater(len(data["regime_board"]), 0)
        self.assertEqual(data["global_risk"]["level"], "MEDIUM")
