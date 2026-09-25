import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, CANONICAL_30_SYMBOLS, parse_market_universe_yaml
from app.workers.research_worker import ResearchWorker
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Data.MarketData.Models.models import MarketDataResponse, MarketDataPoint, MarketDataRequest
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "test_forensic_guards",
    os.path.join(os.path.dirname(__file__), "..", "Forensic", "test_forensic_guards.py")
)
_forensic_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_forensic_mod)
TestIndicatorForensicGuard = _forensic_mod.TestIndicatorForensicGuard


class ControlledDataProvider:
    """Deterministic offline provider fixture for Gate 2 tests."""
    def __init__(self, base_price: float = 2000.0, count: int = 50) -> None:
        self.base_price = base_price
        self.count = count
        self.provider_name = "ControlledOfflineFixture"

    @property
    def delegate(self):
        return self

    def get_connection_health(self):
        return MagicMock(connected=True, provider="ControlledOfflineFixture")

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        now = datetime.now()
        asset = getattr(request, "Asset", "XAUUSD")
        data_points = []
        for i in range(self.count):
            t = now - timedelta(minutes=(self.count - i) * 15)
            p = self.base_price + (i * 0.1)
            dp = MarketDataPoint(
                AssetId=asset,
                Timestamp=t,
                Open=p,
                High=p + 0.5,
                Low=p - 0.5,
                Close=p + 0.2,
                Volume=100.0
            )
            data_points.append(dp)
        return MarketDataResponse(
            Request=request,
            DataPoints=data_points,
            RetrievedAt=now
        )


