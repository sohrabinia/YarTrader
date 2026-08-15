import os
import time
import unittest
import base64
from unittest.mock import patch
import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import AuthService, LockoutAuditStore
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Infrastructure.Configuration.settings import ProductionSettings, BaseSettings
from src.Infrastructure.exceptions import ValidationException
from src.Application.Dashboard.oidc_validator import validate_social_token, decode_base64url

class TestP0RemediationSecurity(unittest.TestCase):
    """
    Comprehensive, focused test suite verifying real OIDC cryptographic validation,
    production database credential fail-closed rules, and persistent admin lockouts.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        # Generate real RSA keys for cryptographic JWT signature testing
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()

        # Derive JWKS components (n, e) from public key
        numbers = cls.public_key.public_numbers()

        # Convert integers n and e to base64url bytes
        n_bytes = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder='big')
        e_bytes = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, byteorder='big')

        cls.mock_jwks = [
            {
                "kid": "test-kid-123",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": base64_url_encode(n_bytes),
                "e": base64_url_encode(e_bytes)
            }
        ]

    def setUp(self) -> None:
        # Clear lockout audit logs before each test
        import uuid
        self.lockout_file = f"runtime_logs/lockout_test_audit_{uuid.uuid4().hex}.json"
        if os.path.exists(self.lockout_file):
            try:
                os.remove(self.lockout_file)
            except Exception:
                pass
        self.lockout_store = LockoutAuditStore(self.lockout_file)
        self.auth_service = AuthService(lockout_store=self.lockout_store)

    def tearDown(self) -> None:
        if os.path.exists(self.lockout_file):
            try:
                os.remove(self.lockout_file)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # P0-1 SOCIAL SIGN-IN TESTS
    # -------------------------------------------------------------------------

    @patch("src.Application.Dashboard.oidc_validator.fetch_jwks")
    def test_social_login_google_cryptographic_success(self, mock_fetch) -> None:
        """Verifies that a valid cryptographically signed Google token with correct issuer/audience is accepted."""
        mock_fetch.return_value = self.mock_jwks

        payload = {
            "iss": "https://accounts.google.com",
            "aud": "test-google-client-id",
            "sub": "google-user-12345",
            "email": "google-user@yartrader.app",
            "name": "Google User",
            "exp": int(time.time()) + 3600,
            "email_verified": True
        }

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "test-kid-123"}
        )

        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-google-client-id"}):
            decoded = validate_social_token(token, "google")
            self.assertEqual(decoded["email"], "google-user@yartrader.app")
            self.assertEqual(decoded["sub"], "google-user-12345")

    @patch("src.Application.Dashboard.oidc_validator.fetch_jwks")
    def test_social_login_google_expired_rejected(self, mock_fetch) -> None:
        """Verifies that an expired Google OIDC token is strictly rejected."""
        mock_fetch.return_value = self.mock_jwks

        payload = {
            "iss": "https://accounts.google.com",
            "aud": "test-google-client-id",
            "sub": "google-user-12345",
            "email": "google-user@yartrader.app",
            "exp": int(time.time()) - 100,  # expired
            "email_verified": True
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": "test-kid-123"})

        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-google-client-id"}):
            with self.assertRaises(ValidationException) as ctx:
                validate_social_token(token, "google")
            self.assertIn("expired", str(ctx.exception).lower())

    @patch("src.Application.Dashboard.oidc_validator.fetch_jwks")
    def test_social_login_google_wrong_audience_rejected(self, mock_fetch) -> None:
        """Verifies that a token intended for another client ID is strictly rejected."""
        mock_fetch.return_value = self.mock_jwks

        payload = {
            "iss": "https://accounts.google.com",
            "aud": "wrong-client-id",
            "sub": "google-user-12345",
            "email": "google-user@yartrader.app",
            "exp": int(time.time()) + 3600,
            "email_verified": True
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": "test-kid-123"})

        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-google-client-id"}):
            with self.assertRaises(ValidationException) as ctx:
                validate_social_token(token, "google")
            self.assertIn("audience", str(ctx.exception).lower())

    @patch("src.Application.Dashboard.oidc_validator.fetch_jwks")
    def test_social_login_google_wrong_issuer_rejected(self, mock_fetch) -> None:
        """Verifies that a token from an unverified/attacker issuer is strictly rejected."""
        mock_fetch.return_value = self.mock_jwks

        payload = {
            "iss": "https://attacker-identity-provider.com",
            "aud": "test-google-client-id",
            "sub": "google-user-12345",
            "email": "google-user@yartrader.app",
            "exp": int(time.time()) + 3600,
            "email_verified": True
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": "test-kid-123"})

        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-google-client-id"}):
            with self.assertRaises(ValidationException) as ctx:
                validate_social_token(token, "google")
            self.assertIn("issuer", str(ctx.exception).lower())

    @patch("src.Application.Dashboard.oidc_validator.fetch_jwks")
    def test_social_login_apple_cryptographic_success(self, mock_fetch) -> None:
        """Verifies that a valid Apple signed token is accepted."""
        mock_fetch.return_value = self.mock_jwks

        payload = {
            "iss": "https://appleid.apple.com",
            "aud": "test-apple-client-id",
            "sub": "apple-user-9988",
            "email": "apple-user@yartrader.app",
            "exp": int(time.time()) + 3600
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": "test-kid-123"})

        with patch.dict(os.environ, {"APPLE_CLIENT_ID": "test-apple-client-id"}):
            decoded = validate_social_token(token, "apple")
            self.assertEqual(decoded["email"], "apple-user@yartrader.app")

    def test_social_login_missing_config_fails_closed_in_production(self) -> None:
        """Verifies that social validation immediately fails closed in production mode if configuration is missing."""
        token = "some-token"
        with patch.dict(os.environ, {"TRADEYAR_ENV": "production", "GOOGLE_CLIENT_ID": ""}):
            with self.assertRaises(ValidationException) as ctx:
                validate_social_token(token, "google")
            self.assertIn("configuration error", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # P0-2 DATABASE CREDENTIALS TESTS
    # -------------------------------------------------------------------------

    def test_production_mode_fail_closed_on_missing_db_token(self) -> None:
        """Verifies that ProductionSettings initialization raises ValidationException if RG_DB_SECURE_TOKEN is missing."""
        with patch.dict(os.environ, {"TRADEYAR_ENV": "production", "RG_DB_SECURE_TOKEN": ""}):
            with self.assertRaises(ValidationException) as ctx:
                ProductionSettings()
            self.assertIn("rg_db_secure_token", str(ctx.exception).lower())

    def test_production_mode_fail_closed_on_placeholder_db_token(self) -> None:
        """Verifies that ProductionSettings initialization raises ValidationException if a default placeholder is used."""
        for placeholder in ["prod-token-secure", "dev-token-12345", "test-token-77777"]:
            with patch.dict(os.environ, {"TRADEYAR_ENV": "production", "RG_DB_SECURE_TOKEN": placeholder}):
                with self.assertRaises(ValidationException) as ctx:
                    ProductionSettings()
                self.assertIn("insecure placeholder", str(ctx.exception).lower())

    def test_production_mode_fail_closed_on_missing_admin_password_hash(self) -> None:
        """Verifies that AuthRepository raises ValidationException in production if TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH is unset/insecure."""
        # Using a temporary mock filepath for the user JSON DB
        test_filepath = "runtime_logs/auth_test_prod_fail.json"
        if os.path.exists(test_filepath):
            os.remove(test_filepath)

        try:
            with patch.dict(os.environ, {
                "TRADEYAR_ENV": "production",
                "TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH": "",
                "TRADEYAR_DEFAULT_ADMIN_EMAIL": "admin@yartrader.app"
            }):
                with self.assertRaises(ValidationException) as ctx:
                    AuthRepository(filepath=test_filepath)
                self.assertIn("password_hash", str(ctx.exception).lower())
        finally:
            if os.path.exists(test_filepath):
                os.remove(test_filepath)

    def test_development_settings_isolated_from_production_fail_closed(self) -> None:
        """Verifies that non-production environments can continue using defaults without trigger-blocking prod rules."""
        # Clean environment without RG_DB_SECURE_TOKEN to test default fallback
        old_env = os.environ.pop("RG_DB_SECURE_TOKEN", None)
        try:
            with patch.dict(os.environ, {"TRADEYAR_ENV": "development"}):
                # Dev initialization succeeds and uses sandbox defaults
                settings = BaseSettings()
                self.assertEqual(settings.db_token, "dev-token-12345")
        finally:
            if old_env is not None:
                os.environ["RG_DB_SECURE_TOKEN"] = old_env

    # -------------------------------------------------------------------------
    # P0-3 ADMIN LOCKOUT TESTS
    # -------------------------------------------------------------------------

    def test_admin_lockout_persists_across_restart(self) -> None:
        """Verifies that failed login attempts are written persistently and lockout state survives manager re-initialization."""
        email = "admin@yartrader.app"
        now = time.time()

        # 1. Record 4 attempts
        for i in range(4):
            self.lockout_store.record_failed_attempt(email, now)

        # Re-initialize LockoutAuditStore and AuthService (simulating a full process restart)
        new_store = LockoutAuditStore(self.lockout_file)
        new_service = AuthService(lockout_store=new_store)

        # 2. Add the 5th attempt (which triggers persistent lockout)
        res = new_service.authenticate_credentials(email, "incorrect_pass")
        self.assertIsNone(res)

        # 3. Add a 6th attempt, which should be immediately blocked by persistent lockout
        res_blocked = new_service.authenticate_credentials(email, "incorrect_pass")
        self.assertIsNone(res_blocked)

        # Verify the lockout event is in the audit log
        logs = new_store._load()["audit_log"]
        lockout_events = [l for l in logs if l["event_type"] == "ADMIN_LOCKOUT"]
        self.assertGreaterEqual(len(lockout_events), 1)
        self.assertTrue(lockout_events[0]["lockout_state"])

    def test_lockout_records_source_ip_and_user_agent(self) -> None:
        """Verifies that user agent and client IP are successfully extracted and persisted in the lockout audit record."""
        email = "admin-audit@yartrader.app"
        now = time.time()

        self.lockout_store.log_audit_event(
            event_type="ADMIN_LOGIN_FAILURE",
            identifier=email,
            source_ip="203.0.113.195",
            user_agent="YarTraderSecBot/1.0",
            result="Failed password",
            lockout_state=False,
            penalty_info="Attempt 1/5"
        )

        # Load directly from persistent store
        data = self.lockout_store._load()
        self.assertEqual(data["audit_log"][-1]["source_ip"], "203.0.113.195")
        self.assertEqual(data["audit_log"][-1]["user_agent"], "YarTraderSecBot/1.0")

    def test_lockout_never_logs_passwords(self) -> None:
        """Verifies that password/secrets are never recorded in the audit trail or persistent logs."""
        email = "sec-test@yartrader.app"
        secret_password = "MySuperSecretPassword123!"

        # Authenticate with credentials
        self.auth_service.authenticate_credentials(email, secret_password)

        # Read raw JSON file
        with open(self.lockout_file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Ensure password is not written anywhere in the file
        self.assertNotIn(secret_password, raw_text)


# Help utilities for OIDC key conversion
def base64_url_encode(b: bytes) -> str:
    """Helper to base64url encode bytes without padding."""
    return base64.b64encode(b).decode('utf-8').replace("+", "-").replace("/", "_").rstrip("=")
