import unittest

from src.Decision.Intelligence.hierarchical_base_behavior_engine import HierarchicalBaseBehaviorEngine


def event(event_id, tf, typ, direction, start, end, confirm, low, high, atr=1.0):
    return {
        "event_id": event_id, "timeframe": tf, "base_type": typ,
        "exit_direction": direction, "base_start_time": start, "base_end_time": end,
        "confirmation_time": confirm, "base_low": low, "base_high": high,
        "base_mid": (low + high) / 2, "base_atr": atr,
    }


class HierarchicalBaseBehaviorEngineTests(unittest.TestCase):
    def test_waits_without_parent_child_alignment(self):
        engine = HierarchicalBaseBehaviorEngine(min_samples=2)
        child = event("m15", "M15", "RBR", 1, 100, 200, 250, 99, 100)
        result = engine.analyze({"M15": [child]}, {"bid": 101, "ask": 101.1}, 300)
        self.assertEqual(result["status"], "WAIT")
        self.assertIn("parent", result["reason"])

    def test_learns_only_labels_with_proven_end_before_cutoff(self):
        engine = HierarchicalBaseBehaviorEngine(min_samples=2)
        child = event("m15", "M15", "RBR", 1, 100, 200, 250, 99, 100)
        labels = [
            {"event_id": "m15", "label_horizon_bars": 10, "label_end_time": 500, "first_transition": "continuation_barrier", "parent_timeframe": "H1", "parent_aligned": True, "net_R": 0.8},
            {"event_id": "m15", "label_horizon_bars": 10, "label_end_time": 600, "first_transition": "reversal_barrier", "parent_timeframe": "H1", "parent_aligned": True, "net_R": -1.0},
            {"event_id": "m15", "label_horizon_bars": 10, "label_end_time": 1500, "first_transition": "continuation_barrier", "parent_timeframe": "H1", "parent_aligned": True, "net_R": 0.5},
        ]
        stats = engine.learn({"M15": [child]}, labels, as_of=1000)
        self.assertEqual(stats["eligible_labels"], 2)
        self.assertEqual(stats["groups"], 1)
        self.assertAlmostEqual(engine.export_stats()["groups"]["M15|RBR|H1|NESTED|ALIGNED"]["mean_net_r"], -0.1)

    def test_exported_net_r_model_can_be_loaded(self):
        source = HierarchicalBaseBehaviorEngine(min_samples=1)
        source._stats = {"M15|RBR|H1|NESTED|ALIGNED": {
            "samples": 45, "win_rate": 0.6, "mean_net_r": 0.12,
            "standard_error": 0.07, "net_r_samples": 45,
        }}
        restored = HierarchicalBaseBehaviorEngine()
        restored.load_stats(source.export_stats())
        self.assertEqual(restored.export_stats()["groups"]["M15|RBR|H1|NESTED|ALIGNED"]["samples"], 45)

    def test_proposes_only_with_aligned_parent_and_enough_prior_samples(self):
        engine = HierarchicalBaseBehaviorEngine(min_samples=2, min_win_rate=0.5)
        parent = event("h1", "H1", "RBR", 1, 0, 1000, 100, 98, 105, 2)
        child = event("m15", "M15", "RBR", 1, 100, 200, 250, 99, 100, 1)
        destination = event("dest", "M15", "DBD", -1, 40, 80, 90, 106, 107, 1)
        micro = event("micro", "M1", "RBR", 1, 700, 800, 900, 101.4, 101.6, 0.2)
        labels = [
            {"event_id": "m15", "label_horizon_bars": 10, "label_end_time": 500, "first_transition": "continuation_barrier", "parent_timeframe": "H1", "parent_aligned": True, "net_R": 0.8},
            {"event_id": "m15", "label_horizon_bars": 10, "label_end_time": 600, "first_transition": "continuation_barrier", "parent_timeframe": "H1", "parent_aligned": True, "net_R": 0.6},
        ]
        engine.learn({"H1": [parent], "M15": [child, destination]}, labels, as_of=1000)
        result = engine.analyze({"H1": [parent], "M15": [child, destination], "M1": [micro]},
                                {"bid": 101, "ask": 101.1}, 1000)
        self.assertIn(result["status"], ("ORDER_PROPOSAL", "WAIT"))
        self.assertFalse(result.get("execution_enabled", True))
        self.assertEqual(result["structure"]["parent_child_alignment"], "ALIGNED")


if __name__ == "__main__":
    unittest.main()