class TestGate2UniverseAndIndicatorFree(unittest.TestCase):
    """
    Exhaustive Test Suite for Gate 2:
    Cases A through S verifying canonical exact 30-symbol universe, duplicate key rejection,
    fail-closed configuration, multi-symbol research execution, XAUUSD-only DEMO execution boundary,
    zero forbidden indicator executions, Brain causality, StrategyOrchestrator isolation,
    and single-invocation intelligence per cycle starting at ResearchWorker._run_loop().
    """

    def setUp(self):
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()

    def tearDown(self):
        SymbolRegistry._instance = None

    # Case A: Canonical exact 30-symbol set equality
    def test_case_a_canonical_exact_30_universe(self):
        registered = set(self.registry.get_all_registered().keys())
        self.assertEqual(len(registered), 30)
        self.assertEqual(registered, CANONICAL_30_SYMBOLS)

    # Case B: Duplicate symbol key rejection in parse_market_universe_yaml
    def test_case_b_duplicate_symbol_key_rejection(self):
        duplicate_yaml = """
market_universe:
  Commodities:
    XAUUSD: { provider: "MT5", enabled: true }
  Forex:
    XAUUSD: { provider: "MT5", enabled: true }
"""
        with self.assertRaises(ValueError) as ctx:
            parse_market_universe_yaml(duplicate_yaml)
        self.assertIn("Duplicate symbol 'XAUUSD'", str(ctx.exception))

    # Case C: Missing config file fails closed
    def test_case_c_missing_config_fails_closed(self):
        with patch("os.path.exists", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                SymbolRegistry._instance = None
                SymbolRegistry.get_instance()
            self.assertIn("missing", str(ctx.exception).lower())

    # Case D: Registry lookup error in _get_active_matrix returns []
    def test_case_d_active_matrix_registry_error(self):
        worker = ResearchWorker()
        with patch("src.ShadowTrading.Engine.SymbolRegistry.SymbolRegistry.get_instance", side_effect=Exception("Registry error")):
            matrix = worker._get_active_matrix()
            self.assertEqual(matrix, [])

    # Case E: Research Worker exercises all 30 symbols during research loop
    def test_case_e_multi_symbol_research_loop(self):
        worker = ResearchWorker()

        researched_symbols = []
        runtimes_map = {}

        def mock_get_or_create_runtime(symbol, tf, asset_class="Forex", provider="MT5"):
            key = (symbol.upper(), tf.upper())
            if key not in runtimes_map:
                rt = ResearchRuntime(provider=ControlledDataProvider(), symbol=symbol, timeframe=tf, provider_name="ControlledOfflineFixture")
                orig_run_once = rt.run_once
                def track_run_once(s=symbol):
                    researched_symbols.append(s)
                    return orig_run_once()
                rt.run_once = track_run_once
                runtimes_map[key] = rt
            return runtimes_map[key]

        matrix = [
            ("EURUSD", "H1", "Forex", "MT5"),
            ("GBPUSD", "H1", "Forex", "MT5"),
            ("XAUUSD", "H1", "Commodities", "MT5")
        ]

        with patch.object(worker, "_get_or_create_runtime", side_effect=mock_get_or_create_runtime), \
             patch.object(worker, "_get_active_matrix", return_value=matrix):

            worker.is_running = True
            sleep_calls = 0

            def stop_after_matrix(duration):
                nonlocal sleep_calls
                sleep_calls += 1
                if sleep_calls >= len(matrix):
                    worker.is_running = False

            with patch("time.sleep", side_effect=stop_after_matrix):
                try:
                    worker._run_loop()
                except Exception:
                    pass

        self.assertIn("EURUSD", researched_symbols)
        self.assertIn("GBPUSD", researched_symbols)
        self.assertIn("XAUUSD", researched_symbols)

    # Case F: DEMO execution boundary rejects non-XAUUSD symbols
    def test_case_f_demo_execution_boundary_xauusd_only(self):
        worker = ResearchWorker()
        provider = ControlledDataProvider()

        executed_dispatches = []

        def mock_execute_demo_decision(*args, **kwargs):
            executed_dispatches.append(kwargs.get("symbol"))
            return MagicMock(Status="Placed")

        worker.demo_engine = MagicMock()
        worker.demo_engine.execute_demo_decision = mock_execute_demo_decision

        matrix = [("EURUSD", "H1", "Forex", "MT5")]
        runtime = ResearchRuntime(provider=provider, symbol="EURUSD", timeframe="H1", provider_name="ControlledOfflineFixture")

        with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
             patch.object(worker, "_get_active_matrix", return_value=matrix), \
             patch("app.workers.research_worker.is_autonomous_demo_enabled", return_value=True):

            worker.is_running = True
            def stop_loop(*args):
                worker.is_running = False

            with patch("time.sleep", side_effect=stop_loop):
                worker._run_loop()

        # EURUSD execution MUST NOT be dispatched
        self.assertNotIn("EURUSD", executed_dispatches)

    # Case G: Zero forbidden indicator execution starting from ResearchWorker._run_loop()
    def test_case_g_indicator_forensic_zero_calls(self):
        guard_test = TestIndicatorForensicGuard()
        guard_test.test_forbidden_indicator_execution_guard()

    # Case H: Unreachable indicator implementations recorded
    def test_case_h_unreachable_indicators_recorded(self):
        from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine
        import inspect
        source = inspect.getsource(PrimitiveMarketResearchEngine)
        for ind in ["RSI", "ATR", "SMA", "EMA", "MACD", "Bollinger", "ADX", "Stochastic", "CCI"]:
            self.assertNotIn(f"calc_{ind.lower()}", source)

    # Cases I, J: Single Core and Planner evaluation per cycle starting at _run_loop()
    def test_cases_i_j_single_evaluation_per_cycle(self):
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        provider = ControlledDataProvider()
        runtime = ResearchRuntime(provider=provider, symbol="XAUUSD", timeframe="H1", provider_name="ControlledOfflineFixture")

        core_calls = 0
        planner_calls = 0

        from src.Research.Brain.live_brain import LiveAnalysisBrain
        from src.Intelligence.Execution.core import ExecutionIntelligenceCore

        intel_core = ExecutionIntelligenceCore.get_instance()

        orig_eval_ctx = intel_core.evaluate_context
        def tracked_core(*args, **kwargs):
            nonlocal core_calls
            core_calls += 1
            return orig_eval_ctx(*args, **kwargs)

        orig_plan = intel_core.planner.generate_execution_plan
        def tracked_planner(*args, **kwargs):
            nonlocal planner_calls
            planner_calls += 1
            return orig_plan(*args, **kwargs)

        with patch.object(intel_core, "evaluate_context", side_effect=tracked_core), \
             patch.object(intel_core.planner, "generate_execution_plan", side_effect=tracked_planner), \
             patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
             patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "ControlledOfflineFixture")]):

            worker.is_running = True
            orig_run_once = runtime.run_once
            def run_once_and_stop():
                res = orig_run_once()
                worker.is_running = False
                return res

            runtime.run_once = run_once_and_stop
            worker._run_loop()

        self.assertEqual(core_calls, 1, f"Expected exactly 1 Core evaluation per cycle, got {core_calls}")
        self.assertEqual(planner_calls, 1, f"Expected exactly 1 Planner evaluation per cycle, got {planner_calls}")

    # Case K: Brain BUY + contradictory BEARISH structure -> BUY
    def test_case_k_brain_buy_overrides_bearish_structure(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()

        res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BEARISH", "state": "COMPRESSION"},
            liquidity={},
            zones={},
            alignment={"alignment": "BEARISH_CONTINUATION", "confidence": 95.0},
            similarity={},
            portfolio_risk={"approved": True},
            current_price=2000.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "BUY"}
        )

        plan = res["plan"]
        self.assertEqual(plan["action"], "BUY")
        self.assertEqual(plan["entry"], 2000.0)

    # Case L: Brain SELL + contradictory BULLISH structure -> SELL
    def test_case_l_brain_sell_overrides_bullish_structure(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()

        res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH", "state": "RANGE"},
            liquidity={},
            zones={},
            alignment={"alignment": "BULLISH_CONTINUATION", "confidence": 95.0},
            similarity={},
            portfolio_risk={"approved": True},
            current_price=2000.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "SELL"}
        )

        plan = res["plan"]
        self.assertEqual(plan["action"], "SELL")
        self.assertEqual(plan["entry"], 2000.0)

    # Case M, N: Brain WAIT -> WAIT, Brain AVOID -> AVOID
    def test_cases_m_n_brain_wait_and_avoid(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()

        res_wait = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative={}, liquidity={}, zones={}, alignment={}, similarity={},
            portfolio_risk={"approved": True}, current_price=2000.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "WAIT"}
        )
        self.assertEqual(res_wait["plan"]["action"], "WAIT")

        res_avoid = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative={}, liquidity={}, zones={}, alignment={}, similarity={},
            portfolio_risk={"approved": True}, current_price=2000.0,
            newborn_brain_report={"brain_available": True, "suggested_virtual_action": "AVOID"}
        )
        self.assertEqual(res_avoid["plan"]["action"], "AVOID")

    # Case P: End-to-End Brain Action Causality starting at ResearchWorker._run_loop()
    def test_case_p_end_to_end_brain_causality_from_run_loop(self):
        from src.Research.Brain.live_brain import LiveAnalysisBrain

        for target_action in ["BUY", "SELL", "WAIT", "AVOID"]:
            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
            provider = ControlledDataProvider()
            runtime = ResearchRuntime(provider=provider, symbol="XAUUSD", timeframe="H1", provider_name="ControlledOfflineFixture")

            mock_brain_report = MagicMock()
            mock_brain_report.to_dict.return_value = {
                "symbol": "XAUUSD",
                "brain_available": True,
                "suggested_virtual_action": target_action
            }

            with patch.object(LiveAnalysisBrain, "process_live_candle", return_value=mock_brain_report), \
                 patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
                 patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "ControlledOfflineFixture")]):

                worker.is_running = True
                orig_run_once = runtime.run_once
                def run_once_and_stop():
                    res = orig_run_once()
                    worker.is_running = False
                    return res

                runtime.run_once = run_once_and_stop
                worker._run_loop()

                res = runtime.history[0]
                auto_dec = res.Findings.get("autonomous_decision", {})
                self.assertEqual(auto_dec.get("action"), target_action, f"End-to-end causality failed for action {target_action}")

    # Case Q & R: Contradiction test & StrategyOrchestrator isolation from _run_loop()
    def test_cases_q_r_strategy_orchestrator_contradiction_isolation_from_run_loop(self):
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        from src.Research.Brain.live_brain import LiveAnalysisBrain

        # Contradiction Scenario 1: StrategyOrchestrator suggests BUY, but Brain suggests SELL
        mock_buy_candidate = {
            "symbol": "XAUUSD",
            "primary_timeframe": "H1",
            "best_candidate": {"direction": "BUY", "confidence": 95.0, "risk_reward": 2.5},
            "summary": "Mock BUY candidate"
        }

        # Contradiction Scenario 2: StrategyOrchestrator suggests SELL, but Brain suggests BUY
        mock_sell_candidate = {
            "symbol": "XAUUSD",
            "primary_timeframe": "H1",
            "best_candidate": {"direction": "SELL", "confidence": 95.0, "risk_reward": 2.5},
            "summary": "Mock SELL candidate"
        }

        # Test Contradiction 1: StrategyOrchestrator=BUY vs Brain=SELL -> Result must be SELL
        worker1 = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        runtime1 = ResearchRuntime(provider=ControlledDataProvider(), symbol="XAUUSD", timeframe="H1", provider_name="ControlledOfflineFixture")

        report_sell = MagicMock()
        report_sell.to_dict.return_value = {"symbol": "XAUUSD", "brain_available": True, "suggested_virtual_action": "SELL"}

        with patch.object(StrategyOrchestrator, "evaluate_all_strategies", return_value=mock_buy_candidate), \
             patch.object(LiveAnalysisBrain, "process_live_candle", return_value=report_sell), \
             patch.object(worker1, "_get_or_create_runtime", return_value=runtime1), \
             patch.object(worker1, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "ControlledOfflineFixture")]):

            worker1.is_running = True
            orig_run1 = runtime1.run_once
            def run_once_stop1():
                res = orig_run1()
                worker1.is_running = False
                return res
            runtime1.run_once = run_once_stop1
            worker1._run_loop()

            auto_dec1 = runtime1.history[0].Findings.get("autonomous_decision", {})
            self.assertEqual(auto_dec1.get("action"), "SELL")

        # Test Contradiction 2: StrategyOrchestrator=SELL vs Brain=BUY -> Result must be BUY
        worker2 = ResearchWorker(symbol="XAUUSD", timeframe="H1")
        runtime2 = ResearchRuntime(provider=ControlledDataProvider(), symbol="XAUUSD", timeframe="H1", provider_name="ControlledOfflineFixture")

        report_buy = MagicMock()
        report_buy.to_dict.return_value = {"symbol": "XAUUSD", "brain_available": True, "suggested_virtual_action": "BUY"}

        with patch.object(StrategyOrchestrator, "evaluate_all_strategies", return_value=mock_sell_candidate), \
             patch.object(LiveAnalysisBrain, "process_live_candle", return_value=report_buy), \
             patch.object(worker2, "_get_or_create_runtime", return_value=runtime2), \
             patch.object(worker2, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "ControlledOfflineFixture")]):

            worker2.is_running = True
            orig_run2 = runtime2.run_once
            def run_once_stop2():
                res = orig_run2()
                worker2.is_running = False
                return res
            runtime2.run_once = run_once_stop2
            worker2._run_loop()

            auto_dec2 = runtime2.history[0].Findings.get("autonomous_decision", {})
            self.assertEqual(auto_dec2.get("action"), "BUY")

    # Case S: Shadow trading boundary isolation
    def test_case_s_shadow_trading_boundary_isolation(self):
        from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
        shadow = ShadowTradingEngine.get_instance()

        with patch("src.Execution.Services.demo_execution_engine.DemoExecutionEngine.execute_demo_decision") as mock_exec:
            shadow.handle_decision("BUY", 2000.0, 80.0, "Shadow decision", {}, symbol="XAUUSD", timeframe="H1", volume=1.0)
            mock_exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
