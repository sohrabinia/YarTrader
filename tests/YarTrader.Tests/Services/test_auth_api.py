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
        import os
        os.environ["YARTRADER_ENV"] = "test"
        # Register a unique user for credentials testing
        self.test_email = "trader-test-auth@tradeyar.ai"
        self.test_pass = "traderPass123!"
        self.test_name = "Testing Trader"

        # Clear existing user if exists
        repo = global_auth_service.repo
        if self.test_email in repo.users:
            del repo.users[self.test_email]
        repo.save_db()

    def tearDown(self) -> None:
        import os
        os.environ["YARTRADER_ENV"] = "test"

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

    def test_password_hashing_random_salt_and_legacy_support(self) -> None:
        """Verifies random per-password salt generation and backward compatibility for legacy hashes."""
        raw_password = "SecretPassword123!"

        # Generate two hashes of the same password
        hash1 = global_auth_service.hash_password(raw_password)
        hash2 = global_auth_service.hash_password(raw_password)

        # 1. Hashes must be different because salts are cryptographically random
        self.assertNotEqual(hash1, hash2)

        # Extract salts
        salt1 = hash1.split("$")[2]
        salt2 = hash2.split("$")[2]
        self.assertNotEqual(salt1, salt2)

        # 2. Both hashes must be verifiable
        self.assertTrue(global_auth_service.verify_password(raw_password, hash1))
        self.assertTrue(global_auth_service.verify_password(raw_password, hash2))
        self.assertFalse(global_auth_service.verify_password("WrongPassword123!", hash1))

        # 3. Verify legacy hash format with explicit/fixed salt remains verifiable
        legacy_hash = global_auth_service.hash_password(raw_password, salt="salt123")
        self.assertIn("$salt123$", legacy_hash)
        self.assertTrue(global_auth_service.verify_password(raw_password, legacy_hash))

    def test_token_logging_elimination_and_production_email_fail_closed(self) -> None:
        """Verifies token sanitization in email logs and production email fail-closed behavior."""
        import os
        from src.Application.Dashboard.auth_service import send_saas_email

        test_token = "secret_reset_token_xyz_999"
        email_body = f"Click link to reset: http://example.com/reset?token={test_token}"

        # Test non-production sanitization
        os.environ["YARTRADER_ENV"] = "development"
        send_saas_email("user@example.com", "Reset Password", email_body)

        log_path = "runtime_logs/mock_emails.log"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertNotIn(test_token, content)
                self.assertIn("[REDACTED_TOKEN]", content)

        # Test production fail-closed without SMTP
        os.environ["YARTRADER_ENV"] = "production"
        for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]:
            os.environ.pop(k, None)

        sent = send_saas_email("user@example.com", "Reset Password", email_body)
        self.assertFalse(sent)
