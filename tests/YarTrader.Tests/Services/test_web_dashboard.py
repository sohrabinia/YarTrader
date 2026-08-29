import unittest
import os
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, val_state

class TestWebDashboardFastAPI(unittest.TestCase):
    """
    Production Acceptance & Release Quality Assurance Suite.
    Thoroughly validates all endpoints, parameters and SPA pages.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_get_dashboard_spa(self):
        """Verifies SPA root pages render successfully with HTML contents across localized and static paths."""
        for path in [
            "/",
            "/dashboard",
            "/pricing",
            "/features",
            "/login",
            "/register",
            "/forgot-password",
            "/execution-intel",
            "/admin",
            "/fa",
            "/en",
            "/tr",
            "/ar",
            "/de",
            "/fa/admin",
            "/fa/login",
            "/fa/dashboard",
            "/fa/blog",
            "/fa/news",
            "/fa/guide",
            "/fa/faq",
            "/fa/about",
            "/fa/contact",
            "/en/admin",
            "/tr/admin",
            "/ar/admin",
            "/de/admin",
        ]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"Failed for path: {path}")
            self.assertIn("text/html", resp.headers["content-type"], f"Wrong content type for path: {path}")
            self.assertIn("YarTrader", resp.text, f"Missing YarTrader brand in path: {path}")

    def test_api_404_isolation(self):
        """Verifies unregistered API endpoints return 404 JSON detail rather than HTML SPA fallback."""
        resp = self.client.get("/api/nonexistent_endpoint_xyz")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("application/json", resp.headers["content-type"])
        self.assertEqual(resp.json(), {"detail": "Not Found"})

    def test_get_health_diagnostics(self):
        """Verifies health diagnostics API returns successful schema."""
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Healthy")
        self.assertTrue(data["apes_fin_compliant"])

    def test_get_live_research_degraded_fallback(self):
        """Verifies /v1/dashboard/live-research returns HTTP 200 degraded payload instead of 503 error."""
        resp = self.client.get("/v1/dashboard/live-research?symbol=XAUUSD&timeframe=H1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["symbol"], "XAUUSD")
        self.assertEqual(data["timeframe"], "H1")
        self.assertIn("bias", data)
        self.assertIn("confidence", data)
        self.assertIn("reasoning", data)
        self.assertIn("timestamp", data)

    def test_get_runtime_status(self):
        """Verifies runtime status API."""
        resp = self.client.get("/v1/runtime")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("runtime_status", data)
        self.assertEqual(data["service_status"], "SERVICE_READY")
        self.assertIn("production_ready", data)

    def test_get_dashboard_overview(self):
        """Verifies overview aggregated diagnostics API."""
        resp = self.client.get("/v1/dashboard/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["system_health"], "Healthy")

    def test_get_monitoring_alerts(self):
        """Verifies active diagnostic logs and alerts."""
        resp = self.client.get("/v1/monitoring")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["telemetry_state"], "ONLINE")

    def test_get_telemetry_metrics(self):
        """Verifies latency and resource telemetry metrics."""
        resp = self.client.get("/v1/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pipeline_latency_ms", data)

    def test_execute_runtime_control(self):
        """Verifies start, stop, pause, resume controllers."""
        for cmd in ["start", "stop", "pause", "resume"]:
            resp = self.client.post("/api/control", json={"command": cmd})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["status"], "Berry" if False else "Success")

        # invalid command
        resp_err = self.client.post("/api/control", json={"command": "invalid_cmd"})
        self.assertEqual(resp_err.status_code, 400)

    def test_list_symbol_administration(self):
        """Verifies symbol administration lookup lists."""
        resp = self.client.get("/api/symbols")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("EURUSD", data["administered_symbols"])

    def test_transition_operating_mode(self):
        """Verifies operating mode transition handlers."""
        for mode in ["Research", "Backtest", "Simulation", "Shadow"]:
            resp = self.client.post("/api/mode", json={"mode": mode})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["transitioned_to_mode"], mode)

        resp_err = self.client.post("/api/mode", json={"mode": "LiveActiveTrading"})
        self.assertEqual(resp_err.status_code, 400)

    def test_trigger_backtesting_job(self):
        """Verifies offline backtest execution endpoint."""
        resp = self.client.post("/api/backtest/run", json={"symbol": "EURUSD"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("job_id", resp.json())

    def test_trigger_emergency_stop(self):
        """Verifies immediate emergency protective stop halts."""
        resp = self.client.post("/api/risk/emergency_stop")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["emergency_stop_triggered"])

    def test_get_scorecard(self):
        """Verifies production readiness scorecards."""
        resp = self.client.get("/api/production-readiness")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("production_readiness_score", data)
        self.assertIn("status", data)
        self.assertIn("blocking_reasons", data)

    def test_async_validation_run_lifecycle(self):
        """Verifies trigger, progress retrieval, history and downloading."""
        # 1. Trigger
        resp_run = self.client.post("/api/validation/run")
        self.assertEqual(resp_run.status_code, 200)
        self.assertIn(resp_run.json()["status"], ["Accepted", "Already Running"])

        # 2. Get status
        resp_status = self.client.get("/api/validation/status")
        self.assertEqual(resp_status.status_code, 200)
        status_data = resp_status.json()
        self.assertIn("is_running", status_data)

        # 3. Get history
        resp_hist = self.client.get("/api/validation/history")
        self.assertEqual(resp_hist.status_code, 200)
        self.assertIsInstance(resp_hist.json(), list)

        # 4. Download report
        resp_dl = self.client.get("/api/validation/reports/download?type=html")
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn("text/html", resp_dl.headers["content-type"])
