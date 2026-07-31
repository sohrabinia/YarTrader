import os
import json
import unittest
from app.core.logging import log_event, log_audit, log_intelligence_decision

class TestLogging(unittest.TestCase):
    def test_json_logging_format(self):
        """Verifies that logged events are written in valid JSON format with correct keys."""
        log_event("INFO", "Test event format", custom_id=987)

        app_log_path = os.path.join("logs", "application", "application.log")
        self.assertTrue(os.path.exists(app_log_path))

        with open(app_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        last_line = lines[-1].strip()
        data = json.loads(last_line)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["service"], "TradeYar-AI")
        self.assertEqual(data["event"], "Test event format")
        self.assertEqual(data["custom_id"], 987)
        self.assertIn("time", data)

    def test_error_separation(self):
        """Checks that ERROR logs are written to error.log as well."""
        log_event("ERROR", "Test critical error separate")

        err_log_path = os.path.join("logs", "error", "error.log")
        self.assertTrue(os.path.exists(err_log_path))

        with open(err_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        last_line = lines[-1].strip()
        data = json.loads(last_line)
        self.assertEqual(data["level"], "ERROR")
        self.assertEqual(data["event"], "Test critical error separate")
