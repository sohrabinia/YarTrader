import os
import json
import unittest
import tempfile
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
        """Verify YAROPERATOR_RUNTIME_URL environment variable is respected when loopback."""
        with patch.dict(os.environ, {"YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:3000"}):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter.base_url, "http://127.0.0.1:3000")
            self.assertEqual(adapter.port, 3000)

    def test_external_runtime_url_fails_closed_in_adapter(self):
        """Verify external non-loopback runtime URLs are rejected fail-closed in submit_task and get_runtime_health."""
        admin_identity = {"email": "admin_ext@yartrader.app", "role": "ADMIN"}
        with patch.dict(os.environ, {"YAROPERATOR_RUNTIME_URL": "http://8.8.8.8:3000", "OPERATOR_OWNER_TOKEN": "tok", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            adapter = YarTraderOperatorAdapter()

            # submit_task should be blocked
            res = adapter.submit_task(admin_identity, "Execute task")
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], OperatorTaskStatus.BLOCKED.value)
            self.assertIn("local loopback endpoint", res["error"])

            # get_runtime_health should return UNAVAILABLE
            health = adapter.get_runtime_health()
            self.assertFalse(health["connected"])
            self.assertEqual(health["status"], "UNAVAILABLE")
            self.assertIn("local loopback endpoint", health["details"])

    def test_config_status_reports_missing_runtime_url_when_env_var_absent(self):
        """Verify config_status reports YAROPERATOR_RUNTIME_URL as missing when env var is absent, despite default fallback."""
        admin_identity = {"email": "admin_cfg@yartrader.app", "role": "ADMIN"}
        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "tok_123", "OPERATOR_OWNER_ID": "owner_sohrab"}, clear=True):
            adapter = YarTraderOperatorAdapter()
            health = adapter.get_runtime_health()
            self.assertEqual(health["config_status"]["YAROPERATOR_RUNTIME_URL"], "missing")
            self.assertEqual(health["config_status"]["OPERATOR_OWNER_ID"], "configured")
            self.assertEqual(health["config_status"]["OPERATOR_OWNER_TOKEN"], "configured")

        # When set, should report configured
        with patch.dict(os.environ, {"YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:3000", "OPERATOR_OWNER_TOKEN": "tok_123", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            adapter = YarTraderOperatorAdapter()
            health = adapter.get_runtime_health()
            self.assertEqual(health["config_status"]["YAROPERATOR_RUNTIME_URL"], "configured")

    def test_secret_token_loaded_from_acl_file_when_env_absent(self):
        """Verify OPERATOR_OWNER_TOKEN is safely loaded from secrets/operator_owner_token.secret file if env var is missing."""
        secret_dir = os.path.join(os.getcwd(), "secrets")
        secret_file = os.path.join(secret_dir, "operator_owner_token.secret")

        os.makedirs(secret_dir, exist_ok=True)
        try:
            with open(secret_file, "w", encoding="utf-8") as f:
                f.write("SECRET_FILE_TOKEN_VAL_123")

            with patch.dict(os.environ, {"OPERATOR_OWNER_ID": "owner_sohrab"}, clear=True):
                adapter = YarTraderOperatorAdapter()
                token = adapter._get_bearer_token()
                self.assertEqual(token, "SECRET_FILE_TOKEN_VAL_123")
        finally:
            if os.path.exists(secret_file):
                try:
                    os.remove(secret_file)
                except Exception:
                    pass

    def test_missing_owner_id_fails_closed(self):
        """Verify task submission fails closed if OPERATOR_OWNER_ID is not explicitly configured."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_no_owner@yartrader.app", "role": "ADMIN"}
        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "test_token"}, clear=True):
            res = adapter.submit_task(admin_identity, "Execute task")
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], OperatorTaskStatus.BLOCKED.value)
            self.assertIsNone(res["task_id"])
            self.assertIn("OPERATOR_OWNER_ID", res["error"])

    def test_missing_owner_token_fails_closed(self):
        """Verify task submission fails closed if OPERATOR_OWNER_TOKEN is not explicitly configured."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_no_token@yartrader.app", "role": "ADMIN"}
        with patch.dict(os.environ, {"OPERATOR_OWNER_ID": "owner_sohrab"}, clear=True):
            res = adapter.submit_task(admin_identity, "Execute task")
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], OperatorTaskStatus.BLOCKED.value)
            self.assertIsNone(res["task_id"])
            self.assertIn("OPERATOR_OWNER_TOKEN", res["error"])

    def test_canonical_owner_id_sohrab(self):
        """Verify configured owner ID resolves to canonical owner_sohrab."""
        with patch.dict(os.environ, {"OPERATOR_OWNER_ID": "owner_sohrab"}):
            adapter = YarTraderOperatorAdapter()
            self.assertEqual(adapter._get_owner_id(), "owner_sohrab")

    def test_workspace_mismatch_fails_closed(self):
        """Verify workspace_id other than 'yartrader' is rejected immediately."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_ws@yartrader.app", "role": "ADMIN"}
        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "token_123", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            res = adapter.submit_task(admin_identity, "Execute task", workspace_id="unauthorized_workspace")
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], OperatorTaskStatus.BLOCKED.value)
            self.assertIn("Only 'yartrader' workspace is permitted", res["error"])

    def test_health_check_does_not_execute_commands_and_reports_config_status(self):
        """Verify get_runtime_health() performs a socket connection probe, reports config_status, and does NOT call POST /api/v1/operator/chat."""
        adapter = YarTraderOperatorAdapter()
        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "token_123", "OPERATOR_OWNER_ID": "owner_sohrab", "YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:3000"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                with patch("socket.create_connection") as mock_socket:
                    mock_sock_inst = MagicMock()
                    mock_socket.return_value = mock_sock_inst

                    health = adapter.get_runtime_health()
                    self.assertTrue(health["connected"])
                    self.assertEqual(health["status"], "ONLINE")
                    self.assertEqual(health["config_status"]["OPERATOR_OWNER_ID"], "configured")
                    self.assertEqual(health["config_status"]["YAROPERATOR_RUNTIME_URL"], "configured")
                    self.assertEqual(health["config_status"]["OPERATOR_OWNER_TOKEN"], "configured")

                    # Crucial assertion: urllib.request.urlopen must NEVER be called during health checks
                    mock_urlopen.assert_not_called()

    def test_exact_m12_response_parsing(self):
        """Verify POST /api/v1/operator/chat exact M12 response schema parsing."""
        admin_identity = {"email": "admin_parse@yartrader.app", "role": "ADMIN"}
        adapter = YarTraderOperatorAdapter()

        m12_response_body = {
            "success": True,
            "result": {
                "commandId": "cmd_m12_999",
                "accepted": True,
                "status": "COMPLETED",
                "preservedCommandText": "Run audit",
                "resolvedCapability": "system_audit",
                "resolvedToolId": "tool_audit_v1",
                "auditEventId": "audit_evt_101",
                "details": {"score": 100}
            }
        }

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "m12_token_val", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.read.return_value = json.dumps(m12_response_body).encode("utf-8")
                mock_urlopen.return_value.__enter__.return_value = mock_resp

                res = adapter.submit_task(admin_identity, "Run audit")

                self.assertTrue(res["success"])
                self.assertEqual(res["command_id"], "cmd_m12_999")
                self.assertEqual(res["task_id"], "cmd_m12_999")
                self.assertEqual(res["status"], "COMPLETED")
                self.assertEqual(res["audit_event_id"], "audit_evt_101")
                self.assertEqual(res["result"]["resolvedCapability"], "system_audit")

                # Verify Request headers and body
                req = mock_urlopen.call_args[0][0]
                self.assertTrue(req.full_url.endswith("/api/v1/operator/chat"))
                self.assertEqual(req.headers.get("Authorization"), "Bearer m12_token_val")

                body = json.loads(req.data.decode("utf-8"))
                self.assertEqual(body["ownerId"], "owner_sohrab")
                self.assertEqual(body["workspaceId"], "yartrader")
                self.assertEqual(body["rawCommandText"], "Run audit")
                self.assertEqual(body["environmentId"], "production")

    def test_bearer_token_never_returned_in_api_responses(self):
        """Verify OPERATOR_OWNER_TOKEN is never returned in API responses or diagnostic status."""
        token_val = "SUPER_SECRET_BEARER_TOKEN_999"
        admin = global_auth_service.repo.create_user("admin_sec@yartrader.app", password_hash="pass", role="ADMIN", name="Admin")
        admin_token = global_auth_service.create_session(admin)

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": token_val, "OPERATOR_OWNER_ID": "owner_sohrab", "YAROPERATOR_RUNTIME_URL": "http://127.0.0.1:3000"}):
            res = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
            self.assertNotIn(token_val, res.text)
            self.assertIn('"OPERATOR_OWNER_TOKEN":"configured"', res.text)

    def test_deployment_scripts_do_not_contain_secret_literals_or_plaintext_registry(self):
        """Verify deployment PowerShell scripts do not pass plaintext token in NSSM args or SCM registry."""
        deploy_script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/deploy_service.ps1")
        install_script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/install_service.ps1")

        for script_path in (deploy_script_path, install_script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertNotIn("SUPER_SECRET", content)
                self.assertNotIn("token_val", content)
                self.assertNotIn('OPERATOR_OWNER_TOKEN=$OperatorOwnerToken"', content)
                self.assertIn('operator_owner_token.secret', content)
                self.assertIn('icacls.exe', content)

    def test_deployment_scripts_do_not_accept_operator_owner_token_parameter(self):
        """Verify param(...) block in PowerShell deployment scripts does NOT accept OperatorOwnerToken CLI parameter."""
        deploy_script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/deploy_service.ps1")
        install_script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/install_service.ps1")

        for script_path in (deploy_script_path, install_script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
                param_block = content.split("param(")[1].split(")")[0]
                self.assertNotIn("OperatorOwnerToken", param_block)

    def test_no_local_fake_task_history(self):
        """Verify task history and status endpoints report unsupported state rather than local fake history."""
        adapter = YarTraderOperatorAdapter()
        admin_identity = {"email": "admin_hist@yartrader.app", "role": "ADMIN"}

        tasks_res = adapter.get_all_tasks(admin_identity)
        self.assertFalse(tasks_res["success"])
        self.assertEqual(tasks_res["tasks"], [])
        self.assertIn("not supported", tasks_res["error"])

        status_res = adapter.get_task_status(admin_identity, "cmd_123")
        self.assertFalse(status_res["success"])
        self.assertIn("not supported", status_res["error"])

    def test_operator_status_endpoint_admin_required(self):
        """Verify GET /api/admin/operator/status requires admin authorization."""
        res_anon = self.client.get("/api/admin/operator/status")
        self.assertEqual(res_anon.status_code, 401)

        user = global_auth_service.repo.create_user("user_op@yartrader.app", password_hash="pass", role="USER", name="User")
        user_token = global_auth_service.create_session(user)
        res_user = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(res_user.status_code, 403)

    def test_submit_task_handles_invalid_json_body_200_ok(self):
        """Verify HTTP 200 + invalid non-JSON body returns structured failure payload without raw exception."""
        admin_identity = {"email": "admin_parse@yartrader.app", "role": "ADMIN"}
        adapter = YarTraderOperatorAdapter()

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "token_val", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.read.return_value = b"<html>NOT_JSON_BODY</html>"
                mock_urlopen.return_value.__enter__.return_value = mock_resp

                res = adapter.submit_task(admin_identity, "Run task")

                self.assertFalse(res["success"])
                self.assertEqual(res["status"], OperatorTaskStatus.FAILED.value)
                self.assertIn("malformed response structure", res["error"])
                self.assertIsNone(res["task_id"])

    def test_submit_task_handles_wrong_schema_json_body_200_ok(self):
        """Verify HTTP 200 + valid JSON but non-dict/wrong schema returns structured failure payload."""
        admin_identity = {"email": "admin_parse@yartrader.app", "role": "ADMIN"}
        adapter = YarTraderOperatorAdapter()

        with patch.dict(os.environ, {"OPERATOR_OWNER_TOKEN": "token_val", "OPERATOR_OWNER_ID": "owner_sohrab"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.read.return_value = json.dumps(["just", "a", "list", "not", "dict"]).encode("utf-8")
                mock_urlopen.return_value.__enter__.return_value = mock_resp

                res = adapter.submit_task(admin_identity, "Run task")

                self.assertFalse(res["success"])
                self.assertEqual(res["status"], OperatorTaskStatus.FAILED.value)
                self.assertIn("malformed response structure", res["error"])
                self.assertIsNone(res["task_id"])

    def test_operator_diagnostics_endpoint_returns_worker_status(self):
        """Verify GET /api/admin/operator/diagnostics returns actual latest worker diagnostic event."""
        from app.workers.research_worker import set_last_worker_diagnostic_status
        admin = global_auth_service.repo.create_user("admin_diag@yartrader.app", password_hash="pass", role="ADMIN", name="AdminDiag")
        admin_token = global_auth_service.create_session(admin)

        # 1. Test when no status has been recorded
        set_last_worker_diagnostic_status(None)
        res_empty = self.client.get("/api/admin/operator/diagnostics", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_empty.status_code, 200)
        data_empty = res_empty.json()
        self.assertEqual(data_empty["status"], "NO_DIAGNOSTICS")
        self.assertIsNone(data_empty["last_diagnostic"])

        # 2. Inject a known diagnostic event
        event = {
            "timestamp": "2025-01-01T00:00:00Z",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "cycle_id": "CYC-100",
            "decision_id": "DEC-100",
            "connection_state": "DISCONNECTED",
            "decision_action": "WAIT",
            "risk_state": "SKIPPED",
            "execution_state": "SKIPPED",
            "reason_code": "MT5_DISCONNECTED",
            "details": "MT5 Terminal process unverified"
        }
        set_last_worker_diagnostic_status(event)

        # 3. Request diagnostics endpoint and verify matching reason code and correlation IDs
        res = self.client.get("/api/admin/operator/diagnostics", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "OK")
        diag = data["last_diagnostic"]
        self.assertEqual(diag["reason_code"], "MT5_DISCONNECTED")
        self.assertEqual(diag["symbol"], "XAUUSD")
        self.assertEqual(diag["cycle_id"], "CYC-100")
        self.assertEqual(diag["decision_id"], "DEC-100")
        self.assertEqual(diag["details"], "MT5 Terminal process unverified")

        # 4. Request status endpoint and verify last_worker_diagnostic is included
        res_status = self.client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_status.status_code, 200)
        status_data = res_status.json()
        self.assertIn("last_worker_diagnostic", status_data)
        self.assertEqual(status_data["last_worker_diagnostic"]["reason_code"], "MT5_DISCONNECTED")

if __name__ == "__main__":
    unittest.main()
