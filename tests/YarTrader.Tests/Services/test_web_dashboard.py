import unittest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.Application.Services.web_dashboard import app, val_state, global_auth_service

class TestWebDashboardFastAPI(unittest.TestCase):
    """
    Production Acceptance & Release Quality Assurance Suite.
    Thoroughly validates all endpoints, parameters and SPA pages.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        admin = global_auth_service.repo.get_user_by_email("admin-disabled@yartrader.app")
        cls.admin_headers = {"Authorization": f"Bearer {global_auth_service.create_session(admin)}"}
        admin = global_auth_service.repo.get_user_by_email("admin-disabled@yartrader.app")
        cls.admin_headers = {"Authorization": f"Bearer {global_auth_service.create_session(admin)}"}

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

    def test_version_endpoints_consistency_and_env_precedence(self):
        """Verifies version resolution endpoints (/api/version, /api/system/version, /v1/version) and env overrides."""
        resp_v1 = self.client.get("/api/version")
        self.assertEqual(resp_v1.status_code, 200)
        data_v1 = resp_v1.json()

        resp_v2 = self.client.get("/api/system/version")
        self.assertEqual(resp_v2.status_code, 200)
        self.assertEqual(resp_v2.json()["commit"], data_v1["commit"])

        resp_v3 = self.client.get("/v1/version")
        self.assertEqual(resp_v3.status_code, 200)
        self.assertEqual(resp_v3.json()["commit"], data_v1["commit"])

        # Test environment variable override
        import os
        from src.Infrastructure.version import get_application_version_info
        try:
            os.environ["GIT_COMMIT"] = "override_sha_12345"
            info = get_application_version_info()
            self.assertEqual(info["commit"], "override_sha_12345")
        finally:
            os.environ.pop("GIT_COMMIT", None)

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
        """Verifies authenticated runtime control mutations."""
        headers = {"Authorization": "Bearer fixture-admin-token"}
        with patch.object(global_auth_service, "validate_session", return_value={"role": "ADMIN", "email": "admin@yartrader.app"}):
            for cmd in ["start", "stop", "pause", "resume"]:
                resp = self.client.post("/api/control", json={"command": cmd}, headers=headers)
                self.assertEqual(resp.status_code, 503)
                self.assertIn("no state mutation was performed", resp.json()["detail"])
            resp_err = self.client.post("/api/control", json={"command": "invalid_cmd"}, headers=headers)
            self.assertEqual(resp_err.status_code, 400)

    def test_list_symbol_administration(self):
        """Verifies symbol administration lookup lists."""
        resp = self.client.get("/api/symbols")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("EURUSD", data["administered_symbols"])

    def test_transition_operating_mode(self):
        """Verifies authenticated authoritative operating-mode transitions."""
        headers = {"Authorization": "Bearer fixture-admin-token"}
        with patch.object(global_auth_service, "validate_session", return_value={"role": "ADMIN", "email": "admin@yartrader.app"}):
            for mode in ["Research", "Backtest", "Demo", "Signal", "Prop"]:
                resp = self.client.post("/api/mode", json={"mode": mode}, headers=headers)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["transitioned_to_mode"], mode)
            resp_err = self.client.post("/api/mode", json={"mode": "LiveActiveTrading"}, headers=headers)
            self.assertEqual(resp_err.status_code, 400)

    def test_trigger_backtesting_job(self):
        """Verifies offline backtest execution endpoint."""
        resp = self.client.post("/api/backtest/run", json={"symbol": "EURUSD"}, headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("job_id", resp.json())

    def test_trigger_emergency_stop(self):
        """Verifies authenticated emergency stop reaches authoritative HALTED state."""
        headers = {"Authorization": "Bearer fixture-admin-token"}
        with patch.object(global_auth_service, "validate_session", return_value={"role": "ADMIN", "email": "admin@yartrader.app"}):
            resp = self.client.post("/api/risk/emergency_stop", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["emergency_stop_triggered"])
        self.assertEqual(resp.json()["status"], "HALTED")
        self.assertTrue(resp.json()["runtime_state"]["system_halted"])

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
        resp_run = self.client.post("/api/validation/run", headers=self.admin_headers)
        self.assertEqual(resp_run.status_code, 200)
        self.assertIn(resp_run.json()["status"], ["Accepted", "Already Running"])

        # 2. Get status
        resp_status = self.client.get("/api/validation/status", headers=self.admin_headers)
        self.assertEqual(resp_status.status_code, 200)
        status_data = resp_status.json()
        self.assertIn("is_running", status_data)

        # 3. Get history
        resp_hist = self.client.get("/api/validation/history", headers=self.admin_headers)
        self.assertEqual(resp_hist.status_code, 200)
        self.assertIsInstance(resp_hist.json(), list)

        # 4. Download report
        resp_dl = self.client.get("/api/validation/reports/download?type=html", headers=self.admin_headers)
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn("text/html", resp_dl.headers["content-type"])

    @unittest.skip("Legacy financial statement endpoints are not part of the canonical v0.2 runtime API.")
    def test_user_and_admin_statements(self):
        """Legacy statement API contract retained only as historical coverage."""
        pass

    def test_08_mtf_research_api_timeframe_isolation(self):
        """Verifies that requesting a non-H1 timeframe (e.g. M5) never leaks H1 memory data."""
        # Clear existing disk snapshots temporarily for test isolation
        snapshot_dir = "runtime_logs/research_snapshots"
        saved_files = {}
        if os.path.exists(snapshot_dir):
            for f in os.listdir(snapshot_dir):
                if f.endswith(".json"):
                    fpath = os.path.join(snapshot_dir, f)
                    with open(fpath, "r", encoding="utf-8") as file:
                        saved_files[f] = file.read()
                    os.remove(fpath)

        try:
            # 1. Request M5 when no M5 snapshot or M5 memory exists -> must return M5 degraded
            resp_m5 = self.client.get("/api/research/current?symbol=XAUUSD&timeframe=M5")
            self.assertEqual(resp_m5.status_code, 200)
            data_m5 = resp_m5.json()
            self.assertEqual(data_m5["symbol"], "XAUUSD")
            self.assertEqual(data_m5["timeframe"], "M5")
            self.assertEqual(data_m5.get("status"), "degraded")

            # 2. Request H1 -> must return H1
            resp_h1 = self.client.get("/api/research/current?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(resp_h1.status_code, 200)
            data_h1 = resp_h1.json()
            self.assertEqual(data_h1["symbol"], "XAUUSD")
            self.assertEqual(data_h1["timeframe"], "H1")
        finally:
            # Restore snapshots
            if saved_files:
                os.makedirs(snapshot_dir, exist_ok=True)
                for f, content in saved_files.items():
                    with open(os.path.join(snapshot_dir, f), "w", encoding="utf-8") as file:
                        file.write(content)
    def test_sensitive_endpoints_require_runtime_authentication(self):
        for path, payload in [
            ("/api/control", {"command": "stop"}),
            ("/api/mode", {"mode": "Research"}),
            ("/api/risk/emergency_stop", None),
        ]:
            resp = self.client.post(path, json=payload) if payload is not None else self.client.post(path)
            self.assertEqual(resp.status_code, 401, path)

    def test_sensitive_endpoints_reject_unauthorized_runtime_identity(self):
        headers = {"Authorization": "Bearer fixture-user-token"}
        with patch.object(global_auth_service, "validate_session", return_value={"role": "USER", "email": "user@yartrader.app"}):
            for path, payload in [
                ("/api/control", {"command": "stop"}),
                ("/api/mode", {"mode": "Research"}),
                ("/api/risk/emergency_stop", None),
            ]:
                resp = self.client.post(path, json=payload, headers=headers) if payload is not None else self.client.post(path, headers=headers)
                self.assertEqual(resp.status_code, 403, path)
