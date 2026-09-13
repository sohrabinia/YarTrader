import os
import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Application.Dashboard.oidc_validator import validate_social_token
from src.Infrastructure.exceptions import ValidationException
from src.Application.Services.operator_adapter import YarTraderOperatorAdapter, OperatorTaskStatus

class TestCTORemediationSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_unsupported_auth_endpoints_return_404(self):
        """Verify Apple and Telegram auth endpoints return 404 Not Found."""
        res_apple = self.client.post("/api/auth/apple", json={"email": "a@b.com", "provider_id": "123"})
        self.assertEqual(res_apple.status_code, 404)

        res_tg = self.client.post("/api/auth/telegram", json={"id": 123, "auth_date": 1, "hash": "x"})
        self.assertEqual(res_tg.status_code, 404)

        res_tg_link = self.client.post("/api/user/link-telegram", json={"id": 123, "auth_date": 1, "hash": "x"})
        self.assertEqual(res_tg_link.status_code, 404)

    def test_mock_token_rejected_without_explicit_flag(self):
        """Verify mock tokens fail closed unless ALLOW_MOCK_AUTH=true is set."""
        with self.assertRaises(ValidationException) as ctx:
            validate_social_token("mock_token_user@gmail.com_12345_MockUser", "google")
        self.assertIn("ALLOW_MOCK_AUTH=true flag required", str(ctx.exception))

    def test_query_string_token_rejected_on_admin_endpoint(self):
        """Verify query-string tokens on admin endpoints are rejected with HTTP 401."""
        admin_user = global_auth_service.repo.create_user("admin_qs@yartrader.app", password_hash="pass", role="ADMIN", name="Admin QS")
        user_session = global_auth_service.create_session(admin_user)
        res = self.client.get(f"/api/admin/symbols?token={user_session}")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Query string token parameters are strictly forbidden", res.json()["detail"])

    def test_bearer_token_admin_authorization(self):
        """Verify Bearer token authorization works for admin and rejects non-admin."""
        non_admin_user = global_auth_service.repo.create_user("user_bearer@yartrader.app", password_hash="pass", role="USER", name="User Bearer")
        admin_user = global_auth_service.repo.create_user("admin_bearer@yartrader.app", password_hash="pass", role="ADMIN", name="Admin Bearer")
        non_admin_token = global_auth_service.create_session(non_admin_user)
        admin_token = global_auth_service.create_session(admin_user)

        res_user = self.client.get("/api/admin/symbols", headers={"Authorization": f"Bearer {non_admin_token}"})
        self.assertEqual(res_user.status_code, 403)

        res_admin = self.client.get("/api/admin/symbols", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_admin.status_code, 200)

    def test_operator_adapter_fails_closed_without_secret(self):
        """Verify operator adapter returns task_id=None when OPERATOR_SERVER_SECRET is unconfigured."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin@yartrader.app", "role": "ADMIN"}
        res = adapter.submit_task(admin_identity, "Test task")
        self.assertFalse(res["success"])
        self.assertIsNone(res["task_id"])
        self.assertEqual(res["status"], OperatorTaskStatus.BLOCKED.value)

    def test_email_login_accepts_non_gmail_address(self):
        """Verify email+password login works for non-Gmail addresses like Yahoo and Outlook."""
        raw_pass = "TestPass123!"
        hashed_pass = global_auth_service.hash_password(raw_pass)
        user_yahoo = global_auth_service.repo.create_user("trader@yahoo.com", password_hash=hashed_pass, role="USER", name="Yahoo User")
        user_yahoo["is_verified"] = True
        global_auth_service.repo.save_db()

        res_yahoo = self.client.post("/api/auth/login", json={"email": "trader@yahoo.com", "password": raw_pass})
        self.assertEqual(res_yahoo.status_code, 200)
        self.assertIn("session_token", res_yahoo.json())

if __name__ == "__main__":
    unittest.main()
