import unittest

from src.Decision.Intelligence.pending_order_planner import PendingOrderPlanner


class TestPendingOrderPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = PendingOrderPlanner(min_confidence=70, min_net_rr=1.5)
        self.quote = {"bid": 2000.0, "ask": 2000.2}

    def test_buy_retest_proposes_limit_order_without_execution(self):
        result = self.planner.plan({
            "direction": "BUY", "setup_type": "RETEST", "zone_low": 1998.0,
            "zone_high": 1999.0, "invalidation": 1995.0, "target": 2007.0,
            "atr": 5.0, "confidence": 82, "expires_at": 5000,
            "slippage_allowance": 0.1, "commission_price_allowance": 0.05,
        }, self.quote, now=1000)
        self.assertEqual(result.status, "PROPOSED")
        self.assertEqual(result.order_type, "BUY_LIMIT")
        self.assertLess(result.entry, self.quote["ask"])
        self.assertGreaterEqual(result.net_reward_risk, 1.5)

    def test_sell_breakout_proposes_stop_order(self):
        result = self.planner.plan({
            "direction": "SELL", "setup_type": "BREAKOUT", "zone_low": 1990.0,
            "zone_high": 1992.0, "invalidation": 2000.0, "target": 1970.0,
            "atr": 5.0, "confidence": 80, "expires_at": 5000,
        }, self.quote, now=1000)
        self.assertEqual(result.status, "PROPOSED")
        self.assertEqual(result.order_type, "SELL_STOP")
        self.assertLess(result.entry, self.quote["bid"])

    def test_expired_or_low_quality_scenario_waits(self):
        base = {"direction": "BUY", "setup_type": "RETEST", "zone_low": 1998,
                "zone_high": 1999, "invalidation": 1995, "target": 2007,
                "atr": 5, "confidence": 80, "expires_at": 900}
        self.assertEqual(self.planner.plan(base, self.quote, now=1000).status, "WAIT")
        base["expires_at"] = 5000
        base["confidence"] = 30
        self.assertEqual(self.planner.plan(base, self.quote, now=1000).status, "WAIT")

    def test_invalidated_opposite_or_expired_order_must_cancel(self):
        plan = {"expires_at": 2000}
        self.assertTrue(self.planner.should_cancel(plan, now=1000, zone_invalidated=True,
                                                  opposite_structure_confirmed=False, spread_atr=0.02))
        self.assertTrue(self.planner.should_cancel(plan, now=1000, zone_invalidated=False,
                                                  opposite_structure_confirmed=True, spread_atr=0.02))
        self.assertTrue(self.planner.should_cancel(plan, now=2000, zone_invalidated=False,
                                                  opposite_structure_confirmed=False, spread_atr=0.02))
        self.assertFalse(self.planner.should_cancel(plan, now=1000, zone_invalidated=False,
                                                   opposite_structure_confirmed=False, spread_atr=0.02))

    def test_retest_entry_can_use_researched_depth_inside_base(self):
        scenario = {"direction": "BUY", "setup_type": "RETEST", "zone_low": 1998.0,
                    "zone_high": 1999.0, "entry_price": 1998.25,
                    "invalidation": 1995.0, "target": 2007.0,
                    "atr": 5.0, "confidence": 82, "expires_at": 5000}
        result = self.planner.plan(scenario, self.quote, now=1000)
        self.assertEqual(result.status, "PROPOSED")
        self.assertAlmostEqual(result.entry, 1998.25)


if __name__ == "__main__":
    unittest.main()