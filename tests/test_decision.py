import unittest

from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
from src.Decision.engine import AutonomousDecisionEngine


class TestBaseOnlyDecisionEngine(unittest.TestCase):
    def test_only_base_hierarchy_is_registered(self):
        self.assertEqual(StrategyOrchestrator.supported_strategies, ["BASE_HIERARCHY"])

    def test_missing_candles_fails_closed(self):
        report = StrategyOrchestrator().evaluate_all_strategies(
            symbol="XAUUSD", primary_timeframe="M1", candles=[]
        )
        self.assertEqual(report["candidates"], [])
        self.assertIsNone(report["best_candidate"])

    def test_legacy_portfolio_strategy_injection_is_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "Legacy portfolio-scoring decisions are disabled"):
            AutonomousDecisionEngine(object(), object(), object())


if __name__ == "__main__":
    unittest.main()
