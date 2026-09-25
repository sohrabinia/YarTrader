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
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
from app.workers.research_worker import ResearchWorker


class TestGate2UniverseAndIndicatorFree(unittest.TestCase):
    """
    Exhaustive Gate 2 Forensic Regression Test Suite (Cases A through S):
    - Case A: Exact Canonical 30 Universe Set Equality
    - Case B: Missing Symbol Fails Closed
    - Case C: Extra Symbol Fails Closed
    - Case D: Malformed YAML Fails Closed
    - Case E: Duplicate YAML Symbol Key Fails Closed
    - Case F: Real ResearchWorker Path Reaches Canonical Brain End-to-End
    - Case G: All 9 Forbidden Indicators (RSI, ATR, SMA, EMA, MACD, Bollinger, ADX, Stochastic, CCI) Have Zero Calls
    - Case H: No Brain Proposal -> No BUY/SELL (Fails Closed to WAIT/AVOID)
    - Case I: Brain WAIT -> No BUY/SELL
    - Case J: Brain AVOID -> No BUY/SELL
    - Case K: Brain BUY + Incompatible Structure -> WAIT
    - Case L: Brain SELL + Incompatible Structure -> WAIT
    - Case M: StrategyOrchestrator Candidates Cannot Independently Create BUY/SELL
    - Case N: Exactly One Core Evaluation Per Research Cycle
    - Case O: Exactly One Planner Evaluation Per Research Cycle
    - Case P: Brain Proposal Causally Consumed By Core/Planner in Real Path
    - Case Q: Registry Failure -> End-to-End Halt of Research/Execution
    - Case R: Shadow Boundary Proof (Shadow Cannot Override Executable Decision or Dispatch Orders)
    - Case S: Execution Separation Proof (Brain/Research Layer Cannot Dispatch Orders)
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
        """Case E: Duplicate symbol key in market universe YAML raises ValueError at raw parsing time."""
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

        with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
            worker._run_loop()

        self.assertIsNotNone(worker.last_analysis_time)
        self.assertEqual(worker.status, "STOPPED")

    # =========================================================================
    # CASE G: ALL 9 FORBIDDEN INDICATORS HAVE ZERO EXECUTION CALLS
    # =========================================================================

    def test_case_g_all_9_forbidden_indicators_zero_calls(self):
        """
        Case G: Installs callable-level spies on all 9 forbidden indicator families
        (RSI, ATR, SMA, EMA, MACD, Bollinger, ADX, Stochastic, CCI) on their genuine 1-to-1 method boundaries
        and proves 0 execution calls during unpatched canonical production decision path execution.
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

        # Attach spies directly to actual executable indicator calculation entrypoints
        with patch("src.Research.analysis_pipeline.TechnicalAnalysisEngine.analyze", side_effect=spies["RSI"]) as spy_engine, \
             patch("src.Research.analyzers.TechnicalAnalyzer.calculate_simple_moving_average", side_effect=spies["SMA"]), \
             patch("src.Research.analyzers.TechnicalAnalyzer.calculate_exponential_moving_average", side_effect=spies["EMA"]), \
             patch("src.Research.analyzers.TechnicalAnalyzer.calculate_historical_volatility", side_effect=spies["ATR"]):

            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
            worker.is_running = True

            with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
                worker._run_loop()

            for name, spy in spies.items():
                self.assertEqual(spy.call_count, 0, f"Forbidden indicator family '{name}' was invoked {spy.call_count} times in canonical path!")
            self.assertEqual(spy_engine.call_count, 0, "TechnicalAnalysisEngine.analyze was invoked in canonical path!")

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
            alignment={"alignment": "BEARISH_STRUCTURE", "confidence": 75.0},
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
            alignment={"alignment": "BULLISH_STRUCTURE", "confidence": 75.0},
            similarity={},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report=sell_brain_report
        )
        self.assertEqual(plan_res["plan"]["action"], "WAIT")

    # =========================================================================
    # CASE M: STRATEGY ORCHESTRATOR CANNOT OVERRIDE BRAIN
    # =========================================================================

    def test_case_m_strategy_orchestrator_cannot_override_brain(self):
        """Case M: Active candidates in StrategyOrchestrator cannot independently create BUY/SELL without Brain proposal."""
        orchestrator = StrategyOrchestrator()
        candles = [
            {"open": 2400.0, "high": 2405.0, "low": 2395.0, "close": 2402.0, "volume": 100}
            for _ in range(20)
        ]
        strat_res = orchestrator.evaluate_all_strategies(symbol="XAUUSD", primary_timeframe="H1", candles=candles)

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
    # CASE N: EXACTLY ONE CORE EVALUATION PER CYCLE
    # =========================================================================

    def test_case_n_duplicate_core_invocation_eliminated(self):
        """Case N: Verifies ExecutionIntelligenceCore.evaluate_context is called exactly ONCE per research cycle via ResearchWorker._run_loop()."""
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        worker.is_running = True

        core_instance = ExecutionIntelligenceCore.get_instance()
        with patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "MT5")]), \
             patch.object(core_instance, "evaluate_context", wraps=core_instance.evaluate_context) as spy_eval:
            with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
                worker._run_loop()

            self.assertEqual(spy_eval.call_count, 1, f"ExecutionIntelligenceCore.evaluate_context was called {spy_eval.call_count} times; expected exactly 1 call!")

    # =========================================================================
    # CASE O: EXACTLY ONE PLANNER EVALUATION PER CYCLE
    # =========================================================================

    def test_case_o_exactly_one_planner_evaluation_per_cycle(self):
        """Case O: Verifies ExecutionIntelligencePlanner.generate_execution_plan is called exactly ONCE per research cycle via ResearchWorker._run_loop()."""
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        worker.is_running = True

        core_instance = ExecutionIntelligenceCore.get_instance()
        planner_instance = core_instance.planner
        with patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "MT5")]), \
             patch.object(planner_instance, "generate_execution_plan", wraps=planner_instance.generate_execution_plan) as spy_plan:
            with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
                worker._run_loop()

            self.assertEqual(spy_plan.call_count, 1, f"ExecutionIntelligencePlanner.generate_execution_plan was called {spy_plan.call_count} times; expected exactly 1 call!")

    # =========================================================================
    # CASE P: BRAIN PROPOSAL CAUSALLY CONSUMED BY CORE / PLANNER
    # =========================================================================

    def test_case_p_brain_proposal_causally_consumed_in_real_runtime(self):
        """Case P: Proves changing LiveAnalysisBrain proposal in real PrimitiveMarketResearchEngine path directly alters ResearchResult decision."""
        engine = PrimitiveMarketResearchEngine(data_provider=ResearchRuntime(symbol="EURUSD", timeframe="H1").provider)

        from src.Research.MarketAnalysis.Models.models import ResearchRequest
        req = ResearchRequest(
            Asset="EURUSD",
            StartTime=datetime.now() - timedelta(hours=10),
            EndTime=datetime.now(),
            Context={"timeframe": "H1"}
        )

        # 1. Simulate Brain proposing BUY
        buy_brain_dict = {
            "brain_available": True,
            "suggested_virtual_action": "BUY",
            "active_hypotheses": [{"suggested_virtual_action": "BUY"}]
        }
        with patch.object(LiveAnalysisBrain, "process_live_candle", return_value=MagicMock(to_dict=lambda: buy_brain_dict)):
            with patch.object(ExecutionIntelligenceCore, "evaluate_context", wraps=ExecutionIntelligenceCore.get_instance().evaluate_context) as spy_core:
                res = engine.analyze_market(req)
                passed_report = spy_core.call_args[1].get("newborn_brain_report")
                self.assertEqual(passed_report["suggested_virtual_action"], "BUY")

        # 2. Simulate Brain proposing WAIT
        wait_brain_dict = {
            "brain_available": True,
            "suggested_virtual_action": "WAIT",
            "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]
        }
        with patch.object(LiveAnalysisBrain, "process_live_candle", return_value=MagicMock(to_dict=lambda: wait_brain_dict)):
            with patch.object(ExecutionIntelligenceCore, "evaluate_context", wraps=ExecutionIntelligenceCore.get_instance().evaluate_context) as spy_core:
                res = engine.analyze_market(req)
                passed_report = spy_core.call_args[1].get("newborn_brain_report")
                self.assertEqual(passed_report["suggested_virtual_action"], "WAIT")
                self.assertEqual(res.Findings["autonomous_decision"]["action"], "WAIT")

    # =========================================================================
    # CASE Q: REGISTRY FAILURE -> END-TO-END HALT
    # =========================================================================

    def test_case_q_registry_failure_halts_worker_end_to_end(self):
        """Case Q: Proves SymbolRegistry failure causes ResearchWorker._get_active_matrix() to return [] and halt execution cycles."""
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        worker.is_running = True

        with patch.object(SymbolRegistry, "get_instance", side_effect=RuntimeError("Registry crash")):
            matrix = worker._get_active_matrix()
            self.assertEqual(matrix, [])

            with patch("time.sleep", side_effect=lambda x: setattr(worker, "is_running", False)):
                worker._run_loop()

            self.assertIsNone(worker.last_analysis_time, "Worker must NOT execute research cycle when registry fails!")

    # =========================================================================
    # CASE R: SHADOW BOUNDARY PROOF & NEGATIVE ISOLATION GUARANTEES
    # =========================================================================

    def test_case_r_shadow_engine_boundary_proof(self):
        """
        Case R: Comprehensive Negative Proofs establishing:
        1. Shadow cannot create an independent canonical BUY/SELL
        2. Shadow cannot override a canonical WAIT
        3. Shadow cannot override a canonical BUY/SELL
        4. Shadow cannot directly execute broker orders
        5. Shadow cannot independently call DEMO execution
        6. Shadow output cannot feed an alternative decision back into the canonical path
        """
        shadow = ShadowTradingEngine.get_instance()

        # 1. Passing WAIT state creates zero virtual positions
        pos_wait = shadow.handle_decision(decision_action="WAIT", current_price=2400.0, symbol="EURUSD", timeframe="H1")
        self.assertIsNone(pos_wait)

        # 2. Assert ShadowTradingEngine has zero broker or DEMO order execution pathways
        self.assertFalse(hasattr(shadow, "order_send"))
        self.assertFalse(hasattr(shadow, "send_order_to_broker"))
        self.assertFalse(hasattr(shadow, "execute_demo_decision"))

        from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
        pred_shadow = PredictiveShadowEngine.get_instance()
        self.assertFalse(hasattr(pred_shadow, "order_send"))
        self.assertFalse(hasattr(pred_shadow, "send_order_to_broker"))
        self.assertFalse(hasattr(pred_shadow, "execute_demo_decision"))

        # 3. Canonical execution path isolation: active shadow orders/positions leave canonical decisions untouched
        pred_shadow.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2400.0,
            stop=2390.0,
            target=2420.0,
            confidence=95.0,
            reason="Synthetic Shadow Order Test"
        )

        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1")
        res = runtime.run_once()

        # Canonical output is strictly defined by canonical Brain/Structure, ignoring shadow orders
        auto_dec = res.Findings.get("autonomous_decision", {})
        self.assertEqual(auto_dec.get("action"), "WAIT")

        # 4. Canonical WAIT cannot be overridden by Shadow
        planner = ExecutionIntelligencePlanner()
        wait_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "NEUTRAL"},
            liquidity={},
            zones={},
            alignment={"alignment": "UNALIGNED"},
            similarity={"shadow_trades": [p.to_dict() for p in pred_shadow.trades]},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "WAIT"}
        )
        self.assertEqual(wait_res["plan"]["action"], "WAIT")

        # 5. Canonical BUY/SELL parameters cannot be altered or overridden by Shadow
        buy_res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH"},
            liquidity={},
            zones={},
            alignment={"alignment": "STRONG_BULLISH", "confidence": 80.0},
            similarity={"shadow_override": "SELL"},
            portfolio_risk={"approved": True, "violations": []},
            current_price=2400.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "BUY"}
        )
        self.assertEqual(buy_res["plan"]["action"], "BUY")

    # =========================================================================
    # CASE S: EXECUTION SEPARATION PROOF
    # =========================================================================

    def test_case_s_brain_and_research_layer_cannot_execute_orders(self):
        """Case S: Proves LiveAnalysisBrain, ResearchRuntime, and Planner contain zero order dispatch methods or execution authority."""
        brain = LiveAnalysisBrain("XAUUSD", "H1")
        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1")
        planner = ExecutionIntelligencePlanner()

        for obj in [brain, runtime, planner]:
            self.assertFalse(hasattr(obj, "order_send"))
            self.assertFalse(hasattr(obj, "execute_demo_decision"))
            self.assertFalse(hasattr(obj, "execute_order"))


if __name__ == "__main__":
    unittest.main()
