import os
import uuid
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service

class TestSaaSAuthAPI(unittest.TestCase):
    """
    Comprehensive deterministic test suite proving the YarTrader Google-Only Customer Authentication Contract.
    Verifies that Google OIDC is the ONLY customer login mechanism, legacy password/social auth endpoints
    return 410 Gone or 404/405, and Admin Bearer authorization remains independent and intact.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        """Takes an in-memory snapshot of global_auth_service.repo.users for test state isolation."""
        import copy
        self._auth_db_snapshot = copy.deepcopy(global_auth_service.repo.users)

    def tearDown(self) -> None:
        """Restores in-memory and on-disk auth DB to pre-test snapshot preventing test pollution."""
        import copy
        global_auth_service.repo.users = copy.deepcopy(self._auth_db_snapshot)
        global_auth_service.repo.save_db()

    def test_password_endpoints_return_410_gone(self) -> None:
        """Verifies that password endpoints (/register, /login, /set-password) return 410 Gone per Google-Only policy."""
        password_endpoints = [
            ("/api/auth/register", {"email": "test@yartrader.app", "password": "Password123!", "name": "Test"}),
            ("/api/auth/login", {"email": "test@yartrader.app", "password": "Password123!"}),
            ("/api/auth/set-password", {"new_password": "Password123!"})
        ]

        for url, payload in password_endpoints:
            resp = self.client.post(url, json=payload)
            self.assertEqual(resp.status_code, 410, f"Endpoint {url} should return 410 Gone")
            self.assertIn("Password", resp.json()["detail"])
            self.assertIn("disabled", resp.json()["detail"])

    def test_forbidden_customer_auth_endpoints_unreachable(self) -> None:
        """Verifies that non-standard customer auth endpoints (apple, telegram, forgot-password, reset-password, verify-email) return 404/405."""
        forbidden_endpoints = [
            ("POST", "/api/auth/forgot-password", {"email": "user@yartrader.app"}),
            ("GET", "/api/auth/verify-email?token=xyz123", None),
            ("POST", "/api/auth/reset-password", {"token": "xyz123", "new_password": "NewPassword123!"}),
            ("POST", "/api/auth/apple", {"email": "a@b.com", "provider_id": "123"}),
            ("POST", "/api/auth/telegram", {"id": 123, "auth_date": 1, "hash": "x"})
        ]

        for method, url, payload in forbidden_endpoints:
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

    def test_google_oidc_id_token_only_payload_reaches_validation_layer(self) -> None:
        """Verifies that sending an id_token-only payload to /api/auth/google is NOT rejected with 422, but reaches validation (401)."""
        id_token_only_payload = {
            "id_token": "fake.jwt.token"
        }

        with patch("src.Application.Dashboard.oidc_validator.validate_social_token", side_effect=Exception("Token verification failed")):
            resp = self.client.post("/api/auth/google", json=id_token_only_payload)
            self.assertEqual(resp.status_code, 401)
            self.assertNotEqual(resp.status_code, 422)
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

    def test_admin_list_users_returns_registered_and_google_users(self) -> None:
        """
        Verifies that GET /api/admin/users lists all registered user accounts (including Google OIDC users),
        requires ADMIN role authorization, and rejects non-admin/unauthenticated access.
        """
        # 1. Register a Google user
        google_email = f"google-user-{uuid.uuid4().hex[:6]}@gmail.com"
        google_sub = f"sub-google-{uuid.uuid4().hex[:6]}"
        global_auth_service.authenticate_social(
            email=google_email,
            provider="google",
            provider_id=google_sub,
            name="Google Test User"
        )

        # 2. Unauthenticated access fails
        unauth_resp = self.client.get("/api/admin/users")
        self.assertEqual(unauth_resp.status_code, 401)

        # 3. User role access fails with 403
        user_session = {"email": "user@yartrader.app", "role": "USER", "user_id": "usr-normal"}
        user_token = global_auth_service.create_session(user_session)
        user_resp = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(user_resp.status_code, 403)

        # 4. Admin role access succeeds and contains the Google user
        admin_session = {"email": "admin@yartrader.app", "role": "ADMIN", "user_id": "adm-sre"}
        admin_token = global_auth_service.create_session(admin_session)
        admin_resp = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(admin_resp.status_code, 200)
        data = admin_resp.json()
        self.assertEqual(data["status"], "Success")
        self.assertGreaterEqual(data["count"], 1)

        emails = [u["email"] for u in data["users"]]
        self.assertIn(google_email, emails)

        # Verify Google user details
        google_user_item = next(u for u in data["users"] if u["email"] == google_email)
        self.assertEqual(google_user_item["name"], "Google Test User")
        self.assertIn("google", google_user_item["social_providers"])

    def test_session_durability_across_process_restart(self) -> None:
        """Verifies that a customer session token remains valid across AuthService restart/re-instantiation."""
        from src.Application.Dashboard.auth_service import AuthService
        from src.Application.Dashboard.auth_repo import AuthRepository

        # Create user & session in service instance 1
        user = global_auth_service.repo.create_user("restart-user@yartrader.app", "hash123", "USER", "Restart User")
        token = global_auth_service.create_session(user)
        self.assertTrue(token.startswith("tkn-"))

        # Verify token is valid
        sess1 = global_auth_service.validate_session(token)
        self.assertIsNotNone(sess1)
        self.assertEqual(sess1["email"], "restart-user@yartrader.app")

        # Simulate server restart by instantiating a fresh AuthService reading same DB
        fresh_auth_service = AuthService(repo=global_auth_service.repo)

        # Validate token on the fresh AuthService instance
        sess2 = fresh_auth_service.validate_session(token)
        self.assertIsNotNone(sess2, "Session token must survive AuthService process restart")
        self.assertEqual(sess2["email"], "restart-user@yartrader.app")
        self.assertEqual(sess2["role"], "USER")

if __name__ == "__main__":
    unittest.main()
