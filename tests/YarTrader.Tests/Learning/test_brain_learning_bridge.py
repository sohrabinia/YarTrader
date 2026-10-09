import json
import tempfile
import unittest
from pathlib import Path

from src.Research.Brain.learning_bridge import BrainLearningBridge


class TestBrainLearningBridge(unittest.TestCase):
    def test_invalid_geometry_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = BrainLearningBridge(storage_dir=tmp)
            bridge.record_signal(
                "SIG-INVALID", "EURUSD", "M15", "BUY",
                -1.26, -1.92, 0.19, 0.70,
            )
            pending_path = Path(tmp) / "pending_signals.json"
            pending = json.loads(pending_path.read_text()) if pending_path.exists() else {}
            self.assertNotIn("SIG-INVALID", pending)

    def test_signal_to_demo_outcome_reaches_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = BrainLearningBridge(storage_dir=tmp)
            bridge.record_signal(
                "SIG-BRIDGE-1", "XAUUSD", "M15", "BUY",
                2000.0, 1990.0, 2020.0, 0.72,
                {"source": "SIGNAL"},
            )
            pending = json.loads((Path(tmp) / "pending_signals.json").read_text())
            self.assertIn("SIG-BRIDGE-1", pending)

            result = bridge.record_demo_outcome(
                "SIG-BRIDGE-1", "XAUUSD", "M15", "BUY",
                2000.0, 2020.0, 20.0,
            )

            self.assertEqual(result["source"], "DEMO")
            self.assertEqual(result["outcome"], "SUCCESS")
            self.assertGreaterEqual(result["memory"]["total_experiences"], 1)
            self.assertNotIn("SIG-BRIDGE-1", json.loads((Path(tmp) / "pending_signals.json").read_text()))


if __name__ == "__main__":
    unittest.main()
