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

    def test_evaluate_all_strategies_including_base_engulf_reversal(self):
        """Verifies all supported strategy profiles including BASE_ENGULF_REVERSAL are evaluated independently."""
        res = self.orchestrator.evaluate_all_strategies(
            symbol="XAUUSD",
            primary_timeframe="M5",
            candles=self.mock_candles
        )
        self.assertEqual(res["symbol"], "XAUUSD")
        self.assertEqual(res["primary_timeframe"], "M5")
        self.assertEqual(len(res["candidates"]), 7)

        strategy_names = [c["strategy_name"] for c in res["candidates"]]
        expected = ["FAST_SCALP", "SCALP", "DAY_TRADING", "JUMP", "PRICE_ACTION_RTM", "FRACTAL", "BASE_ENGULF_REVERSAL"]
        for exp in expected:
            self.assertIn(exp, strategy_names)

    def test_base_engulf_reversal_bullish_and_bearish(self):
        """Verifies BASE_ENGULF_REVERSAL correctly evaluates bullish and bearish engulfing candlestick setups."""
        # Bullish Engulfing setup candles at demand zone
        bullish_candles = [
            {"open": 2000.0, "high": 2002.0, "low": 1980.0, "close": 1985.0, "volume": 100}, # Bearish candle
            {"open": 1983.0, "high": 2008.0, "low": 1982.0, "close": 2005.0, "volume": 120}  # Bullish engulfing candle
        ]
        zones_bullish = {"order_blocks": [{"type": "BULLISH_OB", "bottom": 1980.0, "top": 2010.0}]}
        cand_bull = self.orchestrator._evaluate_base_engulf_reversal(
            symbol="XAUUSD",
            tf="M15",
            candles=bullish_candles,
            zones=zones_bullish,
            current_price=2005.0,
            pip_factor=0.1
        )
        self.assertEqual(cand_bull.direction, "BUY")
        self.assertEqual(cand_bull.strategy_name, "BASE_ENGULF_REVERSAL")
        self.assertTrue(cand_bull.is_reversal)
        self.assertGreater(cand_bull.risk_reward, 1.5)

        # Bearish Engulfing setup candles at supply zone
        bearish_candles = [
            {"open": 1985.0, "high": 2002.0, "low": 1983.0, "close": 2000.0, "volume": 100}, # Bullish candle
            {"open": 2002.0, "high": 2005.0, "low": 1978.0, "close": 1980.0, "volume": 120}  # Bearish engulfing candle
        ]
        zones_bearish = {"order_blocks": [{"type": "BEARISH_OB", "bottom": 1975.0, "top": 1990.0}]}
        cand_bear = self.orchestrator._evaluate_base_engulf_reversal(
            symbol="XAUUSD",
            tf="M15",
            candles=bearish_candles,
            zones=zones_bearish,
            current_price=1980.0,
            pip_factor=0.1
        )
        self.assertEqual(cand_bear.direction, "SELL")
        self.assertEqual(cand_bear.strategy_name, "BASE_ENGULF_REVERSAL")
        self.assertTrue(cand_bear.is_reversal)
        self.assertGreater(cand_bear.risk_reward, 1.5)

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
