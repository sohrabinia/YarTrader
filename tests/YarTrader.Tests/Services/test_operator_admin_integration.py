import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Application.Services.operator_adapter import YarTraderOperatorAdapter, OperatorTaskStatus

class TestOperatorAdminIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_operator_default_port_is_8080(self):
        """Verify default host is 127.0.0.1 and port is 8080 without stale 8890 assumption."""
        with patch.dict(os.environ, {}, clear=True):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter.host, "127.0.0.1")
            self.assertEqual(adapter.port, 8080)
            self.assertEqual(adapter.base_url, "http://127.0.0.1:8080")

    def test_operator_runtime_url_env_override(self):
        """Verify YAROPERATOR_RUNTIME_URL environment variable is respected."""
        with patch.dict(os.environ, {"YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:8080"}):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter.base_url, "http://127.0.0.1:8080")
            self.assertEqual(adapter.port, 8080)

    def test_operator_status_endpoint_admin_required(self):
        """Verify GET /api/admin/operator/status requires admin authorization."""
        res_anon = self.client.get("/api/admin/operator/status")
        self.assertEqual(res_anon.status_code, 401)

        user = global_auth_service.repo.create_user("user_op@yartrader.app", password_hash="pass", role="USER", name="User")
        user_token = global_auth_service.create_session(user)
        res_user = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(res_user.status_code, 403)

    def test_operator_status_endpoint_with_admin_headers(self):
        """Verify GET /api/admin/operator/status succeeds for authenticated admin."""
        admin = global_auth_service.repo.create_user("admin_op@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        res_admin = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_admin.status_code, 200)
        json_data = res_admin.json()
        self.assertIn("operator_runtime", json_data)
        self.assertEqual(json_data["port"], 8080)

    def test_operator_task_submission_admin(self):
        """Verify POST /api/admin/operator/tasks handles admin task submissions."""
        admin = global_auth_service.repo.create_user("admin_task@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        payload = {"task_description": "Deploy YarOperator service worker", "workspace_id": "yartrader"}
        res = self.client.post("/api/admin/operator/tasks", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        # Without secret, fails closed with task_id=None
        self.assertIsNone(res.json()["task_id"])

    def test_operator_task_submission_workspace_propagation(self):
        """Verify workspace_id is forwarded to YarOperator task payload."""
        admin_identity = {"email": "admin_ws@yartrader.app", "role": "ADMIN", "name": "Admin WS"}
        adapter = YarTraderOperatorAdapter()

        with patch.dict(os.environ, {"OPERATOR_SERVER_SECRET": "test_secret_123"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 201
                mock_response.read.return_value = b'{"status": "Created", "task_id": "task_1001"}'
                mock_urlopen.return_value.__enter__.return_value = mock_response

                res = adapter.submit_task(
                    admin_identity=admin_identity,
                    task_description="Execute risk audit",
                    workspace_id="custom_workspace"
                )

                self.assertTrue(res["success"])
                self.assertEqual(res["task_id"], "task_1001")

                # Verify Request object sent to urllib
                call_args = mock_urlopen.call_args[0]
                req = call_args[0]
                import json
                sent_body = json.loads(req.data.decode("utf-8"))
                self.assertEqual(sent_body["workspace_id"], "custom_workspace")
                self.assertEqual(sent_body["requested_by"]["email"], "admin_ws@yartrader.app")
                self.assertEqual(req.headers.get("X-operator-server-secret"), "test_secret_123")

    def test_secret_never_returned_in_api_responses(self):
        """Verify OPERATOR_SERVER_SECRET is never returned in API payloads."""
        secret_val = "SUPER_SECRET_OPERATOR_KEY_999"
        admin = global_auth_service.repo.create_user("admin_sec@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)

        with patch.dict(os.environ, {"OPERATOR_SERVER_SECRET": secret_val}):
            res = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
            res_str = res.text
            self.assertNotIn(secret_val, res_str)

    def test_unreachable_runtime_fails_closed(self):
        """Verify unreachable YarOperator runtime fails closed with status UNAVAILABLE/FAILED."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_fail@yartrader.app", "role": "ADMIN"}

        with patch.dict(os.environ, {"OPERATOR_SERVER_SECRET": "test_secret"}):
            with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
                health = adapter.get_runtime_health()
                self.assertFalse(health["connected"])
                self.assertEqual(health["status"], "UNAVAILABLE")

                task_res = adapter.submit_task(admin_identity, "Test task")
                self.assertFalse(task_res["success"])
                self.assertEqual(task_res["status"], OperatorTaskStatus.FAILED.value)

    def test_operator_tasks_list_admin(self):
        """Verify GET /api/admin/operator/tasks requires admin privilege."""
        admin = global_auth_service.repo.create_user("admin_list@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        res = self.client.get("/api/admin/operator/tasks", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("tasks", res.json())

if __name__ == "__main__":
    unittest.main()
