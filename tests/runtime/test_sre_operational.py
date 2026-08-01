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

        security_log_path = os.path.join("logs", "security", "security.log")
        self.assertTrue(os.path.exists(security_log_path), "security.log must be generated")

        with open(security_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertTrue(len(lines) > 0)
        last_line = lines[-1].strip()
        log_data = json.loads(last_line)

        self.assertEqual(log_data["level"], "INFO")
        self.assertEqual(log_data["service"], "TradeYar-AI")
        self.assertEqual(log_data["event"], "Unauthorized endpoint access attempt detected")
        self.assertEqual(log_data["src_ip"], "192.168.1.100")
        self.assertEqual(log_data["port"], 443)

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
        self.assertEqual(data["service"], "TradeYar-AI")
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
