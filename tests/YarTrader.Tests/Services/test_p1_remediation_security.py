import os
import time
import shutil
import zipfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import AuthService, LockoutAuditStore
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Infrastructure.exceptions import ValidationException
from src.Application.Runtime.backup_manager import BackupManager

class TestP1RemediationSecurity(unittest.TestCase):
    """
    Focused, robust test suite verifying SaaS subscription tier gating (P1-1),
    secure password reset verification (P1-2), email verification loop (P1-3),
    and backup/restore automation (P1-4).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        # Isolated mock user DB for testing
        self.test_user_db = "runtime_logs/auth_test_p1.json"
        if os.path.exists(self.test_user_db):
            try:
                os.remove(self.test_user_db)
            except Exception:
                pass

        self.repo = AuthRepository(filepath=self.test_user_db)
        self.lockout_file = "runtime_logs/lockout_test_p1.json"
        self.lockout_store = LockoutAuditStore(self.lockout_file)
        self.auth_service = AuthService(repo=self.repo, lockout_store=self.lockout_store)

        # Isolated backup test environment
        self.test_backup_dir = "runtime_logs/backups_test_p1"
        self.test_source_dir = "runtime_logs/source_test_p1"

        if os.path.exists(self.test_backup_dir):
            shutil.rmtree(self.test_backup_dir)
        if os.path.exists(self.test_source_dir):
            shutil.rmtree(self.test_source_dir)

        os.makedirs(self.test_source_dir, exist_ok=True)
        # Create some dummy file contents in the source folder
        with open(os.path.join(self.test_source_dir, "db.json"), "w", encoding="utf-8") as f:
            f.write('{"data": "yartrader"}')

        self.backup_manager = BackupManager(backup_dir=self.test_backup_dir, source_dir=self.test_source_dir)

    def tearDown(self) -> None:
        # Cleanup mock user DB
        if os.path.exists(self.test_user_db):
            try:
                os.remove(self.test_user_db)
            except Exception:
                pass
        # Cleanup lockout audit files
        if os.path.exists(self.lockout_file):
            try:
                os.remove(self.lockout_file)
            except Exception:
                pass
        # Cleanup backups
        if os.path.exists(self.test_backup_dir):
            shutil.rmtree(self.test_backup_dir)
        if os.path.exists(self.test_source_dir):
            shutil.rmtree(self.test_source_dir)

    # -------------------------------------------------------------------------
    # P1-1 SUBSCRIPTION TIER GATING TESTS
    # -------------------------------------------------------------------------

    def test_tier_gating_denies_free_user_accessing_restricted_horizons(self) -> None:
        """Verifies that FREE tier users are blocked from accessing premium horizons (e.g. MICRO)."""
        email = "free-user@yartrader.app"
        user = self.repo.create_user(email=email, password_hash="hash123", role="USER", name="Free User")
        user["is_verified"] = True
        user["tier"] = "FREE"  # FREE tier limits: H1 and SHORT only
        self.repo.users[email] = user
        self.repo.save_db()

        # Login to generate session
        session_token = self.auth_service.create_session(user)
        headers = {"Authorization": f"Bearer {session_token}"}

        # Request with a restricted horizon (MICRO) should return 403 Forbidden
        with patch("src.Application.Services.user_api_router.global_auth_service", self.auth_service):
            resp = self.client.get("/api/user/signals?horizon=micro", headers=headers)
            self.assertEqual(resp.status_code, 403)
            self.assertIn("not permitted", resp.json()["detail"].lower())

    def test_tier_gating_permits_institutional_user_all_access(self) -> None:
        """Verifies that paid INSTITUTIONAL tier users can access premium features without restriction."""
        email = "institutional-user@yartrader.app"
        user = self.repo.create_user(email=email, password_hash="hash123", role="USER", name="Pro User")
        user["is_verified"] = True
        user["tier"] = "INSTITUTIONAL"
        self.repo.users[email] = user
        self.repo.save_db()

        session_token = self.auth_service.create_session(user)
        headers = {"Authorization": f"Bearer {session_token}"}

        with patch("src.Application.Services.user_api_router.global_auth_service", self.auth_service):
            resp = self.client.get("/api/user/signals?horizon=micro", headers=headers)
            self.assertEqual(resp.status_code, 200)

    # -------------------------------------------------------------------------
    # P1-2 PASSWORD RESET VERIFICATION TESTS
    # -------------------------------------------------------------------------

    def test_password_reset_flow_lifecycle(self) -> None:
        """Verifies full forgot password token generation, hashing, secure verification, reset, and token invalidation."""
        email = "forgot@yartrader.app"
        user = self.repo.create_user(email=email, password_hash="hash123", role="USER", name="User")
        user["is_verified"] = True
        self.repo.users[email] = user
        self.repo.save_db()

        # 1. Forgot password request (with mocks to prevent SMTP errors)
        with patch("src.Application.Services.web_dashboard.global_auth_service", self.auth_service):
            resp_forgot = self.client.post("/api/auth/forgot-password", json={"email": email})
            self.assertEqual(resp_forgot.status_code, 200)

            # Retrieve raw token from mock email log
            log_file = "runtime_logs/mock_emails.log"
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract token
            self.assertIn("Reset Your YarTrader Password", content)
            token_prefix = "token to reset your password: "
            start_idx = content.rfind(token_prefix) + len(token_prefix)
            end_idx = content.find("\n", start_idx)
            raw_token = content[start_idx:end_idx].strip()
            self.assertGreater(len(raw_token), 20)

            # 2. Reset password using valid token
            reset_payload = {
                "token": raw_token,
                "new_password": "NewSecurePassword123!"
            }
            resp_reset = self.client.post("/api/auth/reset-password", json=reset_payload)
            self.assertEqual(resp_reset.status_code, 200)
            self.assertEqual(resp_reset.json()["status"], "Success")

            # 3. Check password updated and token is invalidated
            updated_user = self.repo.get_user_by_email(email)
            self.assertIsNone(updated_user.get("reset_token_hash"))
            self.assertTrue(self.auth_service.verify_password("NewSecurePassword123!", updated_user["password_hash"]))

            # 4. Attempt reuse of token must fail
            resp_reuse = self.client.post("/api/auth/reset-password", json=reset_payload)
            self.assertEqual(resp_reuse.status_code, 400)
            self.assertIn("invalid or expired", resp_reuse.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # P1-3 EMAIL VERIFICATION LOOP TESTS
    # -------------------------------------------------------------------------

    def test_unverified_registration_fails_authentication_until_verified(self) -> None:
        """Verifies new registrants default to unverified, are blocked from login, and can login only after verify-email."""
        email = "unverified-test@yartrader.app"
        pw = "Password123!"

        # 1. Register unverified user
        reg_payload = {"email": email, "password": pw, "name": "Test User"}
        with patch("src.Application.Services.web_dashboard.global_auth_service", self.auth_service):
            resp_reg = self.client.post("/api/auth/register", json=reg_payload)
            self.assertEqual(resp_reg.status_code, 200)

            # Unverified account should fail login
            login_payload = {"email": email, "password": pw}
            resp_login = self.client.post("/api/auth/login", json=login_payload)
            self.assertEqual(resp_login.status_code, 401)
            self.assertIn("not verified", resp_login.json()["detail"].lower())

            # Retrieve verification token from mock email log
            log_file = "runtime_logs/mock_emails.log"
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            token_prefix = "token="
            start_idx = content.rfind(token_prefix) + len(token_prefix)
            end_idx = content.find("\n", start_idx)
            if " " in content[start_idx:end_idx]:
                end_idx = content.find(" ", start_idx)
            raw_token = content[start_idx:end_idx].strip()
            self.assertGreater(len(raw_token), 20)

            # 2. Trigger email verification link
            resp_verify = self.client.get(f"/api/auth/verify-email?token={raw_token}")
            self.assertEqual(resp_verify.status_code, 200)
            self.assertIn("Verified", resp_verify.text)

            # 3. Successful verification permits normal authentication
            resp_login_success = self.client.post("/api/auth/login", json=login_payload)
            self.assertEqual(resp_login_success.status_code, 200)
            self.assertEqual(resp_login_success.json()["status"], "Success")

    # -------------------------------------------------------------------------
    # P1-4 BACKUP AND RESTORE AUTOMATION TESTS
    # -------------------------------------------------------------------------

    def test_backup_and_restore_operations_with_retention_and_integrity(self) -> None:
        """Verifies automated zip backups creation, verification, retention constraints, and successful data restoration."""
        # 1. Verify backup creation
        res = self.backup_manager.create_backup()
        self.assertEqual(res["status"], "Success")
        self.assertEqual(res["file_count"], 1)
        backup_file = res["filename"]

        # Verify zip archive exists
        full_backup_path = os.path.join(self.test_backup_dir, backup_file)
        self.assertTrue(os.path.exists(full_backup_path))

        # 2. Verify retention policy deletes old backups when limit exceeded
        # Trigger 6 more backups
        for _ in range(6):
            time.sleep(0.1)  # tiny delay to distinguish modification time
            self.backup_manager.create_backup()

        # Total backup files inside backups folder should be strictly capped to 5!
        backup_files_count = len(glob_backups(self.test_backup_dir))
        self.assertEqual(backup_files_count, 5)

        # 3. Verify corrupted backup is detected on restore
        corrupt_backup = os.path.join(self.test_backup_dir, "corrupt_backup.zip")
        with open(corrupt_backup, "w", encoding="utf-8") as f:
            f.write("definitely_not_a_valid_zip_archive")

        with self.assertRaises(ValidationException) as ctx:
            self.backup_manager.restore_backup("corrupt_backup.zip")
        self.assertIn("not a zip", str(ctx.exception).lower())

        # 4. Verify successful restoration of authentic data
        # Clean source folder first
        shutil.rmtree(self.test_source_dir)
        os.makedirs(self.test_source_dir, exist_ok=True)
        self.assertFalse(os.path.exists(os.path.join(self.test_source_dir, "db.json")))

        # Restore from the last successful backup
        recent_backups = glob_backups(self.test_backup_dir)
        recent_backups.sort(reverse=True)
        last_good_backup = os.path.basename(recent_backups[0])

        restore_res = self.backup_manager.restore_backup(last_good_backup)
        self.assertEqual(restore_res["status"], "Success")

        # Confirm that the file is successfully restored
        self.assertTrue(os.path.exists(os.path.join(self.test_source_dir, "db.json")))
        with open(os.path.join(self.test_source_dir, "db.json"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"data": "yartrader"}')

def glob_backups(directory: str) -> list:
    import glob
    return glob.glob(os.path.join(directory, "backup_*.zip"))
