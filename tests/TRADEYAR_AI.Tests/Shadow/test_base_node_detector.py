import unittest
from datetime import datetime, timedelta
from src.ShadowTrading.Engine.BaseNodeDetector import (
    BaseStructure,
    NodeStructure,
    NodePathTracker,
    BaseNodeDetector
)

class TestBaseNodeDetectorAdditions(unittest.TestCase):
    """
    Verifies that the advanced Tick, Base state transitions, and Node path tracking work perfectly.
    """

    def setUp(self) -> None:
        self.detector = BaseNodeDetector(compression_threshold=0.5)
        self.base_time = datetime(2026, 1, 1, 12, 0, 0)
        self.ticks = [
            {"price": 100.0, "volume": 10.0, "direction": "BUY", "timestamp": self.base_time},
            {"price": 100.1, "volume": 5.0, "direction": "BUY", "timestamp": self.base_time + timedelta(seconds=1)},
            {"price": 100.2, "volume": 8.0, "direction": "BUY", "timestamp": self.base_time + timedelta(seconds=2)},
            {"price": 100.1, "volume": 15.0, "direction": "SELL", "timestamp": self.base_time + timedelta(seconds=3)},
            {"price": 100.0, "volume": 20.0, "direction": "SELL", "timestamp": self.base_time + timedelta(seconds=4)},
            {"price": 100.1, "volume": 5.0, "direction": "BUY", "timestamp": self.base_time + timedelta(seconds=5)},
            {"price": 100.2, "volume": 12.0, "direction": "BUY", "timestamp": self.base_time + timedelta(seconds=6)},
            {"price": 100.1, "volume": 6.0, "direction": "SELL", "timestamp": self.base_time + timedelta(seconds=7)},
            {"price": 100.0, "volume": 10.0, "direction": "SELL", "timestamp": self.base_time + timedelta(seconds=8)},
            {"price": 100.1, "volume": 8.0, "direction": "BUY", "timestamp": self.base_time + timedelta(seconds=9)},
        ]

    def test_tick_velocity_and_volume_pressure(self) -> None:
        velocity = self.detector.calculate_tick_velocity(self.ticks)
        self.assertAlmostEqual(velocity, 0.1 / 9.0)  # price difference 0.1 / 9 seconds

        pressure = self.detector.calculate_volume_pressure(self.ticks)
        self.assertAlmostEqual(pressure, 48.0 / 99.0)

    def test_base_structure_transitions_and_serialization(self) -> None:
        base = self.detector.detect_base("XAUUSD", self.ticks)
        self.assertIsNotNone(base)
        self.assertEqual(base.state, "Compression")
        self.assertEqual(base.volume_behavior, "NEUTRAL")  # 0.4 <= pressure <= 0.6

        # Transition state strictly in order
        base.transition_state("Break")
        self.assertEqual(base.state, "Break")

        # Dict serialization / deserialization
        data = base.to_dict()
        self.assertEqual(data["state"], "Break")
        self.assertEqual(data["volume_behavior"], "NEUTRAL")
        self.assertIn("fingerprint", data)

        restored = BaseStructure.from_dict(data)
        self.assertEqual(restored.state, "Break")
        self.assertEqual(restored.volume_behavior, "NEUTRAL")
        self.assertEqual(restored.fingerprint, base.fingerprint)

    def test_duplicate_base_detection_fingerprint(self) -> None:
        base1 = self.detector.detect_base("XAUUSD", self.ticks)
        base2 = self.detector.detect_base("XAUUSD", self.ticks)

        # Verify that two bases detected with the exact same structure generate the exact same fingerprint
        self.assertEqual(base1.fingerprint, base2.fingerprint)

    def test_state_transition_integrity(self) -> None:
        base = BaseStructure(symbol="XAUUSD", high=100.5, low=100.0, duration=10, tick_count=10)
        self.assertEqual(base.state, "Creation")

        # Creation -> Formation is valid
        base.transition_state("Formation")
        self.assertEqual(base.state, "Formation")

        # Creation -> Outcome directly is invalid (violates state machine order)
        with self.assertRaises(ValueError):
            base.transition_state("Outcome")

    def test_serialization_stability_lossless(self) -> None:
        base = self.detector.detect_base("XAUUSD", self.ticks)
        base.add_reaction_outcome("react-1", "Breakout", "WIN", "Clean price acceleration")

        serialized = base.to_dict()
        restored = BaseStructure.from_dict(serialized)

        self.assertEqual(restored.base_id, base.base_id)
        self.assertEqual(restored.symbol, base.symbol)
        self.assertEqual(restored.high, base.high)
        self.assertEqual(restored.low, base.low)
        self.assertEqual(restored.state, base.state)
        self.assertEqual(restored.fingerprint, base.fingerprint)
        self.assertEqual(len(restored.reactions), 1)
        self.assertEqual(restored.reactions[0]["outcome_result"], "WIN")

    def test_node_path_tracker(self) -> None:
        tracker = NodePathTracker()
        base = self.detector.detect_base("XAUUSD", self.ticks)

        path = tracker.start_path_tracking(base)
        self.assertEqual(path["status"], "TRACKING")
        self.assertEqual(path["base_id"], base.base_id)

        node = NodeStructure(price_level=100.5, creation_context="Rebound", movement_phase="Reversal", reaction_strength=0.8)
        updated_path = tracker.add_node_to_path(path["path_id"], node, "Breakout_Reaction")
        self.assertIsNotNone(updated_path)
        self.assertEqual(len(updated_path["nodes"]), 1)
        self.assertEqual(updated_path["nodes"][0]["price_level"], 100.5)

        final_path = tracker.finalize_path(path["path_id"], "WIN")
        self.assertIsNotNone(final_path)
        self.assertEqual(final_path["status"], "COMPLETED")
        self.assertEqual(final_path["outcome"], "WIN")
