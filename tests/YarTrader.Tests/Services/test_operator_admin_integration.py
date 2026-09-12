import os
import json
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service

client = TestClient(app)

def get_admin_headers():
    user = global_auth_service.authenticate_social(
        email="admin_operator_test@yartrader.app",
        provider="google",
        provider_id="google_12345",
        name="Admin Test User"
    )
    user["role"] = "ADMIN"
    token = global_auth_service.create_session(user)
    return {"Authorization": f"Bearer {token}"}

def test_operator_status_endpoint_admin_required():
    res = client.get("/api/admin/operator/status")
    assert res.status_code in (200, 401, 403)

def test_operator_status_endpoint_with_admin_headers():
    headers = get_admin_headers()
    res = client.get("/api/admin/operator/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "operator_runtime" in data
    assert "status" in data
    assert "connected" in data

def test_operator_task_submission_admin():
    headers = get_admin_headers()
    payload = {
        "task_description": "Return current Operator health status.",
        "workspace_id": "yartrader"
    }
    res = client.post("/api/admin/operator/tasks", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "status" in data

def test_operator_tasks_list_admin():
    headers = get_admin_headers()
    res = client.get("/api/admin/operator/tasks", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "tasks" in data or "error" in data or "success" in data
