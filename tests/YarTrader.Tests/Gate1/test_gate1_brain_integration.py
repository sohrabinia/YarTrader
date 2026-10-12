import inspect
import unittest

from app.workers.research_worker import ResearchWorker
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine


class TestGate1BaseOnlyArchitecture(unittest.TestCase):
    """Regression contract: all actionable decisions originate from Base hierarchy only."""

    def test_parallel_brain_hypotheses_are_disabled(self):
        source = inspect.getsource(PrimitiveMarketResearchEngine.analyze_market)
        self.assertNotIn("LiveAnalysisBrain", source)
        self.assertIn("DISABLED_NON_BASE", source)

    def test_legacy_planner_never_uses_brain_to_create_action(self):
        planner = ExecutionIntelligencePlanner()
        for action in ("BUY", "SELL", "WAIT", "AVOID"):
            result = planner.generate_execution_plan(
                symbol="XAUUSD", timeframe="H1", narrative={"trend": "BULLISH"},
                liquidity={}, zones={}, alignment={"alignment": "BULLISH"},
                similarity={}, portfolio_risk={"approved": True}, current_price=2000.0,
                newborn_brain_report={"brain_available": True, "suggested_virtual_action": action,
                                      "active_hypotheses": [{"suggested_virtual_action": action}]},
            )
            self.assertEqual(result["plan"]["action"], "WAIT")
            self.assertEqual(result["plan"]["decision_source"], "BASE_HIERARCHY_ONLY")

    def test_core_returns_only_base_authority(self):
        result = ExecutionIntelligenceCore().evaluate_context("XAUUSD", "H1", [])
        self.assertEqual(result["plan"]["strategy"], "BASE_HIERARCHY")
        self.assertEqual(result["plan"]["action"], "WAIT")
        self.assertEqual(result["plan"]["decision_authority"], "BASE_HIERARCHY_ONLY")
        self.assertEqual(result["zones"]["status"], "DISABLED_NON_BASE")
        self.assertEqual(result["liquidity"]["status"], "DISABLED_NON_BASE")

    def test_research_worker_has_no_broker_execution_path(self):
        source = inspect.getsource(ResearchWorker)
        self.assertNotIn("execute_demo_decision", source)
        self.assertNotIn("send_order_to_broker", source)
        self.assertNotIn("_validate_and_size_decision", source)

    def test_strategy_orchestrator_exposes_only_base_hierarchy(self):
        orchestrator = StrategyOrchestrator()
        self.assertEqual(orchestrator.supported_strategies, ["BASE_HIERARCHY"])
        self.assertFalse(hasattr(orchestrator, "_evaluate_price_action_rtm"))

    def test_active_research_does_not_run_technical_indicators(self):
        source = inspect.getsource(PrimitiveMarketResearchEngine)
        for indicator in ("calc_rsi", "calc_atr", "calc_sma", "calc_ema", "calc_macd",
                          "calc_bollinger", "calc_adx", "calc_stochastic", "calc_cci"):
            self.assertNotIn(indicator, source)


if __name__ == "__main__":
    unittest.main()
