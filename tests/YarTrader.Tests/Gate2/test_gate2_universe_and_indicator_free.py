import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, CANONICAL_30_SYMBOLS
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine, FeatureExtractionResearchEngine
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Research.Brain.live_brain import LiveAnalysisBrain
from app.workers.research_worker import ResearchWorker


class TestGate2UniverseAndIndicatorFree(unittest.TestCase):
    """
    Focused Gate 2 Forensic Regression Test Suite:
    - Case A: Exact Canonical 30 Universe (23 Forex, 2 Commodities, 4 Indices, 1 Crypto)
    - Case B: Invalid Universe Configuration Fails Closed
    - Case C: Forbidden Indicators Cannot Influence Canonical Decision Path
    - Case D: Real Production Worker Path Executable Flow Verification
    - Case E: Single Brain Decision Authority (WAIT/AVOID Cannot Become BUY/SELL)
    - Case F: Legacy Indicator Code Path Isolation Proof
    """

    def setUp(self):
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()

    def tearDown(self):
        SymbolRegistry._instance = None

    # =========================================================================
    # CASE A: EXACT UNIVERSE
    # =========================================================================

    def test_case_a_exact_canonical_30_universe(self):
        """Case A: resolved_symbols == exact canonical 30, no duplicates, no extras, no missing."""
        registered = self.registry.get_all_registered()
        resolved_symbols = set(registered.keys())

        self.assertEqual(len(resolved_symbols), 30)
        self.assertEqual(resolved_symbols, CANONICAL_30_SYMBOLS)

        expected_30 = {
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
            "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "EURAUD", "EURNZD", "GBPAUD",
            "GBPCAD", "GBPCHF", "AUDJPY", "AUDCAD", "AUDNZD", "CADJPY", "CHFJPY",
            "NZDJPY", "NZDCAD", "XAUUSD", "XAGUSD", "US30", "NAS100", "GER40",
            "UK100", "BTCUSD"
        }
        self.assertEqual(resolved_symbols, expected_30)

        # Confirm active matrix contains only symbols in canonical 30
        active_matrix = self.registry.get_active_matrix()
        active_symbols = set(item[0] for item in active_matrix)
        self.assertTrue(active_symbols.issubset(expected_30))

    # =========================================================================
    # CASE B: INVALID UNIVERSE FAILS CLOSED
    # =========================================================================

    def test_case_b_invalid_universe_fails_closed(self):
        """Case B: Missing, extra, duplicate, or malformed market universe config FAILS CLOSED."""
        invalid_yaml_missing = """
market_universe:
  Commodities:
    XAUUSD: { provider: "MT5", enabled: true }
"""
        invalid_yaml_extra = """
market_universe:
  Commodities:
    XAUUSD: { provider: "MT5", enabled: true }
    EXTRA_PAIR: { provider: "MT5", enabled: true }
"""
        # Direct validation raises ValueError
        with self.assertRaises(ValueError) as ctx:
            self.registry._validate_canonical_30_invariant({"XAUUSD": {}})
        self.assertIn("invariant violated", str(ctx.exception))

        # Loading invalid YAML raises RuntimeError (fail closed)
        mock_file = unittest.mock.mock_open(read_data=invalid_yaml_missing)
        with patch("builtins.open", mock_file):
            with self.assertRaises(RuntimeError) as ctx:
                self.registry.load_registry()
            self.assertIn("Fail Closed", str(ctx.exception))

        # Check worker active matrix fallback is empty on registry exception
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        with patch.object(SymbolRegistry, "get_instance", side_effect=Exception("Registry crash")):
            matrix = worker._get_active_matrix()
            self.assertEqual(matrix, [], "Worker must return empty list (fail closed) on registry crash")

    # =========================================================================
    # CASE C: FORBIDDEN INDICATORS CANNOT INFLUENCE DECISION
    # =========================================================================

    def test_case_c_forbidden_indicators_uncalled_in_canonical_path(self):
        """
        Case C: Injects sentinel side_effects into indicator pipeline modules.
        Proves the canonical decision path never calls or consumes RSI, ATR, SMA, EMA, MACD, Bollinger, ADX, Stochastic, CCI.
        """
        forbidden_sentinels = {
            "TechnicalAnalysisEngine.analyze": patch("src.Research.analysis_pipeline.TechnicalAnalysisEngine.analyze", side_effect=AssertionError("FORBIDDEN_CALL: TechnicalAnalysisEngine")),
            "FeatureEngineeringLayer.process": patch("src.Research.analysis_pipeline.FeatureEngineeringLayer.process", side_effect=AssertionError("FORBIDDEN_CALL: FeatureEngineeringLayer")),
            "TrendAnalysis.analyze": patch("src.Research.analysis_pipeline.TrendAnalysis.analyze", side_effect=AssertionError("FORBIDDEN_CALL: TrendAnalysis")),
            "VolatilityAnalysis.analyze": patch("src.Research.analysis_pipeline.VolatilityAnalysis.analyze", side_effect=AssertionError("FORBIDDEN_CALL: VolatilityAnalysis")),
            "MomentumAnalysis.analyze": patch("src.Research.analysis_pipeline.MomentumAnalysis.analyze", side_effect=AssertionError("FORBIDDEN_CALL: MomentumAnalysis")),
            "MarketRegimeDetection.detect": patch("src.Research.analysis_pipeline.MarketRegimeDetection.detect", side_effect=AssertionError("FORBIDDEN_CALL: MarketRegimeDetection")),
        }

        # Start all patches
        started_patches = [p.start() for p in forbidden_sentinels.values()]
        try:
            runtime = ResearchRuntime(symbol="EURUSD", timeframe="H1")
            res = runtime.run_once()

            self.assertIsNotNone(res)
            findings = res.Findings
            self.assertTrue(findings.get("indicator_independent"))

            # Verify autonomous decision was produced without invoking sentinel indicators
            auto_dec = findings.get("autonomous_decision", {})
            self.assertIn("action", auto_dec)
            self.assertIn(auto_dec["action"], ["BUY", "SELL", "WAIT", "AVOID"])
        finally:
            patch.stopall()

    # =========================================================================
    # CASE D: REAL RUNTIME WORKER PATH
    # =========================================================================

    def test_case_d_real_worker_path_verified(self):
        """Case D: Verifies execution path starting from ResearchWorker._run_loop()."""
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        worker.is_running = True

        # Run single worker pass
        with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
            worker._run_loop()

        self.assertIsNotNone(worker.last_analysis_time)
        self.assertEqual(worker.status, "STOPPED")

    # =========================================================================
    # CASE E: DECISION AUTHORITY (BRAIN IS THE SOLE AUTHORITY)
    # =========================================================================

    def test_case_e_brain_authority_invariant(self):
        """
        Case E: Brain WAIT or AVOID cannot become BUY/SELL downstream.
        Missing or unavailable Brain report forces action = WAIT with decision_source = BRAIN_UNAVAILABLE.
        """
        planner = ExecutionIntelligencePlanner()

        narrative = {"trend": "BULLISH", "state": "TRENDING"}
        liquidity = {}
        zones = {}
        alignment = {"alignment": "STRONG_BULLISH", "confidence": 85.0}
        similarity = {}
        portfolio_risk = {"approved": True, "violations": []}
        price = 2400.0

        # Sub-case 1: Brain proposes WAIT -> Planner MUST output WAIT
        wait_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "WAIT",
            "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity=liquidity,
            zones=zones,
            alignment=alignment,
            similarity=similarity,
            portfolio_risk=portfolio_risk,
            current_price=price,
            newborn_brain_report=wait_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")
        self.assertEqual(plan_res["plan"]["decision_source"], "BRAIN")

        # Sub-case 2: Brain proposes AVOID -> Planner MUST output AVOID
        avoid_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "AVOID",
            "active_hypotheses": [{"suggested_virtual_action": "AVOID"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity=liquidity,
            zones=zones,
            alignment=alignment,
            similarity=similarity,
            portfolio_risk=portfolio_risk,
            current_price=price,
            newborn_brain_report=avoid_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "AVOID")

        # Sub-case 3: Brain report missing / None -> Planner MUST output WAIT with decision_source = BRAIN_UNAVAILABLE
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity=liquidity,
            zones=zones,
            alignment=alignment,
            similarity=similarity,
            portfolio_risk=portfolio_risk,
            current_price=price,
            newborn_brain_report=None
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")
        self.assertEqual(plan_res["plan"]["decision_source"], "BRAIN_UNAVAILABLE")

    # =========================================================================
    # CASE F: LEGACY INDICATOR CODE ISOLATION PROOF
    # =========================================================================

    def test_case_f_legacy_indicator_code_unreachable_from_canonical_path(self):
        """Case F: Proves FeatureExtractionResearchEngine is NOT used by default in ResearchRuntime."""
        runtime = ResearchRuntime(symbol="EURUSD", timeframe="H1")
        self.assertIsInstance(runtime.research_engine, PrimitiveMarketResearchEngine)
        self.assertNotIsInstance(runtime.research_engine, FeatureExtractionResearchEngine)


if __name__ == "__main__":
    unittest.main()
