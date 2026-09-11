import os
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_auth_users():
    """Sets up test users in the AuthRepository for deterministic test cases."""
    repo = global_auth_service.repo
    # Admin User
    admin_hash = global_auth_service.hash_password("admin_pass_123")
    repo.users["operator-admin@yartrader.app"] = {
        "email": "operator-admin@yartrader.app",
        "password_hash": admin_hash,
        "role": "ADMIN",
        "name": "Operator Admin",
        "user_id": "usr-admin-op-001"
    }
    # Non-Admin Regular User
    user_hash = global_auth_service.hash_password("user_pass_123")
    repo.users["regular-user@yartrader.app"] = {
        "email": "regular-user@yartrader.app",
        "password_hash": user_hash,
        "role": "USER",
        "name": "Regular User",
        "user_id": "usr-regular-002"
    }
    repo.save_db()
    yield

def test_case_a_unauthenticated_access_denied():
    """CASE A — Unauthenticated request is denied."""
    os.environ["YARTRADER_ENV"] = "production"
    try:
        response = client.get("/api/admin/operator")
        assert response.status_code in [401, 403]
    finally:
        os.environ.pop("YARTRADER_ENV", None)

def test_case_b_authenticated_non_admin_denied():
    """CASE B — Authenticated YarTrader user with non-admin role receives 403 Forbidden."""
    user_session = global_auth_service.repo.users["regular-user@yartrader.app"]
    token = global_auth_service.create_session(user_session)

    response = client.get(f"/api/admin/operator?token={token}")
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

def test_case_c_authenticated_admin_allowed():
    """CASE C — Authenticated YarTrader Admin is allowed access."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.get(f"/api/admin/operator?token={token}")
    assert response.status_code == 200
    data = response.json()
    assert data["auth_reused"] is True
    assert data["authoritative_identity"] == "operator-admin@yartrader.app"

def test_case_d_no_second_login_required():
    """CASE D — Flow reuses YarTrader session without requesting second login or Operator password."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.post(
        f"/api/admin/operator?token={token}",
        json={"action": "status"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "OPERATOR_OWNER_TOKEN" not in data
    assert "password" not in data

def test_case_e_server_side_identity_propagation():
    """CASE E — Authenticated YarTrader identity reaches Operator integration context server-side."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.post(
        f"/api/admin/operator?token={token}",
        json={"action": "get_workspace_policy"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authoritative_identity"] == "operator-admin@yartrader.app"

def test_case_f_anti_impersonation():
    """CASE F — Browser-supplied identity override attempt is rejected with 403 Forbidden."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.post(
        f"/api/admin/operator?token={token}",
        json={
            "action": "execute",
            "client_identity": {
                "email": "impersonated-owner@yartrader.app",
                "userId": "usr-fake-999",
                "role": "OWNER"
            }
        }
    )
    assert response.status_code == 403
    assert "conflicts with authoritative session identity" in response.json()["detail"]

def test_case_g_real_runtime_boundary():
    """CASE G — Integration targets real runtime boundary without returning fake mock payloads."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.get(f"/api/admin/operator?token={token}")
    assert response.status_code == 200
    data = response.json()
    # When offline, reports exact missing production dependency rather than fabricating fake success
    assert data["operator_runtime_status"] in ["ONLINE", "OFFLINE"]
    if data["operator_runtime_status"] == "OFFLINE":
        assert "missing_dependency" in data
        assert "YarOperator Internal Production Runtime" in data["missing_dependency"]["required_service"]

def test_case_h_security_preservation():
    """CASE H — Security boundary enforcement metadata remains active."""
    admin_session = global_auth_service.repo.users["operator-admin@yartrader.app"]
    token = global_auth_service.create_session(admin_session)

    response = client.get(f"/api/admin/operator?token={token}")
    assert response.status_code == 200
    data = response.json()
    if data["operator_runtime_status"] == "OFFLINE":
        dep = data["missing_dependency"]
        assert dep["workspace_policy"] == "ENFORCED_SERVER_SIDE"
        assert dep["environment_manager"] == "ENFORCED_SERVER_SIDE"
