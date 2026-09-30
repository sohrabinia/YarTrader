import json
import tempfile
import unittest
from pathlib import Path

from src.Research.Brain.learning_bridge import BrainLearningBridge


class TestBrainLearningBridge(unittest.TestCase):
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
