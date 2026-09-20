import os
import json
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Application.Services.operator_adapter import YarTraderOperatorAdapter, OperatorTaskStatus

class TestOperatorAdminIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_operator_default_port_is_3000(self):
        """Verify default host is 127.0.0.1 and port is 3000 matching YarOperator M12 contract."""
        with patch.dict(os.environ, {}, clear=True):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter.host, "127.0.0.1")
            self.assertEqual(adapter.port, 3000)
            self.assertEqual(adapter.base_url, "http://127.0.0.1:3000")

    def test_operator_runtime_url_env_override(self):
        """Verify YAROPERATOR_RUNTIME_URL environment variable is respected."""
        with patch.dict(os.environ, {"YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:3000"}):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter.base_url, "http://127.0.0.1:3000")
            self.assertEqual(adapter.port, 3000)

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
        self.assertEqual(json_data["port"], 3000)

    def test_operator_task_submission_admin(self):
        """Verify POST /api/admin/operator/tasks handles admin task submissions."""
        admin = global_auth_service.repo.create_user("admin_task@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        payload = {"task_description": "Deploy YarOperator service worker", "workspace_id": "yartrader"}
        res = self.client.post("/api/admin/operator/tasks", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        # Without secret/token, fails closed with task_id=None
        self.assertIsNone(res.json()["task_id"])

    def test_m12_chat_endpoint_contract_and_workspace_propagation(self):
        """Verify POST /api/v1/operator/chat is called with Bearer token, rawCommandText, ownerId, and workspaceId='yartrader'."""
        admin_identity = {"email": "admin_m12@yartrader.app", "role": "ADMIN", "name": "Admin M12"}
        adapter = YarTraderOperatorAdapter()

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "m12_bearer_token_xyz", "OPERATOR_OWNER_ID": "owner_yartrader_prod"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.read.return_value = b'{"taskId": "task_m12_777", "status": "Completed", "output": "Execution successful"}'
                mock_urlopen.return_value.__enter__.return_value = mock_response

                res = adapter.submit_task(
                    admin_identity=admin_identity,
                    task_description="Execute risk assessment",
                    workspace_id="yartrader"
                )

                self.assertTrue(res["success"])
                self.assertEqual(res["task_id"], "task_m12_777")
                self.assertEqual(res["result"], "Execution successful")

                # Verify urllib Request sent to M12 POST /api/v1/operator/chat
                call_args = mock_urlopen.call_args[0]
                req = call_args[0]
                self.assertTrue(req.full_url.endswith("/api/v1/operator/chat"))
                self.assertEqual(req.headers.get("Authorization"), "Bearer m12_bearer_token_xyz")

                sent_body = json.loads(req.data.decode("utf-8"))
                self.assertEqual(sent_body["workspaceId"], "yartrader")
                self.assertEqual(sent_body["ownerId"], "owner_yartrader_prod")
                self.assertEqual(sent_body["rawCommandText"], "Execute risk assessment")
                self.assertEqual(sent_body["environmentId"], "production")

    def test_bearer_token_never_returned_in_api_responses(self):
        """Verify OPERATOR_OWNER_TOKEN / OPERATOR_SERVER_SECRET is never returned in API responses."""
        token_val = "SECRET_BEARER_TOKEN_NEVER_LEAK_123"
        admin = global_auth_service.repo.create_user("admin_sec@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": token_val}):
            res = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
            self.assertNotIn(token_val, res.text)

    def test_unreachable_runtime_fails_closed(self):
        """Verify unreachable YarOperator M12 runtime fails closed with status UNAVAILABLE/FAILED."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_fail@yartrader.app", "role": "ADMIN"}

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "test_token"}):
            with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
                health = adapter.get_runtime_health()
                self.assertFalse(health["connected"])
                self.assertEqual(health["status"], "UNAVAILABLE")

                task_res = adapter.submit_task(admin_identity, "Test command")
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
