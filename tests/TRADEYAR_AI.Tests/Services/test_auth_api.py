import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service

class TestSaaSAuthAPI(unittest.TestCase):
    """
    Comprehensive test suite for secure credentials-based auth services,
    verifying hashing, user registration, login sessions, and password recovery.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        # Register a unique user for credentials testing
        self.test_email = "trader-test-auth@tradeyar.ai"
        self.test_pass = "traderPass123!"
        self.test_name = "Testing Trader"

        # Clear existing user if exists
        repo = global_auth_service.repo
        if self.test_email in repo.users:
            del repo.users[self.test_email]
        repo.save_db()

    def test_user_registration_and_login_lifecycle(self) -> None:
        """Verifies full registration, PBKDF2-SHA256 password validation, and secure session allocation."""
        # 1. Register User
        reg_payload = {
            "email": self.test_email,
            "password": self.test_pass,
            "name": self.test_name
        }
        resp_reg = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(resp_reg.status_code, 200)
        self.assertEqual(resp_reg.json()["status"], "Success")
        self.assertEqual(resp_reg.json()["user"]["email"], self.test_email)

        # Mark verified for this test's login step compliance
        repo = global_auth_service.repo
        if self.test_email in repo.users:
            repo.users[self.test_email]["is_verified"] = True
            repo.save_db()

        # Try duplicate registration
        resp_reg_dup = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(resp_reg_dup.status_code, 400)

        # 2. Login User
        login_payload = {
            "email": self.test_email,
            "password": self.test_pass
        }
        resp_login = self.client.post("/api/auth/login", json=login_payload)
        self.assertEqual(resp_login.status_code, 200)
        self.assertEqual(resp_login.json()["status"], "Success")
        token = resp_login.json()["session_token"]
        self.assertTrue(token.startswith("tkn-"))

        # Verify password validation and session validity
        session = global_auth_service.validate_session(token)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], self.test_email)
        self.assertEqual(session["role"], "USER")

        # Try wrong password login
        wrong_payload = {
            "email": self.test_email,
            "password": "wrongPassword123"
        }
        resp_login_err = self.client.post("/api/auth/login", json=wrong_payload)
        self.assertEqual(resp_login_err.status_code, 401)

        # 3. Forgot Password Simulation
        forgot_payload = {"email": self.test_email}
        resp_forgot = self.client.post("/api/auth/forgot-password", json=forgot_payload)
        self.assertEqual(resp_forgot.status_code, 200)
        self.assertIn("Success", resp_forgot.json()["status"])

        # 4. Logout User
        logout_payload = {"token": token}
        resp_logout = self.client.post("/api/auth/logout", json=logout_payload)
        self.assertEqual(resp_logout.status_code, 200)

        # Verify session is invalidated
        session_invalid = global_auth_service.validate_session(token)
        self.assertIsNone(session_invalid)
