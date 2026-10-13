import unittest

from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator


class TestInBaseRotationPlanner(unittest.TestCase):
    def setUp(self):
        self.child = {
            "event_id": "base-1",
            "base_low": 100.0,
            "base_high": 110.0,
            "confirmation_time": 1000,
        }

    def test_bullish_rejection_near_lower_edge_proposes_buy_without_preset_tp(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 101.0, "high": 106.5, "low": 100.5, "close": 106.0}],
            {"bid": 105.0, "ask": 105.1},
            now=1120,
            spread_allowance=0.1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertEqual(result["setup_type"], "IN_BASE_ROTATION")
        self.assertEqual(result["direction"], "BUY")
        self.assertIsNone(result["take_profit"])
        self.assertGreater(result["net_reward_risk"], 1.0)

    def test_bearish_rejection_near_upper_edge_proposes_sell_without_preset_tp(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 109.0, "high": 109.5, "low": 104.0, "close": 104.5}],
            {"bid": 104.9, "ask": 105.0},
            now=1120,
            spread_allowance=0.1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertEqual(result["direction"], "SELL")
        self.assertIsNone(result["take_profit"])
        self.assertGreater(result["net_reward_risk"], 1.0)

    def test_outside_quote_still_proposes_retest_of_confirmed_base(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 101.0, "high": 106.5, "low": 100.5, "close": 106.0}],
            {"bid": 110.2, "ask": 110.3},
            now=1120,
            spread_allowance=0.1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertEqual(result["direction"], "BUY")
        self.assertIsNone(result["expires_at"])

    def test_directional_candle_inside_base_can_trade_without_edge_touch(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 104.0, "high": 106.0, "low": 103.0, "close": 105.5}],
            {"bid": 104.9, "ask": 105.0},
            now=1120,
            spread_allowance=0.1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["direction"], "BUY")
        self.assertEqual(result["setup_type"], "IN_BASE_ROTATION")
        self.assertIsNone(result["take_profit"])

    def test_higher_timeframe_closed_candle_can_seed_sparse_history_exploration(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 101.0, "high": 106.5, "low": 100.5, "close": 106.0}],
            {"bid": 105.0, "ask": 105.1},
            now=1120,
            spread_allowance=0.1,
            trigger_timeframe="H1",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertIsNone(result["expires_at"])

    def test_doji_inside_base_is_sampled_for_exploration(self):
        result = StrategyOrchestrator._plan_in_base_rotation(
            self.child,
            [{"time": 1100, "open": 105.0, "high": 106.0, "low": 104.0, "close": 105.0}],
            {"bid": 104.9, "ask": 105.0},
            now=1120,
            spread_allowance=0.1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertEqual(result["direction"], "BUY")


if __name__ == "__main__":
    unittest.main()
