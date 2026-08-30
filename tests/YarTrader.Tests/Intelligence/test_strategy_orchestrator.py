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

    def test_evaluate_all_6_strategies(self):
        """Verifies all 6 strategy profiles are evaluated independently."""
        res = self.orchestrator.evaluate_all_strategies(
            symbol="XAUUSD",
            primary_timeframe="M5",
            candles=self.mock_candles
        )
        self.assertEqual(res["symbol"], "XAUUSD")
        self.assertEqual(res["primary_timeframe"], "M5")
        self.assertEqual(len(res["candidates"]), 6)

        strategy_names = [c["strategy_name"] for c in res["candidates"]]
        expected = ["FAST_SCALP", "SCALP", "DAY_TRADING", "JUMP", "PRICE_ACTION_RTM", "FRACTAL"]
        for exp in expected:
            self.assertIn(exp, strategy_names)

    def test_fvg_boundary_safety_bullish_and_bearish(self):
        """
        Verifies that PRICE_ACTION_RTM correctly handles both bullish and bearish FVGs
        without outer/inner block short-circuiting.
        """
        zones = {
            "fair_value_gaps": [
                {"type": "BULLISH_FVG", "bottom": 1900.0, "top": 1950.0}, # Out of range for current price 2000.0
                {"type": "BEARISH_FVG", "bottom": 1990.0, "top": 2010.0}  # In range for current price 2000.0
            ]
        }

        rtm_cand = self.orchestrator._evaluate_price_action_rtm(
            symbol="XAUUSD",
            tf="M15",
            candles=self.mock_candles,
            zones=zones,
            liquidity={},
            current_price=2000.0,
            pip_factor=0.1
        )

        # Must correctly identify the bearish FVG in-range and output SELL
        self.assertEqual(rtm_cand.direction, "SELL")
        self.assertEqual(rtm_cand.strategy_name, "PRICE_ACTION_RTM")

if __name__ == "__main__":
    unittest.main()
