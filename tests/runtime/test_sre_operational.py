import os
import json
import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from app.core.logging import log_security

class TestSREOperational(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_security_logging_generation(self):
        """Verifies that security events write properly formatted JSON to security.log."""
        log_security("Unauthorized endpoint access attempt detected", src_ip="192.168.1.100", port=443)

        from src.Application.Deployment.storage import YarTraderStorageManager
        logs_dir = YarTraderStorageManager.get_manager().get_log_dir()
        security_log_path = os.path.join(logs_dir, "security", "security.log")
        self.assertTrue(os.path.exists(security_log_path), "security.log must be generated")

        found_data = None
        with open(security_log_path, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if data.get("event") == "Unauthorized endpoint access attempt detected":
                        found_data = data
                        break
                except json.JSONDecodeError:
                    continue

        self.assertIsNotNone(found_data, "Security log entry not found")
        self.assertEqual(found_data["level"], "INFO")
        self.assertTrue(found_data["service"] in ("TradeYar-AI", "YarTrader"))
        self.assertEqual(found_data["event"], "Unauthorized endpoint access attempt detected")
        self.assertEqual(found_data["src_ip"], "192.168.1.100")
        self.assertEqual(found_data["port"], 443)

    def test_health_endpoints_live_and_ready(self):
        """Checks SRE /health/live and /health/ready liveness and readiness response schemas."""
        resp_live = self.client.get("/health/live")
        self.assertEqual(resp_live.status_code, 200)
        self.assertEqual(resp_live.json(), {"status": "OK"})

        resp_ready = self.client.get("/health/ready")
        self.assertIn(resp_ready.status_code, [200, 503]) # Standard API response codes for SRE
        data = resp_ready.json()
        self.assertIn("status", data)

    def test_production_health_endpoint(self):
        """Verifies details and worker status fields of the production /health endpoint."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["service"] == "TradeYar-AI" or data["service"] == "YarTrader")
        self.assertIn("api", data)
        self.assertIn("mt5", data)
        self.assertIn("worker", data)

    def test_devops_status_and_metrics(self):
        """Verifies response models of devops SRE dashboard endpoints."""
        resp_status = self.client.get("/api/devops/status")
        self.assertEqual(resp_status.status_code, 200)
        data_status = resp_status.json()
        self.assertEqual(data_status["service_status"], "RUNNING")
        self.assertIn("runtime_health", data_status)
        self.assertIn("error_summary", data_status)

        resp_metrics = self.client.get("/api/devops/metrics")
        self.assertEqual(resp_metrics.status_code, 200)
        data_metrics = resp_metrics.json()
        self.assertIn("pipeline_latency_ms", data_metrics)
        self.assertIn("api_response_ms", data_metrics)
        self.assertIn("memory_used_mb", data_metrics)

    def test_unidirectional_and_read_only_compliance(self):
        """Ensures that the API remains descriptive, analytical and strictly non-trading."""
        resp_overview = self.client.get("/v1/dashboard/overview")
        self.assertEqual(resp_overview.status_code, 200)
        data = resp_overview.json()
        self.assertEqual(data["active_operating_mode"], "Descriptive-Analytical Sandbox")
        self.assertTrue(data["apes_boundary_passed"])

    def test_cognitive_dashboard_endpoints(self):
        """Verifies that passive cognitive query and explainability endpoints are active."""
        resp_cognitive = self.client.get("/v1/dashboard/cognitive")
        self.assertEqual(resp_cognitive.status_code, 200)
        data = resp_cognitive.json()
        self.assertIn("cognitive", data)
        self.assertIn("Learning Progress", data["cognitive"])
        self.assertIn("Brain Weakness", data["cognitive"])

    def test_explainability_bilingual_resolutions(self):
        """Checks the response integrity of Persian/English explainability endpoints."""
        # Query Persian explainability decision
        resp_fa = self.client.get("/api/intelligence/explain/open_trade?lang=fa")
        self.assertEqual(resp_fa.status_code, 200)
        self.assertIn("explanation", resp_fa.json())

        # Query English explainability decision
        resp_en = self.client.get("/api/intelligence/explain/open_trade?lang=en")
        self.assertEqual(resp_en.status_code, 200)
        self.assertIn("explanation", resp_en.json())
