import os
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Application.Services.operator_adapter import YarTraderOperatorAdapter, OperatorTaskStatus, global_operator_adapter

client = TestClient(app)

def get_admin_token():
    email = "admin-op@yartrader.app"
    pw = "Password123!"
    hashed = global_auth_service.hash_password(pw)
    admin = global_auth_service.repo.create_user(
        email=email,
        password_hash=hashed,
        role="ADMIN",
        name="Admin Operator"
    )
    admin["is_verified"] = True
    global_auth_service.repo.users[email] = admin
    auth_res = global_auth_service.authenticate_credentials(email, pw)
    if auth_res:
        sess = global_auth_service.create_session(auth_res)
        return sess
    return None

admin_token = get_admin_token()

def test_operator_adapter_unit_health_check_unavailable():
    """Verifies that YarTraderOperatorAdapter fails closed gracefully when Operator service is offline."""
    os.environ["OPERATOR_SERVER_SECRET"] = "valid-secret-123"
    try:
        adapter = YarTraderOperatorAdapter(host="127.0.0.1", port=9999, timeout_sec=0.1)
        health = adapter.get_runtime_health()
        assert health["connected"] is False
        assert health["status"] == "UNAVAILABLE"
        assert "sohrabinia/YarTrader.Operator" in health["details"]
    finally:
        os.environ.pop("OPERATOR_SERVER_SECRET", None)

def test_operator_adapter_missing_secret_blocked():
    """Verifies that YarTraderOperatorAdapter fails closed if OPERATOR_SERVER_SECRET is missing or empty."""
    os.environ.pop("OPERATOR_SERVER_SECRET", None)
    adapter = YarTraderOperatorAdapter(host="127.0.0.1", port=9999, timeout_sec=0.1)
    health = adapter.get_runtime_health()
    assert health["connected"] is False
    assert health["status"] == "UNAVAILABLE"
    assert "OPERATOR_SERVER_SECRET" in health["details"]

    res = adapter.submit_task(
        admin_identity={"email": "admin-op@yartrader.app", "role": "ADMIN"},
        task_description="Run diagnostic check"
    )
    assert res["success"] is False
    assert res["status"] == OperatorTaskStatus.BLOCKED.value
    assert "OPERATOR_SERVER_SECRET" in res["error"]

def test_operator_adapter_submit_task_non_admin_blocked():
    """Verifies that non-admin identity cannot submit tasks through the adapter."""
    os.environ["OPERATOR_SERVER_SECRET"] = "valid-secret-123"
    try:
        adapter = YarTraderOperatorAdapter()
        res = adapter.submit_task(
            admin_identity={"email": "user@yartrader.app", "role": "USER"},
            task_description="Run diagnostic check"
        )
        assert res["success"] is False
        assert res["status"] == OperatorTaskStatus.BLOCKED.value
        assert "Forbidden" in res["error"]
    finally:
        os.environ.pop("OPERATOR_SERVER_SECRET", None)

def test_operator_adapter_submit_task_offline_fail_closed():
    """Verifies that submitting a task when Operator is offline returns a fail-closed response."""
    os.environ["OPERATOR_SERVER_SECRET"] = "valid-secret-123"
    try:
        adapter = YarTraderOperatorAdapter(host="127.0.0.1", port=9999, timeout_sec=0.1)
        res = adapter.submit_task(
            admin_identity={"email": "admin-op@yartrader.app", "role": "ADMIN"},
            task_description="Run diagnostic check"
        )
        assert res["success"] is False
        assert res["status"] == OperatorTaskStatus.FAILED.value
        assert "unreachable" in res["error"]
        assert "sohrabinia/YarTrader.Operator" in res["details"]
    finally:
        os.environ.pop("OPERATOR_SERVER_SECRET", None)

def test_operator_api_status_unauthenticated_rejected():
    """Verifies 401 response for unauthenticated status query."""
    resp = client.get("/api/admin/operator/status")
    assert resp.status_code == 401

def test_operator_api_status_admin_allowed():
    """Verifies status endpoint for authenticated Admin."""
    os.environ["OPERATOR_SERVER_SECRET"] = "valid-secret-123"
    try:
        resp = client.get("/api/admin/operator/status", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Success"
        assert "admin_identity" in data
        assert data["admin_identity"]["email"] == "admin-op@yartrader.app"
        assert "operator_health" in data
        assert data["operator_health"]["operator_runtime"] == "YarTrader.Operator"
    finally:
        os.environ.pop("OPERATOR_SERVER_SECRET", None)

def test_operator_api_submit_task_and_fail_closed():
    """Verifies task submission API propagates identity and fails closed when Operator is offline."""
    os.environ["OPERATOR_SERVER_SECRET"] = "valid-secret-123"
    try:
        resp = client.post(
            "/api/admin/operator/tasks",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "task_description": "Execute system diagnostic and MT5 DEMO check",
                "metadata": {"environment": "Windows Server"}
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["status"] == OperatorTaskStatus.FAILED.value
        assert "Operator runtime unreachable" in data["error"]
    finally:
        os.environ.pop("OPERATOR_SERVER_SECRET", None)
