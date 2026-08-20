import os
import json
import unittest
from app.core.logging import log_event, log_audit, log_intelligence_decision

class TestLogging(unittest.TestCase):
    def test_json_logging_format(self):
        """Verifies that logged events are written in valid JSON format with correct keys."""
        log_event("INFO", "Test event format", custom_id=987)

        from src.Application.Deployment.storage import YarTraderStorageManager
        logs_root = YarTraderStorageManager.get_manager().get_log_dir()
        app_log_path = os.path.join(logs_root, "application", "application.log")
        self.assertTrue(os.path.exists(app_log_path))

        with open(app_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found_data = None
        for line in reversed(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if data.get("custom_id") == 987 or data.get("event") == "Test event format":
                    found_data = data
                    break
            except json.JSONDecodeError:
                continue

        self.assertIsNotNone(found_data, "Logged event 'Test event format' with custom_id=987 not found in application.log")
        self.assertEqual(found_data["level"], "INFO")
        self.assertTrue(found_data["service"] in ("TradeYar-AI", "YarTrader"))
        self.assertEqual(found_data["event"], "Test event format")
        self.assertEqual(found_data["custom_id"], 987)
        self.assertIn("time", found_data)

    def test_error_separation(self):
        """Checks that ERROR logs are written to error.log as well."""
        log_event("ERROR", "Test critical error separate")

        from src.Application.Deployment.storage import YarTraderStorageManager
        logs_root = YarTraderStorageManager.get_manager().get_log_dir()
        err_log_path = os.path.join(logs_root, "error", "error.log")
        self.assertTrue(os.path.exists(err_log_path))

        with open(err_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found_data = None
        for line in reversed(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if data.get("event") == "Test critical error separate":
                    found_data = data
                    break
            except json.JSONDecodeError:
                continue

        self.assertIsNotNone(found_data, "Logged error 'Test critical error separate' not found in error.log")
        self.assertEqual(found_data["level"], "ERROR")
        self.assertEqual(found_data["event"], "Test critical error separate")
