import os
import json
import unittest
from unittest.mock import patch

from scripts.run_v1_2_demo_learning_loop import run_demo_learning_loop


class TestDemoLearningAuditTrail(unittest.TestCase):

    def setUp(self):
        self.history_file = "runtime_logs/learning_history.json"
        self.report_file = "reports/v1_2_demo_learning_loop_results.json"

    def test_demo_learning_loop_creates_audit_trail(self):
        # Run learning loop
        run_demo_learning_loop()

        self.assertTrue(os.path.exists(self.history_file))
        self.assertTrue(os.path.exists(self.report_file))

        with open(self.history_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        self.assertIsInstance(records, list)
        self.assertGreaterEqual(len(records), 1)

        latest = records[-1]
        self.assertEqual(latest["type"], "DEMO_LEARNING_RUN")
        self.assertTrue(latest["update_id"].startswith("learning-run-"))
        self.assertEqual(latest["total_signals"], 5000)
        self.assertEqual(latest["executed_demo_trades"], 4375)
        self.assertEqual(latest["risk_gate_rejections"], 625)
        self.assertEqual(latest["wins"], 2968)
        self.assertEqual(latest["losses"], 1407)
        self.assertEqual(latest["overall_win_rate_pct"], 67.84)
        self.assertTrue(latest["learning_completed"])
        self.assertIn("PAT_LIQUIDITY_SWEEP_REVERSAL", latest["patterns_updated"])

    def test_demo_learning_loop_appends_to_existing_history(self):
        os.makedirs("runtime_logs", exist_ok=True)
        initial_entry = {
            "update_id": "learning-run-initial",
            "type": "DEMO_LEARNING_RUN",
            "timestamp": "2026-08-20T00:00:00Z",
            "run_id": "RUN-00000000",
            "total_signals": 100,
            "executed_demo_trades": 88,
            "risk_gate_rejections": 12,
            "wins": 60,
            "losses": 28,
            "overall_win_rate_pct": 68.18,
            "average_rr": 2.15,
            "profit_factor": 3.5,
            "max_drawdown_pct": 2.1,
            "patterns_updated": ["PAT_MSS_BREAKOUT"],
            "learning_completed": True
        }

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump([initial_entry], f, indent=2)

        run_demo_learning_loop()

        with open(self.history_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        self.assertGreaterEqual(len(records), 2)
        self.assertEqual(records[0]["update_id"], "learning-run-initial")
        self.assertTrue(records[-1]["update_id"].startswith("learning-run-"))


if __name__ == "__main__":
    unittest.main()
