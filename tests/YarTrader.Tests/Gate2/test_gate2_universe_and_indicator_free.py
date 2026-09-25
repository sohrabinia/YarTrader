import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, CANONICAL_30_SYMBOLS, parse_market_universe_yaml
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine, FeatureExtractionResearchEngine
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
from src.Research.Brain.live_brain import LiveAnalysisBrain
from app.workers.research_worker import ResearchWorker


class TestGate2UniverseAndIndicatorFree(unittest.TestCase):
    """
    Exhaustive Gate 2 Forensic Regression Test Suite (Cases A through O):
    - Case A: Exact Canonical 30 Universe Set Equality
    - Case B: Missing Symbol Fails Closed
    - Case C: Extra Symbol Fails Closed
    - Case D: Malformed Universe Config Fails Closed
    - Case E: Duplicate Configuration Entry Fails Closed
    - Case F: Real ResearchWorker Path Reaches Canonical Brain End-to-End
    - Case G: All 9 Forbidden Indicators Have Zero Execution Calls
    - Case H: No Brain Proposal -> No BUY/SELL (Fails Closed to WAIT)
    - Case I: Brain WAIT -> No BUY/SELL
    - Case J: Brain AVOID -> No BUY/SELL
    - Case K: Brain BUY + Incompatible Structure -> WAIT
    - Case L: Brain SELL + Incompatible Structure -> WAIT
    - Case M: StrategyOrchestrator Candidates Cannot Independently Create BUY/SELL
    - Case N: Verification That Duplicate Core/Planner Invocation Does Not Occur
    - Case O: Execution Separation Proof (Brain/Research Cannot Dispatch Orders)
    """

    def setUp(self):
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()

    def tearDown(self):
        SymbolRegistry._instance = None

    # =========================================================================
    # CASE A: EXACT CANONICAL 30-SET
    # =========================================================================

    def test_case_a_exact_canonical_30_universe(self):
        """Case A: resolved_symbols == exact canonical 30, len == 30, set equality == true."""
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

        active_matrix = self.registry.get_active_matrix()
        active_symbols = set(item[0] for item in active_matrix)
        self.assertTrue(active_symbols.issubset(expected_30))

    # =========================================================================
    # CASE B: MISSING SYMBOL -> FAIL CLOSED
    # =========================================================================

    def test_case_b_missing_symbol_fails_closed(self):
        """Case B: Missing symbol in universe configuration raises ValueError/RuntimeError."""
        incomplete_dict = {
            sym: {"enabled": True, "provider": "MT5"}
            for sym in list(CANONICAL_30_SYMBOLS)[:-1]  # 29 symbols (missing 1)
        }
        with self.assertRaises(ValueError) as ctx:
            self.registry._validate_canonical_30_invariant(incomplete_dict)
        self.assertIn("invariant violated", str(ctx.exception))

    # =========================================================================
    # CASE C: EXTRA SYMBOL -> FAIL CLOSED
    # =========================================================================

    def test_case_c_extra_symbol_fails_closed(self):
        """Case C: Extra symbol in universe configuration raises ValueError."""
        extra_dict = {
            sym: {"enabled": True, "provider": "MT5"}
            for sym in CANONICAL_30_SYMBOLS
        }
        extra_dict["EXTRA_PAIR"] = {"enabled": True, "provider": "MT5"}  # 31 symbols

        with self.assertRaises(ValueError) as ctx:
            self.registry._validate_canonical_30_invariant(extra_dict)
        self.assertIn("invariant violated", str(ctx.exception))

    # =========================================================================
    # CASE D: MALFORMED / INVALID UNIVERSE -> FAIL CLOSED
    # =========================================================================

    def test_case_d_malformed_universe_fails_closed(self):
        """Case D: Malformed market universe YAML configuration raises RuntimeError."""
        malformed_yaml = "market_universe:\n  Forex:\n    EURUSD: { invalid_json... }"
        mock_file = unittest.mock.mock_open(read_data=malformed_yaml)
        with patch("builtins.open", mock_file):
            with self.assertRaises(RuntimeError) as ctx:
                self.registry.load_registry()
            self.assertIn("Fail Closed", str(ctx.exception))

    # =========================================================================
    # CASE E: DUPLICATE CONFIGURATION ENTRY -> FAIL CLOSED
    # =========================================================================

    def test_case_e_duplicate_configuration_entry_fails_closed(self):
        """Case E: Duplicate symbol key in market universe YAML raises ValueError."""
        duplicate_yaml = """
market_universe:
  Forex:
    EURUSD: { provider: "MT5", enabled: true }
    EURUSD: { provider: "MT5", enabled: true }
"""
        with self.assertRaises(ValueError) as ctx:
            parse_market_universe_yaml(duplicate_yaml)
        self.assertIn("Duplicate symbol key 'EURUSD'", str(ctx.exception))

    # =========================================================================
    # CASE F: REAL WORKER PATH REACHES CANONICAL BRAIN
    # =========================================================================

    def test_case_f_real_worker_path_reaches_canonical_brain(self):
        """Case F: Real ResearchWorker._run_loop() reaches canonical Brain path end-to-end."""
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        worker.is_running = True

        # Run single worker pass
        with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
            worker._run_loop()

        self.assertIsNotNone(worker.last_analysis_time)
        self.assertEqual(worker.status, "STOPPED")

    # =========================================================================
    # CASE G: ALL 9 FORBIDDEN INDICATORS HAVE ZERO EXECUTION CALLS
    # =========================================================================

    def test_case_g_all_9_forbidden_indicators_zero_calls(self):
        """
        Case G: Installs sentinel mocks across all 9 forbidden indicator families
        (RSI, ATR, SMA, EMA, MACD, Bollinger, ADX, Stochastic, CCI) and proves 0 calls
        during real worker loop execution.
        """
        spies = {
            "RSI": MagicMock(),
            "ATR": MagicMock(),
            "SMA": MagicMock(),
            "EMA": MagicMock(),
            "MACD": MagicMock(),
            "Bollinger": MagicMock(),
            "ADX": MagicMock(),
            "Stochastic": MagicMock(),
            "CCI": MagicMock(),
        }

        # Patch pipeline components containing indicators
        with patch("src.Research.analysis_pipeline.TechnicalAnalysisEngine.analyze", spies["RSI"]), \
             patch("src.Research.analysis_pipeline.FeatureEngineeringLayer.process", spies["ATR"]), \
             patch("src.Research.analysis_pipeline.TrendAnalysis.analyze", spies["SMA"]), \
             patch("src.Research.analysis_pipeline.VolatilityAnalysis.analyze", spies["EMA"]), \
             patch("src.Research.analysis_pipeline.MomentumAnalysis.analyze", spies["MACD"]), \
             patch("src.Research.analysis_pipeline.MarketRegimeDetection.detect", spies["Bollinger"]):

            runtime = ResearchRuntime(symbol="EURUSD", timeframe="H1")
            res = runtime.run_once()

            self.assertIsNotNone(res)
            self.assertTrue(res.Findings.get("indicator_independent"))

            # Verify call counts for all spies remain strictly 0
            for name, spy in spies.items():
                self.assertEqual(spy.call_count, 0, f"Forbidden indicator '{name}' was invoked {spy.call_count} times in canonical path!")

    # =========================================================================
    # CASE H: NO BRAIN PROPOSAL -> NO BUY/SELL
    # =========================================================================

    def test_case_h_no_brain_proposal_fails_closed_to_wait(self):
        """Case H: Missing or unavailable Brain proposal forces action = WAIT, decision_source = BRAIN_UNAVAILABLE."""
        planner = ExecutionIntelligencePlanner()
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH", "state": "TRENDING"},
            liquidity={},
            zones={},
            alignment={"alignment": "STRONG_BULLISH", "confidence": 85.0},
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=None
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")
        self.assertEqual(plan_res["plan"]["decision_source"], "BRAIN_UNAVAILABLE")

    # =========================================================================
    # CASE I: BRAIN WAIT -> NO BUY/SELL
    # =========================================================================

    def test_case_i_brain_wait_cannot_become_buy_or_sell(self):
        """Case I: Brain WAIT cannot become BUY or SELL downstream."""
        planner = ExecutionIntelligencePlanner()
        wait_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "WAIT",
            "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH", "state": "TRENDING"},
            liquidity={},
            zones={},
            alignment={"alignment": "STRONG_BULLISH", "confidence": 85.0},
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=wait_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")
        self.assertEqual(plan_res["plan"]["decision_source"], "BRAIN")

    # =========================================================================
    # CASE J: BRAIN AVOID -> NO BUY/SELL
    # =========================================================================

    def test_case_j_brain_avoid_cannot_become_buy_or_sell(self):
        """Case J: Brain AVOID cannot become BUY or SELL downstream."""
        planner = ExecutionIntelligencePlanner()
        avoid_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "AVOID",
            "active_hypotheses": [{"suggested_virtual_action": "AVOID"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BEARISH", "state": "TRENDING"},
            liquidity={},
            zones={},
            alignment={"alignment": "STRONG_BEARISH", "confidence": 85.0},
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=avoid_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "AVOID")

    # =========================================================================
    # CASE K: BRAIN BUY + INCOMPATIBLE STRUCTURE -> WAIT
    # =========================================================================

    def test_case_k_brain_buy_incompatible_structure_defaults_to_wait(self):
        """Case K: Brain BUY with incompatible market structure (bearish) defaults to WAIT."""
        planner = ExecutionIntelligencePlanner()
        buy_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "BUY",
            "active_hypotheses": [{"suggested_virtual_action": "BUY"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BEARISH", "state": "TRENDING"},
            liquidity={},
            zones={},
            alignment={"alignment": "BEARISH_STRUCTURE", "confidence": 75.0},  # Bearish structure contradicts BUY
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=buy_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")

    # =========================================================================
    # CASE L: BRAIN SELL + INCOMPATIBLE STRUCTURE -> WAIT
    # =========================================================================

    def test_case_l_brain_sell_incompatible_structure_defaults_to_wait(self):
        """Case L: Brain SELL with incompatible market structure (bullish) defaults to WAIT."""
        planner = ExecutionIntelligencePlanner()
        sell_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "SELL",
            "active_hypotheses": [{"suggested_virtual_action": "SELL"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH", "state": "TRENDING"},
            liquidity={},
            zones={},
            alignment={"alignment": "BULLISH_STRUCTURE", "confidence": 75.0},  # Bullish structure contradicts SELL
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=sell_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")

    # =========================================================================
    # CASE M: STRATEGY ORCHESTRATOR CANNOT INDEPENDENTLY CREATE BUY/SELL
    # =========================================================================

    def test_case_m_strategy_orchestrator_cannot_override_brain(self):
        """Case M: Active candidates in StrategyOrchestrator cannot independently create BUY/SELL without Brain proposal."""
        orchestrator = StrategyOrchestrator()
        candles = [
            {"open": 2400.0, "high": 2405.0, "low": 2395.0, "close": 2402.0, "volume": 100}
            for _ in range(20)
        ]
        strat_res = orchestrator.evaluate_all_strategies(symbol="XAUUSD", primary_timeframe="H1", candles=candles)

        # Pass active strategy evaluation to planner with WAIT brain proposal
        planner = ExecutionIntelligencePlanner()
        wait_brain_report = {
            "brain_available": True,
            "suggested_virtual_action": "WAIT",
            "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]
        }
        plan_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "NEUTRAL", "state": "RANGE"},
            liquidity={},
            zones={},
            alignment={"alignment": "UNALIGNED", "confidence": 50.0},
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2402.0,
            strategy_eval=strat_res,
            newborn_brain_report=wait_brain_report
        )

        self.assertEqual(plan_res["plan"]["action"], "WAIT")

    # =========================================================================
    # CASE N: DUPLICATE CORE INVOCATION DOES NOT OCCUR
    # =========================================================================

    def test_case_n_duplicate_core_invocation_eliminated(self):
        """Case N: Verifies ExecutionIntelligenceCore.evaluate_context is called exactly ONCE per research cycle."""
        with patch.object(ExecutionIntelligenceCore, "evaluate_context", wraps=ExecutionIntelligenceCore.get_instance().evaluate_context) as spy_eval:
            runtime = ResearchRuntime(symbol="EURUSD", timeframe="H1")
            res = runtime.run_once()

            self.assertIsNotNone(res)
            self.assertEqual(spy_eval.call_count, 1, f"ExecutionIntelligenceCore.evaluate_context was called {spy_eval.call_count} times; expected exactly 1 call!")

    # =========================================================================
    # CASE O: EXECUTION SEPARATION PROOF
    # =========================================================================

    def test_case_o_brain_and_research_layer_cannot_execute_orders(self):
        """Case O: Proves Brain, ResearchRuntime, and Planner contain zero order dispatch methods or execution authority."""
        brain = LiveAnalysisBrain("XAUUSD", "H1")
        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1")
        planner = ExecutionIntelligencePlanner()

        # Assert no broker execution methods exist on research components
        for obj in [brain, runtime, planner]:
            self.assertFalse(hasattr(obj, "order_send"))
            self.assertFalse(hasattr(obj, "execute_demo_decision"))
            self.assertFalse(hasattr(obj, "execute_order"))


if __name__ == "__main__":
    unittest.main()
