"""Authorization regression tests for privileged mutating dashboard endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.Application.Services import web_dashboard


client = TestClient(web_dashboard.app)

MUTATING_ENDPOINTS = [
    ("/api/prop/config", {}),
    ("/api/validation/run", None),
    ("/api/backtest/run", {}),
    ("/api/demo/run", {}),
]


@pytest.mark.parametrize(("path", "body"), MUTATING_ENDPOINTS)
def test_mutating_routes_reject_missing_authentication(path, body):
    response = client.post(path, json=body) if body is not None else client.post(path)
    assert response.status_code == 401


@pytest.mark.parametrize(("path", "body"), MUTATING_ENDPOINTS)
def test_mutating_routes_reject_non_admin_sessions(monkeypatch, path, body):
    monkeypatch.setattr(
        web_dashboard.global_auth_service,
        "validate_session",
        lambda token: {"role": "USER", "email": "user@example.invalid"},
    )
    response = (
        client.post(path, json=body, headers={"Authorization": "Bearer valid-user-session"})
        if body is not None
        else client.post(path, headers={"Authorization": "Bearer valid-user-session"})
    )
    assert response.status_code == 403
