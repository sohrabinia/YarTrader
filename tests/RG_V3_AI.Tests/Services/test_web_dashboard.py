import json
import socket
import threading
import time
import unittest
import urllib.request
from typing import Dict, Any

from src.Application.Services.web_dashboard import ThreadingHTTPServer, WebDashboardRequestHandler
from src.Application.Dashboard.control_center import ControlCenterAggregator


class TestWebDashboardRESTAndSPA(unittest.TestCase):
    """
    Comprehensive test suite validating the Web Management Dashboard HTTP Server,
    SPA rendering, REST API routing, and system execution commands.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Dynamically find a free port to avoid conflicts
        cls.port = cls._get_free_port()
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), WebDashboardRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        # Give the server a small moment to start up
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)

    @classmethod
    def _get_free_port(cls) -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def _get_url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _send_get(self, path: str) -> tuple[int, str, Dict[str, Any]]:
        url = self._get_url(path)
        try:
            with urllib.request.urlopen(url) as response:
                code = response.getcode()
                body = response.read().decode("utf-8")
                headers = dict(response.info())
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {}
                return code, body, data
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_data = json.loads(err_body)
            except Exception:
                err_body = ""
                err_data = {}
            return e.code, err_body, err_data

    def _send_post(self, path: str, payload: Dict[str, Any]) -> tuple[int, str, Dict[str, Any]]:
        url = self._get_url(path)
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                code = response.getcode()
                body = response.read().decode("utf-8")
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {}
                return code, body, data
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_data = json.loads(err_body)
            except Exception:
                err_body = ""
                err_data = {}
            return e.code, err_body, err_data

    def test_serve_spa_ui(self) -> None:
        """Verifies GET / serves the SPA single page application with modern dark/light UI."""
        code, body, _ = self._send_get("/")
        self.assertEqual(code, 200)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("TradeYar AI Production Control Center", body)
        self.assertIn("toggleTheme()", body)

    def test_get_status_api(self) -> None:
        """Verifies GET /api/status endpoint returns expected system parameters."""
        code, _, data = self._send_get("/api/status")
        self.assertEqual(code, 200)
        self.assertIn("active_mode", data)
        self.assertIn("runtime_status", data)
        self.assertIn("emergency_stop_active", data)
        self.assertIn("active_agents", data)
        self.assertIn("metrics", data)
        self.assertIn("health_score", data["metrics"])

    def test_get_symbols_api(self) -> None:
        """Verifies GET /api/symbols lists current registered symbols."""
        code, _, data = self._send_get("/api/symbols")
        self.assertEqual(code, 200)
        self.assertIn("symbols", data)
        self.assertTrue(len(data["symbols"]) > 0)
        first_symbol = data["symbols"][0]
        self.assertIn("symbol", first_symbol)
        self.assertIn("broker_mapping", first_symbol)

    def test_get_logs_api(self) -> None:
        """Verifies GET /api/logs returns operational logs and modes audit trial."""
        code, _, data = self._send_get("/api/logs")
        self.assertEqual(code, 200)
        self.assertIn("logs", data)
        self.assertIn("audit_trail", data)

    def test_post_control_api(self) -> None:
        """Verifies POST /api/control actions starting, pausing, and stopping."""
        # Test Start
        code, _, data = self._send_post("/api/control", {"action": "START"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["runtime_status"], "RUNNING")

        # Test Pause
        code, _, data = self._send_post("/api/control", {"action": "PAUSE"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["runtime_status"], "PAUSED")

        # Test Resume
        code, _, data = self._send_post("/api/control", {"action": "RESUME"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["runtime_status"], "RUNNING")

        # Test Restart
        code, _, data = self._send_post("/api/control", {"action": "RESTART"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["runtime_status"], "RUNNING")

        # Test Stop
        code, _, data = self._send_post("/api/control", {"action": "STOP"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["runtime_status"], "STOPPED")

    def test_post_invalid_control_action(self) -> None:
        """Verifies POST /api/control with invalid action returns HTTP 400."""
        code, _, data = self._send_post("/api/control", {"action": "INVALID_ACTION_XYZ"})
        self.assertEqual(code, 400)
        self.assertEqual(data["status"], "ERROR")
        self.assertIn("Unsupported runtime action", data["error_message"])

    def test_post_invalid_json(self) -> None:
        """Verifies POST endpoints handle invalid or corrupt JSON payloads with HTTP 400."""
        url = self._get_url("/api/control")
        req = urllib.request.Request(
            url,
            data=b"{bad_json:",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                self.fail("Should have raised HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            data = json.loads(e.read().decode("utf-8"))
            self.assertEqual(data["status"], "ERROR")
            self.assertEqual(data["error_message"], "Invalid JSON payload.")

    def test_post_mode_api(self) -> None:
        """Verifies POST /api/mode correctly transitions operating mode with safety limits."""
        # Safe transition to Shadow
        code, _, data = self._send_post("/api/mode", {"mode": "Shadow"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["active_mode"], "Shadow")

        # Insecure/Forbidden transition to Live without confirmation
        code, _, data = self._send_post("/api/mode", {"mode": "Live"})
        self.assertEqual(code, 400)
        self.assertEqual(data["status"], "ERROR")

        # Secure transition to Live with confirmation (strictly blocked by configuration/APES guard)
        code, _, data = self._send_post("/api/mode", {"mode": "Live", "live_confirmation": True})
        self.assertEqual(code, 400)  # Standard configuration guards still block it, raising ValidationException
        self.assertEqual(data["status"], "ERROR")

    def test_post_symbols_api(self) -> None:
        """Verifies POST /api/symbols allows CRUD registry changes of active symbols."""
        payload = {
            "symbol": "BTCUSD",
            "broker_mapping": "BTCUSD_m",
            "asset_class": "Crypto",
            "timeframes": ["M30", "H4"]
        }
        code, _, data = self._send_post("/api/symbols", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("registered successfully", data["message"])

        # Missing symbol parameter
        code, _, data = self._send_post("/api/symbols", {"asset_class": "Crypto"})
        self.assertEqual(code, 400)
        self.assertEqual(data["status"], "ERROR")
        self.assertIn("Missing required parameter", data["error_message"])

    def test_post_backtest_run_api(self) -> None:
        """Verifies POST /api/backtest/run registers and starts a backtest job."""
        payload = {
            "symbol": "GBPUSD",
            "timeframe": "M15",
            "start_date": "2026-02-01",
            "end_date": "2026-05-01",
            "initial_capital": 50000.0
        }
        code, _, data = self._send_post("/api/backtest/run", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertIn("job_id", data)
        self.assertIn("metrics", data)

    def test_post_risk_emergency_stop_api(self) -> None:
        """Verifies POST /api/risk/emergency_stop halts all thread operations immediately."""
        code, _, data = self._send_post("/api/risk/emergency_stop", {})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "SHUTDOWN")
        self.assertIn("Emergency global stop triggered", data["message"])

    def test_endpoint_not_found_get(self) -> None:
        """Verifies invalid GET endpoints return HTTP 404."""
        code, _, data = self._send_get("/api/not_exist_endpoint")
        self.assertEqual(code, 404)
        self.assertEqual(data["status"], "ERROR")

    def test_endpoint_not_found_post(self) -> None:
        """Verifies invalid POST endpoints return HTTP 404."""
        code, _, data = self._send_post("/api/not_exist_endpoint", {})
        self.assertEqual(code, 404)
        self.assertEqual(data["status"], "ERROR")
