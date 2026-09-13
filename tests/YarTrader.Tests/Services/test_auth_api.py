import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service

class TestSaaSAuthAPI(unittest.TestCase):
    """
    Comprehensive deterministic test suite proving the YarTrader Google-Only Customer Authentication Contract.
    Verifies that Google OIDC is the ONLY customer login mechanism, legacy password/social auth endpoints
    are strictly 404/405 unreachable, and Admin Bearer authorization remains independent and intact.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_legacy_customer_auth_endpoints_unreachable(self) -> None:
        """Verifies that all legacy email/password customer auth endpoints return 404/405 Not Found/Method Not Allowed."""
        legacy_endpoints = [
            ("POST", "/api/auth/login", {"email": "user@yartrader.app", "password": "Password123!"}),
            ("POST", "/api/auth/register", {"email": "user@yartrader.app", "password": "Password123!", "name": "User"}),
            ("POST", "/api/auth/forgot-password", {"email": "user@yartrader.app"}),
            ("GET", "/api/auth/verify-email?token=xyz123", None),
            ("POST", "/api/auth/reset-password", {"token": "xyz123", "new_password": "NewPassword123!"}),
            ("POST", "/api/auth/apple", {"email": "a@b.com", "provider_id": "123"}),
            ("POST", "/api/auth/telegram", {"id": 123, "auth_date": 1, "hash": "x"})
        ]

        for method, url, payload in legacy_endpoints:
            if method == "POST":
                resp = self.client.post(url, json=payload)
            else:
                resp = self.client.get(url)
            self.assertIn(resp.status_code, (404, 405), f"Endpoint {url} should be unreachable but returned {resp.status_code}")

    def test_google_oidc_authentication_and_session_lifecycle(self) -> None:
        """Verifies valid Google OIDC authentication, session token issuance, session validation, and logout."""
        test_email = "test-google-user@tradeyar.ai"
        google_payload = {
            "id_token": f"mock_token_google_{test_email}_google-sub-998877_Google Tester",
            "email": test_email,
            "provider_id": "google-sub-998877",
            "name": "Google Tester"
        }

        # Non-production mock social login test
        with patch.dict(os.environ, {"ALLOW_MOCK_AUTH": "true"}):
            resp = self.client.post("/api/auth/google", json=google_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Success")
        token = data["session_token"]
        self.assertTrue(token.startswith("tkn-"))

        # Verify session is valid and active
        session = global_auth_service.validate_session(token)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], test_email)
        self.assertEqual(session["role"], "USER")

        # Test Logout
        logout_resp = self.client.post("/api/auth/logout", json={"token": token})
        self.assertEqual(logout_resp.status_code, 200)
        self.assertEqual(logout_resp.json()["status"], "Success")

        # Session should now be invalidated
        self.assertIsNone(global_auth_service.validate_session(token))

    def test_admin_google_oidc_login_grants_admin_role_and_operator_access(self) -> None:
        """Verifies that Google OIDC sign-in for m.a.sohrabinia@gmail.com grants ADMIN role and authorizes Operator access."""
        admin_email = "m.a.sohrabinia@gmail.com"
        google_payload = {
            "id_token": f"mock_token_google_{admin_email}_admin-sub-100_Sorabinia",
            "email": admin_email,
            "provider_id": "admin-sub-100",
            "name": "Principal Administrator"
        }

        with patch.dict(os.environ, {"ALLOW_MOCK_AUTH": "true"}):
            resp = self.client.post("/api/auth/google", json=google_payload)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Success")
        token = data["session_token"]

        # Verify session has ADMIN role server-side
        session = global_auth_service.validate_session(token)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], admin_email)
        self.assertEqual(session["role"], "ADMIN")

        # Verify Operator access with Bearer session token
        headers = {"Authorization": f"Bearer {token}"}
        op_resp = self.client.get("/api/admin/operator/status", headers=headers)
        self.assertEqual(op_resp.status_code, 200)

    def test_invalid_google_oidc_token_fails_closed(self) -> None:
        """Verifies that invalid or malformed Google OIDC token validation fails closed with 401 Unauthorized."""
        invalid_payload = {
            "email": "user@yartrader.app",
            "provider_id": "google-123",
            "id_token": "invalid_or_expired_jwt_token"
        }

        with patch("src.Application.Dashboard.oidc_validator.validate_social_token", side_effect=Exception("Invalid signature")):
            resp = self.client.post("/api/auth/google", json=invalid_payload)
            self.assertEqual(resp.status_code, 401)
            self.assertIn("Google authentication failed", resp.json()["detail"])

    def test_admin_bearer_authorization_remains_independent(self) -> None:
        """Verifies that Admin Bearer authorization remains separate and is not bypassed or converted to customer auth."""
        # Unauthenticated request fails
        resp_unauth = self.client.get("/api/admin/symbols")
        self.assertEqual(resp_unauth.status_code, 401)

        # Customer/USER role token fails with 403 Forbidden
        user_session = {"email": "user@yartrader.app", "role": "USER", "user_id": "usr-1"}
        user_token = global_auth_service.create_session(user_session)
        resp_forbidden = self.client.get("/api/admin/symbols", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(resp_forbidden.status_code, 403)

        # Admin role token succeeds
        admin_session = {"email": "admin@yartrader.app", "role": "ADMIN", "user_id": "adm-1"}
        admin_token = global_auth_service.create_session(admin_session)
        resp_admin = self.client.get("/api/admin/symbols", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp_admin.status_code, 200)
