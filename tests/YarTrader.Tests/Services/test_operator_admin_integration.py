import os
import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service

class TestOperatorAdminIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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
        self.assertIn("operator_runtime", res_admin.json())

    def test_operator_task_submission_admin(self):
        """Verify POST /api/admin/operator/tasks handles admin task submissions."""
        admin = global_auth_service.repo.create_user("admin_task@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        payload = {"task_description": "Deploy YarOperator service worker"}
        res = self.client.post("/api/admin/operator/tasks", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        # Without secret, fails closed with task_id=None
        self.assertIsNone(res.json()["task_id"])

    def test_operator_tasks_list_admin(self):
        """Verify GET /api/admin/operator/tasks requires admin privilege."""
        admin = global_auth_service.repo.create_user("admin_list@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)
        res = self.client.get("/api/admin/operator/tasks", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("tasks", res.json())

if __name__ == "__main__":
    unittest.main()
