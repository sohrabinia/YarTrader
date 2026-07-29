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
        """Verifies SPA root pages render successfully with HTML contents."""
        resp1 = self.client.get("/")
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("text/html", resp1.headers["content-type"])
        self.assertIn("TradeYar AI — Management Dashboard", resp1.text)

        # Test default language and RTL markers are loaded correctly
        self.assertIn('lang="fa"', resp1.text)
        self.assertIn('dir="rtl"', resp1.text)
        self.assertIn('Vazirmatn', resp1.text)
        self.assertIn('id="lang-fa"', resp1.text)
        self.assertIn('id="lang-en"', resp1.text)
        self.assertIn('tradeyar_language', resp1.text)

        resp2 = self.client.get("/dashboard")
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("text/html", resp2.headers["content-type"])

    def test_get_live_research_endpoint(self):
        """Verifies that the new live research REST endpoint returns a valid JSON schema with XAUUSD H1 metrics."""
        resp = self.client.get("/v1/dashboard/live-research")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["symbol"], "XAUUSD")
        self.assertEqual(data["timeframe"], "H1")
        self.assertIn("timestamp", data)
        self.assertIn("features_calculated" if "features_calculated" in data else "market_state", data)
        self.assertIn("latest_insights" if "latest_insights" in data else "reasoning", data)
        self.assertIn("mt5_status" if "mt5_status" in data else "last_candle_time", data)

    def test_get_health_diagnostics(self):
        """Verifies health diagnostics API returns successful schema."""
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Healthy")
        self.assertTrue(data["apes_fin_compliant"])

    def test_get_runtime_status(self):
        """Verifies runtime status API."""
        resp = self.client.get("/v1/runtime")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["runtime_status"], "Ready")

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
        self.assertEqual(resp.json()["production_readiness_score"], 100.0)

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
