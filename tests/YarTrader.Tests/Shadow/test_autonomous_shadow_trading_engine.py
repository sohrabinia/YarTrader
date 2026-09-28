import unittest
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app, global_auth_service

class TestRetiredShadowTradingSurface(unittest.TestCase):
    """The legacy Shadow product surface is retired; learning remains in the canonical Brain."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_shadow_metrics_are_retired(self) -> None:
        for path in ["/api/shadow/metrics", "/api/shadow/report"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 410)

    def test_shadow_admin_api_is_retired(self) -> None:
        token = global_auth_service.create_session({
            "email": "admin@yartrader.app",
            "role": "ADMIN",
            "name": "Admin"
        })
        response = self.client.get(
            "/api/admin/shadow-trades",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 410)

    def test_user_signal_surface_remains_available(self) -> None:
        response = self.client.get("/api/user/signals")
        self.assertEqual(response.status_code, 200)

    def test_live_execution_remains_closed(self) -> None:
        response = self.client.get("/api/production-readiness")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
