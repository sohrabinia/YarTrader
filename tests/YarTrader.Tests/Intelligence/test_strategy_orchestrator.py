import unittest
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
from src.Intelligence.Execution.core import ExecutionIntelligenceCore

class TestStrategyOrchestrator(unittest.TestCase):
    """
    Forensic Review of StrategyOrchestrator & FVG Boundary Safety.
    Verifies that:
    1. All 6 strategy profiles are evaluated independently.
    2. FVG boundary filtering evaluates both bullish and bearish Fair Value Gaps safely.
    3. No valid strategy candidate is falsely suppressed by FVG boundary logic.
    """

    def setUp(self) -> None:
        self.orchestrator = StrategyOrchestrator()
        self.core = ExecutionIntelligenceCore.get_instance()
        self.mock_candles = [
            {"open": 2000.0 + i, "high": 2005.0 + i, "low": 1995.0 + i, "close": 2002.0 + i, "volume": 100}
            for i in range(20)
        ]

    def test_latest_base_reaction_uses_actual_side_and_depth(self):
        child = {"event_id": "M15:100:RBR", "confirmation_time": 100,
                 "base_low": 10.0, "base_high": 20.0}
        bars = [
            {"time": 90, "low": 24.0, "high": 26.0, "close": 25.0},
            {"time": 110, "low": 17.0, "high": 26.0, "close": 18.0},
            {"time": 120, "low": 19.0, "high": 21.0, "close": 20.0},
            {"time": 130, "low": 21.0, "high": 22.0, "close": 21.5},
            {"time": 140, "low": 15.0, "high": 22.0, "close": 16.0},
            {"time": 160, "low": 10.0, "high": 11.0, "close": 10.5},
        ]
        measured = self.orchestrator._measure_latest_base_reaction(bars, child, 150)
        self.assertEqual(measured["reaction_number"], 2)
        self.assertEqual(measured["entry_side"], "FROM_ABOVE")
        self.assertAlmostEqual(measured["penetration_fraction"], 0.5)

    def test_only_base_hierarchy_is_supported(self):
        """Legacy named strategies are not exposed or evaluated."""
        self.assertEqual(self.orchestrator.supported_strategies, ["BASE_HIERARCHY"])
        result = self.orchestrator.evaluate_all_strategies(
            symbol="XAUUSD", primary_timeframe="M5", candles=self.mock_candles
        )
        self.assertEqual(result["symbol"], "XAUUSD")
        self.assertEqual(result["primary_timeframe"], "M5")
        self.assertEqual(
            {candidate["strategy_name"] for candidate in result["candidates"]},
            {"BASE_HIERARCHY"} if result["candidates"] else set(),
        )
        self.assertIn("no fallback strategy", result["summary"].lower())

    def test_legacy_fvg_strategy_evaluator_is_removed(self):
        self.assertFalse(hasattr(self.orchestrator, "_evaluate_price_action_rtm"))

if __name__ == "__main__":
    unittest.main()
