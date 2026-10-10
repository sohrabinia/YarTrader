import unittest

from src.Decision.Intelligence.base_reaction_decision_engine import BaseReactionDecisionEngine


def ev(eid, tf, typ, direction, confirm, low, high):
    return {"event_id": eid, "timeframe": tf, "base_type": typ, "exit_direction": direction,
            "confirmation_time": confirm, "base_low": low, "base_high": high}


class BaseReactionDecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = BaseReactionDecisionEngine(min_samples=2, min_win_rate=0.5, min_mean_net_r=0.01)
        self.parent = ev("h1", "H1", "RBR", 1, 100, 98, 105)
        self.child = ev("m15", "M15", "RBR", 1, 200, 99, 100)
        self.micro = ev("m1", "M1", "RBR", 1, 900, 100.1, 100.2)
        self.reaction = {"base_id": "m15", "reaction_number": 1, "penetration_fraction": 0.2}
        self.setup = {"timeframe": "M15", "base_type": "RBR", "parent_relation": "NESTED",
                      "setup_type": "RETEST", "zone_low": 99.0, "zone_high": 100.0,
                      "invalidation": 98.5, "target": 104.0, "atr": 1.0,
                      "confidence": 85, "expires_at": 5000}
        self.quote = {"bid": 100.5, "ask": 100.6}
        key = self.engine.profile_key("M15", "RBR", "H1", "NESTED", True, 1, 0.2)
        self.engine.load_stats({"version": 1, "groups": {key: {"samples": 30, "win_rate": 0.75,
                               "mean_net_r": 0.2, "standard_error": 0.08, "mean_net_r_standard_error": 0.02}}})

    def evaluate(self, **kwargs):
        args = {"setup": self.setup, "quote": self.quote, "now": 1000,
                "parent": self.parent, "child": self.child, "micro": self.micro,
                "reaction": self.reaction}
        args.update(kwargs)
        return self.engine.evaluate(**args)

    def test_entry_proposal_requires_parent_child_micro_and_same_base_reaction(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "ENTRY_PROPOSAL")
        self.assertEqual(result["structure"]["penetration_bin"], "EDGE")
        self.assertFalse(result["execution_enabled"])

    def test_selects_best_qualified_depth_and_uses_that_limit_price(self):
        outer = self.engine.profile_key("M15", "RBR", "H1", "NESTED", True, 1, 0.375)
        edge = self.engine.profile_key("M15", "RBR", "H1", "NESTED", True, 1, 0.125)
        self.engine.load_stats({"version": 1, "groups": {
            edge: {"samples": 50, "win_rate": 0.60, "mean_net_r": 0.12, "standard_error": 0.07, "mean_net_r_standard_error": 0.02},
            outer: {"samples": 50, "win_rate": 0.65, "mean_net_r": 0.30, "standard_error": 0.07, "mean_net_r_standard_error": 0.03},
        }})
        result = self.evaluate()
        self.assertEqual(result["status"], "ENTRY_PROPOSAL")
        self.assertEqual(result["structure"]["penetration_bin"], "OUTER")
        self.assertAlmostEqual(result["order_plan"]["entry"], 99.625)

    def test_model_without_mean_net_r_uncertainty_is_rejected(self):
        key = self.engine.profile_key("M15", "RBR", "H1", "NESTED", True, 1, 0.125)
        with self.assertRaises(ValueError):
            self.engine.load_stats({"version": 1, "groups": {key: {
                "samples": 50, "win_rate": 0.7, "mean_net_r": 0.2, "standard_error": 0.05}}})

    def test_missing_micro_or_mismatched_reaction_fails_closed(self):
        self.assertEqual(self.evaluate(micro=None)["status"], "WAIT")
        self.assertEqual(self.evaluate(reaction={**self.reaction, "base_id": "other"})["status"], "WAIT")

    def test_future_parent_or_opposed_parent_fails_closed(self):
        self.assertEqual(self.evaluate(parent={**self.parent, "confirmation_time": 300})["status"], "WAIT")
        self.assertEqual(self.evaluate(parent={**self.parent, "exit_direction": -1})["status"], "WAIT")

    def test_exit_proposal_when_held_wave_loses_economic_edge(self):
        result = self.evaluate(active_position={"direction": "SELL"},
                               current_trade={"hold_net_expected_value_r": -0.1,
                                              "wave_structure_valid": True})
        self.assertEqual(result["status"], "EXIT_PROPOSAL")
        self.assertTrue(result["close_current_first"])
        self.assertFalse(result["execution_enabled"])

    def test_reverse_requires_lost_current_edge_and_positive_net_opposite_economics(self):
        result = self.evaluate(active_position={"direction": "SELL"},
                               current_trade={"hold_net_expected_value_r": -0.1,
                                              "wave_structure_valid": False},
                               opposite_setup={"reversal_confirmed": True,
                                               "net_expected_value_r": 0.2,
                                               "net_reward_risk": 1.4})
        self.assertEqual(result["status"], "REVERSE_PROPOSAL")
        self.assertTrue(result["close_current_first"])
        self.assertGreater(result["net_expected_value_r"], 0)

    def test_never_reverse_when_opposite_economics_fail(self):
        result = self.evaluate(active_position={"direction": "SELL"},
                               current_trade={"hold_net_expected_value_r": -0.1,
                                              "wave_structure_valid": False},
                               opposite_setup={"reversal_confirmed": True,
                                               "net_expected_value_r": -0.2,
                                               "net_reward_risk": 1.4})
        self.assertEqual(result["status"], "EXIT_PROPOSAL")

    def test_learning_rejects_unpriced_descriptive_excursions(self):
        report = self.engine.learn([{"timeframe": "M15", "base_type": "RBR",
            "parent_timeframe": "H1", "parent_relation": "NESTED", "parent_aligned": True,
            "reaction_number": 1, "penetration_fraction": 0.2, "label_end_time": 900,
            "label_horizon_bars": 10, "first_transition": "continuation_barrier", "net_R": 2.0}], as_of=1000)
        self.assertEqual(report["eligible_labels"], 0)


if __name__ == "__main__":
    unittest.main()
