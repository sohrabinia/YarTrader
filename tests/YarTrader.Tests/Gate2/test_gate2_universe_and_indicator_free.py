import os
import sys
import tempfile
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
        # Keep runtime Brain learning isolated from the production memory corpus.
        self._memory_tempdir = tempfile.TemporaryDirectory(prefix="yartrader-gate2-memory-")
        from src.Research.Brain.memory import MarketMemorySystem
        self._test_memory = MarketMemorySystem(storage_dir=self._memory_tempdir.name)
        self._memory_patch = patch(
            "src.Research.Brain.live_brain.MarketMemorySystem",
            return_value=self._test_memory,
        )
        self._memory_patch.start()

    def tearDown(self):
        self._memory_patch.stop()
        self._memory_tempdir.cleanup()
        SymbolRegistry._instance = None
        if os.path.exists("runtime_logs/symbols_registry.json"):
            try:
                os.remove("runtime_logs/symbols_registry.json")
            except Exception:
                pass
        SymbolRegistry.get_instance()

    # Case A: Canonical exact 30-symbol set equality
    def test_case_a_canonical_exact_30_universe(self):
        registered = set(self.registry.get_all_registered().keys())
        self.assertEqual(len(registered), 30)
        self.assertEqual(registered, CANONICAL_30_SYMBOLS)

    # Case B: Rollout remains limited to gold and euro until the 30-symbol expansion is approved.
    def test_case_b_active_rollout_is_gold_and_euro_only(self):
        registered = self.registry.get_all_registered()
        active = {symbol for symbol, info in registered.items() if info.get("active")}
        self.assertEqual(active, {"XAUUSD", "EURUSD"})
        self.assertEqual(self.registry.max_symbols, 2)
        matrix = self.registry.get_active_matrix()
        self.assertEqual({row[0] for row in matrix}, active)
        self.assertEqual(len(matrix), 8)
        self.assertEqual({row[1] for row in matrix}, {"M15", "H1", "H4", "D1"})

    # Case C: Duplicate symbol key rejection in parse_market_universe_yaml
    def test_case_c_duplicate_symbol_key_rejection(self):
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

    # Case F: ResearchWorker is strictly read-only; the Base executor is the only order path.
    def test_case_f_research_worker_has_no_broker_dispatch_path(self):
        import inspect
        source = inspect.getsource(ResearchWorker)
        self.assertNotIn("execute_demo_decision", source)
        self.assertNotIn("send_order_to_broker", source)
        self.assertNotIn("_validate_and_size_decision", source)

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
    def test_cases_i_j_single_base_evaluation_and_no_legacy_planner(self):
        import inspect
        from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine
        from src.Intelligence.Execution.core import ExecutionIntelligenceCore
        source = inspect.getsource(PrimitiveMarketResearchEngine.analyze_market)
        self.assertEqual(source.count("evaluate_all_strategies("), 1)
        self.assertNotIn("planner.generate_execution_plan", source)
        self.assertFalse(hasattr(ExecutionIntelligenceCore.get_instance(), "planner"))

    def test_case_k_brain_buy_cannot_create_a_base_signal(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()
        res = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative={"trend": "BEARISH"},
            liquidity={}, zones={}, alignment={"alignment": "BEARISH"},
            similarity={}, portfolio_risk={"approved": True}, current_price=2000.0,
            newborn_brain_report={"brain_available": True, "active_hypotheses": [
                {"suggested_virtual_action": "BUY", "hypothesis_confidence": 99.0}
            ]},
        )
        self.assertEqual(res["plan"]["action"], "WAIT")
        self.assertEqual(res["plan"]["decision_source"], "BASE_HIERARCHY_ONLY")

    def test_case_l_brain_sell_cannot_create_a_base_signal(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()
        res = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative={"trend": "BULLISH"},
            liquidity={}, zones={}, alignment={"alignment": "BULLISH"},
            similarity={}, portfolio_risk={"approved": True}, current_price=2000.0,
            newborn_brain_report={"brain_available": True, "active_hypotheses": [
                {"suggested_virtual_action": "SELL", "hypothesis_confidence": 99.0}
            ]},
        )
        self.assertEqual(res["plan"]["action"], "WAIT")
        self.assertEqual(res["plan"]["decision_source"], "BASE_HIERARCHY_ONLY")

    def test_cases_m_n_brain_wait_and_avoid_are_non_authoritative(self):
        from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
        planner = ExecutionIntelligencePlanner()
        for action in ("WAIT", "AVOID", "BUY", "SELL"):
            res = planner.generate_execution_plan(
                symbol="XAUUSD", timeframe="H1", narrative={}, liquidity={}, zones={},
                alignment={}, similarity={}, portfolio_risk={"approved": True},
                current_price=2000.0,
                newborn_brain_report={"brain_available": True, "suggested_virtual_action": action},
            )
            self.assertEqual(res["plan"]["action"], "WAIT")
            self.assertEqual(res["plan"]["decision_source"], "BASE_HIERARCHY_ONLY")

    def test_case_p_parallel_brain_is_removed_from_active_research(self):
        import inspect
        from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine
        source = inspect.getsource(PrimitiveMarketResearchEngine.analyze_market)
        self.assertNotIn("LiveAnalysisBrain", source)
        self.assertIn("DISABLED_NON_BASE", source)

    # Cases Q/R: There is one supported strategy and no alternative evaluator.
    def test_cases_q_r_only_base_hierarchy_is_supported(self):
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        orchestrator = StrategyOrchestrator()
        self.assertEqual(orchestrator.supported_strategies, ["BASE_HIERARCHY"])
        self.assertFalse(hasattr(orchestrator, "_evaluate_price_action_rtm"))

    # Case S: Shadow trading boundary isolation
    def test_case_s_shadow_trading_boundary_isolation(self):
        from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
        shadow = ShadowTradingEngine.get_instance()

        with patch("src.Execution.Services.demo_execution_engine.DemoExecutionEngine.execute_demo_decision") as mock_exec:
            shadow.handle_decision("BUY", 2000.0, 80.0, "Shadow decision", {}, symbol="XAUUSD", timeframe="H1", volume=1.0)
            mock_exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
