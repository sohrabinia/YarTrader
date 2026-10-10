import unittest
import tempfile
from pathlib import Path

from src.Decision.Intelligence.multitimeframe_base_behavior_monitor import (
    MultitimeframeBaseBehaviorMonitor,
)
from src.Decision.Intelligence.engine import DecisionEngine


class FakeSignalEngine:
    def generate_unified_signal(self, **kwargs):
        return "signal-stub"


def ev(eid, tf, direction, start, end, confirm, low, high):
    return {"event_id": eid, "timeframe": tf, "exit_direction": direction,
            "base_start_time": start, "base_end_time": end,
            "confirmation_time": confirm, "base_low": low, "base_high": high,
            "base_atr": 1.0, "base_mid": (low + high) / 2}


class MultitimeframeBaseBehaviorMonitorTests(unittest.TestCase):
    def test_links_only_causally_confirmed_nested_parent(self):
        parent = ev("h1", "H1", 1, 100, 400, 430, 90, 110)
        child = ev("m15", "M15", 1, 200, 400, 450, 98, 102)
        links = {"H1": [parent], "M15": [child]}
        got = MultitimeframeBaseBehaviorMonitor._parent_for(child, links)
        self.assertEqual(got["event_id"], "h1")

    def test_does_not_link_parent_confirmed_after_child(self):
        parent = ev("h1", "H1", 1, 100, 500, 700, 90, 110)
        child = ev("m15", "M15", 1, 200, 400, 450, 98, 102)
        self.assertIsNone(MultitimeframeBaseBehaviorMonitor._parent_for(child, {"H1": [parent], "M15": [child]}))

    def test_reaction_ledger_counts_separated_visits_and_measures_depth(self):
        event = ev("m15", "M15", 1, 100, 200, 300, 99, 101)
        bars = [
            {"time": 360, "open": 102, "high": 103, "low": 102, "close": 102},
            {"time": 420, "open": 100, "high": 101, "low": 99.5, "close": 100},
            {"time": 480, "open": 102, "high": 103, "low": 101.5, "close": 102},
            {"time": 540, "open": 100, "high": 100.5, "low": 99.0, "close": 99.5},
            {"time": 600, "open": 102, "high": 103, "low": 102, "close": 102},
        ]
        visits = MultitimeframeBaseBehaviorMonitor._reaction_rows(event, bars, "M1", 660)
        self.assertEqual(len(visits), 2)
        self.assertGreater(visits[0]["penetration_fraction"], 0.5)
        self.assertGreaterEqual(visits[0]["mfe_atr"], 0.0)
        self.assertGreaterEqual(visits[1]["mae_atr"], 0.0)

    def test_professional_signal_call_updates_base_monitor_snapshot(self):
        engine = DecisionEngine(signal_engine=FakeSignalEngine())
        self.assertEqual(engine.generate_professional_signal("XAUUSD", {}), "signal-stub")
        self.assertEqual(engine.last_base_behavior_report["status"], "BASE_BEHAVIOR_OBSERVATION_ONLY")

    def test_decision_engine_exposes_base_monitor(self):
        engine = DecisionEngine()
        result = engine.analyze_multitimeframe_base_behavior({}, now=2_000_000_000)
        self.assertEqual(result["status"], "BASE_BEHAVIOR_OBSERVATION_ONLY")
        self.assertFalse(result["execution_enabled"])

    def test_analysis_is_explicitly_observation_only(self):
        monitor = MultitimeframeBaseBehaviorMonitor()
        result = monitor.analyze({}, now=2_000_000_000)
        self.assertEqual(result["status"], "BASE_BEHAVIOR_OBSERVATION_ONLY")
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["decision"]["status"], "WAIT")


    def test_reaction_memory_persists_across_monitor_restarts_without_duplicates(self):
        reaction = {"base_id": "H1:100:RBR", "timeframe": "M5", "visit": 1,
                    "start_time": 600, "first_touch_price": 100.0,
                    "penetration_fraction": 0.4, "mfe_atr": 0.7,
                    "mae_atr": 0.2, "bars": 2, "end_time": 900,
                    "duration_seconds": 600, "complete": True}
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "base_state.json"
            first = MultitimeframeBaseBehaviorMonitor(state_path=state_path)
            self.assertEqual(first._merge_reaction_history("H1:100:RBR", "M5", [reaction], base_timeframe="H1"), [dict(reaction, reaction_number=1)])
            second = MultitimeframeBaseBehaviorMonitor(state_path=state_path)
            merged = second._merge_reaction_history("H1:100:RBR", "M5", [reaction], base_timeframe="H1")
            self.assertEqual(len(merged), 1)
            self.assertEqual(merged[0]["start_time"], 600)
            self.assertEqual(second._reaction_state["bases"]["H1:100:RBR"]["timeframe"], "H1")

    def test_persisted_reaction_episode_metrics_are_updated_in_place(self):
        with tempfile.TemporaryDirectory() as td:
            monitor = MultitimeframeBaseBehaviorMonitor(state_path=Path(td) / "state.json")
            initial = {"timeframe": "M1", "start_time": 120, "penetration_fraction": 0.2, "mfe_atr": 0.1}
            updated = dict(initial, penetration_fraction=0.8, mfe_atr=1.3)
            monitor._merge_reaction_history("base", "H1", [initial])
            history = monitor._merge_reaction_history("base", "H1", [updated])
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["penetration_fraction"], 0.8)
            self.assertEqual(history[0]["mfe_atr"], 1.3)


if __name__ == "__main__":
    unittest.main()
