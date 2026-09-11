import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Services.operator_adapter import YarTraderOperatorAdapter, OperatorTaskStatus, global_operator_adapter

client = TestClient(app)

def test_operator_adapter_unit_health_check_unavailable():
    """Verifies that YarTraderOperatorAdapter fails closed gracefully when Operator service is offline."""
    adapter = YarTraderOperatorAdapter(host="127.0.0.1", port=9999, timeout_sec=0.1)
    health = adapter.get_runtime_health()
    assert health["connected"] is False
    assert health["status"] == "UNAVAILABLE"
    assert "sohrabinia/YarTrader.Operator" in health["details"]

def test_operator_adapter_submit_task_non_admin_blocked():
    """Verifies that non-admin identity cannot submit tasks through the adapter."""
    adapter = YarTraderOperatorAdapter()
    res = adapter.submit_task(
        admin_identity={"email": "user@yartrader.app", "role": "USER"},
        task_description="Run diagnostic check"
    )
    assert res["success"] is False
    assert res["status"] == OperatorTaskStatus.BLOCKED.value
    assert "Forbidden" in res["error"]

def test_operator_adapter_submit_task_offline_fail_closed():
    """Verifies that submitting a task when Operator is offline returns a fail-closed response."""
    adapter = YarTraderOperatorAdapter(host="127.0.0.1", port=9999, timeout_sec=0.1)
    res = adapter.submit_task(
        admin_identity={"email": "admin@yartrader.app", "role": "ADMIN"},
        task_description="Run diagnostic check"
    )
    assert res["success"] is False
    assert res["status"] == OperatorTaskStatus.FAILED.value
    assert "unreachable" in res["error"]
    assert "sohrabinia/YarTrader.Operator" in res["details"]

def test_operator_api_status_unauthenticated_rejected():
    """Verifies 401 response for unauthenticated status query in production environment mode."""
    # TestClient in default test mode overrides check_admin_guard unless YARTRADER_ENV is set
    import os
    os.environ["YARTRADER_ENV"] = "production"
    try:
        resp = client.get("/api/admin/operator/status")
        assert resp.status_code == 401
    finally:
        os.environ.pop("YARTRADER_ENV", None)

def test_operator_api_status_admin_allowed():
    """Verifies status endpoint for authenticated Admin."""
    resp = client.get("/api/admin/operator/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Success"
    assert "admin_identity" in data
    assert "operator_health" in data
    assert data["operator_health"]["operator_runtime"] == "YarTrader.Operator"

def test_operator_api_submit_task_and_fail_closed():
    """Verifies task submission API propagates identity and fails closed when Operator is offline."""
    resp = client.post(
        "/api/admin/operator/tasks",
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
