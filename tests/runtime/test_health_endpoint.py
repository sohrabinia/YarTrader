import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, research_tracker

class TestHealthEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.old_status = research_tracker.copy()

    def tearDown(self) -> None:
        research_tracker.clear()
        research_tracker.update(self.old_status)

    def test_production_health_endpoint(self):
        """Verifies calling /health route returns compliant JSON structure."""
        research_tracker["mt5_status"] = "CONNECTED"
        research_tracker["worker_status"] = "RUNNING"

        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "Healthy")
        self.assertEqual(data["service"], "TradeYar-AI")
        self.assertEqual(data["api"], "Online")
        self.assertEqual(data["mt5"], "Connected")
        self.assertEqual(data["worker"], "Running")
        self.assertEqual(data["intelligence"], "Ready")
        self.assertIn("timestamp", data)

    def test_devops_status_contract(self):
        """Verifies the DevOps integration status contract is intact."""
        response = self.client.get("/api/devops/status")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["service_status"], "RUNNING")
        self.assertEqual(data["runtime_health"], "Healthy")
        self.assertIn("mt5_status", data)
        self.assertIn("worker_status", data)
        self.assertIn("error_summary", data)

    def test_devops_metrics_contract(self):
        """Verifies the DevOps integration metrics contract is intact."""
        response = self.client.get("/api/devops/metrics")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("pipeline_latency_ms", data)
        self.assertIn("api_response_ms", data)
        self.assertIn("memory_used_mb", data)
        self.assertIn("thread_count", data)
