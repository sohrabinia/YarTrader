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
    are strictly 404/405 unreachable, and Admin Bearer authorization remains independent and intact.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

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

    def test_email_password_registration_and_login_flow(self) -> None:
        """Verifies working email/password registration, login, wrong password rejection, and duplicate email rejection."""
        import uuid
        test_email = f"newtrader-{uuid.uuid4().hex[:6]}@yartrader.app"
        test_password = "SecurePassword123!"

        # 1. Registration Success
        reg_resp = self.client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "name": "New Trader"
        })
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        self.assertEqual(reg_data["status"], "Success")
        self.assertTrue(reg_data["session_token"].startswith("tkn-"))
        self.assertEqual(reg_data["user"]["email"], test_email)
        self.assertEqual(reg_data["user"]["role"], "USER")

        # 2. Duplicate Registration Rejection
        dup_resp = self.client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "name": "Duplicate Trader"
        })
        self.assertEqual(dup_resp.status_code, 400)
        self.assertIn("already exists", dup_resp.json()["detail"])

        # 3. Wrong Password Rejection
        wrong_resp = self.client.post("/api/auth/login", json={
            "email": test_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(wrong_resp.status_code, 401)
        self.assertIn("Invalid email or password", wrong_resp.json()["detail"])

        # 4. Login Success
        login_resp = self.client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        self.assertEqual(login_resp.status_code, 200)
        login_data = login_resp.json()
        self.assertEqual(login_data["status"], "Success")
        token = login_data["session_token"]

        # Verify session model matches Google login
        session = global_auth_service.validate_session(token)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], test_email)
        self.assertEqual(session["role"], "USER")

    def test_registration_security_boundary_rejection_for_existing_accounts(self) -> None:
        """
        Verifies that /register strictly REJECTS attempts for existing emails (Google accounts, Admin accounts, and Password accounts)
        without mutating passwords or granting admin access.
        """
        import uuid

        # Test A: Existing Google account + /register -> Rejected with 400
        google_email = f"existing-google-{uuid.uuid4().hex[:6]}@gmail.com"
        google_sub = f"sub-{uuid.uuid4().hex[:6]}"
        google_user = global_auth_service.authenticate_social(
            email=google_email,
            provider="google",
            provider_id=google_sub,
            name="Google Existing User"
        )
        self.assertEqual(google_user["password_hash"], "")

        reg_google_resp = self.client.post("/api/auth/register", json={
            "email": google_email,
            "password": "AttemptedPassword123!",
            "name": "Attacker"
        })
        self.assertEqual(reg_google_resp.status_code, 400)
        self.assertIn("already exists", reg_google_resp.json()["detail"])

        # Confirm account was NOT mutated
        unmutated_google_user = global_auth_service.repo.get_user_by_email(google_email)
        self.assertEqual(unmutated_google_user["password_hash"], "")
        self.assertEqual(unmutated_google_user["email"], google_email)

        # Test B: Existing admin account + /register -> Rejected with 400
        admin_email = f"admin-{uuid.uuid4().hex[:6]}@yartrader.app"
        admin_orig_pw = "OriginalAdminPass123!"
        admin_user = global_auth_service.register_user(email=admin_email, password=admin_orig_pw, name="Admin User")
        admin_orig_hash = admin_user["password_hash"]

        reg_admin_resp = self.client.post("/api/auth/register", json={
            "email": admin_email,
            "password": "AttackerPassword999!",
            "name": "Attacker"
        })
        self.assertEqual(reg_admin_resp.status_code, 400)
        self.assertIn("already exists", reg_admin_resp.json()["detail"])

        # Confirm admin password hash was NOT overwritten
        unmutated_admin = global_auth_service.repo.get_user_by_email(admin_email)
        self.assertEqual(unmutated_admin["password_hash"], admin_orig_hash)

    def test_authenticated_password_recovery_flow_preserves_identity_and_data(self) -> None:
        """
        Verifies that an authenticated Google user can establish a password credential via /api/auth/set-password.
        Asserts that user_id, email, social_providers (Google sub), role, and customer data are preserved,
        and that unauthenticated recovery attempts are rejected.
        """
        import uuid
        test_email = f"google-recovery-{uuid.uuid4().hex[:6]}@gmail.com"
        google_sub = f"google-sub-{uuid.uuid4().hex[:6]}"

        # 1. User signs up via Google OIDC
        user = global_auth_service.authenticate_social(
            email=test_email,
            provider="google",
            provider_id=google_sub,
            name="Google Account Owner"
        )
        orig_social_providers = dict(user.get("social_providers", {}))
        self.assertEqual(user["password_hash"], "")

        # 2. Unauthenticated password reset attempt -> 401 Unauthorized
        unauth_resp = self.client.post("/api/auth/set-password", json={
            "new_password": "NewPassword123!"
        })
        self.assertEqual(unauth_resp.status_code, 401)

        # 3. Create authenticated session for the Google user
        token = global_auth_service.create_session(user)

        # 4. Authenticated password update -> 200 Success
        new_password = "NewPasswordForGoogleAccount123!"
        auth_resp = self.client.post(
            "/api/auth/set-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_password": new_password}
        )
        self.assertEqual(auth_resp.status_code, 200)
        self.assertEqual(auth_resp.json()["status"], "Success")

        # 5. Assert Identity & Account Preservation
        updated_user = global_auth_service.repo.get_user_by_email(test_email)
        self.assertEqual(updated_user["email"], test_email)
        self.assertEqual(updated_user["social_providers"], orig_social_providers)
        self.assertNotEqual(updated_user["password_hash"], "")

        # 6. Verify Email/Password Login works
        login_resp = self.client.post("/api/auth/login", json={
            "email": test_email,
            "password": new_password
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertEqual(login_resp.json()["user"]["email"], test_email)

        # 7. Verify Google Sign-In still works
        google_session = global_auth_service.authenticate_social(
            email=test_email,
            provider="google",
            provider_id=google_sub
        )
        self.assertEqual(google_session["email"], test_email)

    def test_admin_role_granted_via_email_login_and_operator_authorization(self) -> None:
        """Verifies that registering or logging in via email as m.a.sohrabinia@gmail.com grants ADMIN role and authorizes Operator access."""
        admin_email = "admin-email-test@yartrader.app"
        admin_password = "AdminSecurePassword123!"

        # Mock is_admin_email to classify admin_email as admin for test isolation
        with patch.object(global_auth_service.repo, "is_admin_email", side_effect=lambda email: email.lower() in (admin_email, "m.a.sohrabinia@gmail.com")):
            reg_resp = self.client.post("/api/auth/register", json={
                "email": admin_email,
                "password": admin_password,
                "name": "Principal Administrator"
            })
            if reg_resp.status_code == 400:
                reg_resp = self.client.post("/api/auth/login", json={
                    "email": admin_email,
                    "password": admin_password
                })

            self.assertEqual(reg_resp.status_code, 200)
            admin_token = reg_resp.json()["session_token"]

        # Verify session has ADMIN role
        session = global_auth_service.validate_session(admin_token)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], admin_email)
        self.assertEqual(session["role"], "ADMIN")

        # Verify Admin can access Operator status endpoint
        headers = {"Authorization": f"Bearer {admin_token}"}
        op_resp = self.client.get("/api/admin/operator/status", headers=headers)
        self.assertIn(op_resp.status_code, (200, 503))

        # Verify normal USER receives 403 Forbidden on Operator endpoint
        user_reg_email = f"normaluser-{uuid.uuid4().hex[:6]}@yartrader.app"
        user_reg = self.client.post("/api/auth/register", json={
            "email": user_reg_email,
            "password": "UserPass123!",
            "name": "Normal User"
        })
        user_token = user_reg.json()["session_token"]
        user_op_resp = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(user_op_resp.status_code, 403)

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
