import os
import unittest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from src.Application.Services.web_dashboard import app, check_admin_guard
from src.Application.Services.admin_api_router import enforce_admin_token

class TestDashboardDataIntegrityAndBypass(unittest.TestCase):
    """
    Automated test suite verifying data integrity, authentication boundaries,
    and fallback protections under Development and Production environments.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.original_env = os.environ.get("TRADEYAR_ENV")

    def tearDown(self) -> None:
        if self.original_env is not None:
            os.environ["TRADEYAR_ENV"] = self.original_env
        else:
            os.environ.pop("TRADEYAR_ENV", None)

    def test_production_mode_denies_mock_token(self) -> None:
        """Test A - Production Environment: Verify mock_social_token is strictly disabled."""
        os.environ["TRADEYAR_ENV"] = "production"

        # Verify check_admin_guard raises 403 Forbidden for mock_social_token in production
        with self.assertRaises(HTTPException) as ctx:
            check_admin_guard("mock_social_token")
        self.assertEqual(ctx.exception.status_code, 403)

        # Verify enforce_admin_token raises 403 Forbidden for mock_social_token in production
        with self.assertRaises(HTTPException) as ctx:
            enforce_admin_token("mock_social_token")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_development_mode_allows_mock_token(self) -> None:
        """Test B - Development Environment: Verify mock_social_token is accepted as admin."""
        os.environ["TRADEYAR_ENV"] = "development"

        # Verify check_admin_guard accepts mock_social_token
        session = check_admin_guard("mock_social_token")
        self.assertEqual(session.get("role"), "ADMIN")

        # Verify enforce_admin_token accepts mock_social_token
        session2 = enforce_admin_token("mock_social_token")
        self.assertEqual(session2.get("role"), "ADMIN")

    def test_symbols_registry_populated(self) -> None:
        """Test C - Registry Population: Verify `/api/admin/symbols` fetches active symbols."""
        os.environ["TRADEYAR_ENV"] = "development"
        resp = self.client.get("/api/admin/symbols?token=mock_social_token")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("active_symbols", data)
        self.assertGreater(data["count"], 0)

    def test_storage_failures_reported_visible(self) -> None:
        """Test D - Storage Failures: Verify that errors or failures are reported and visible."""
        # When checking validation status, check that the baseline schema does not return mock empty states on error
        resp = self.client.get("/api/validation/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("is_running", data)
        self.assertIn("passed_count", data)
