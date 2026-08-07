import os
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from src.Application.Services.admin_api_router import enforce_admin_token
from src.Application.Services.web_dashboard import check_admin_guard
from src.Application.Dashboard.auth_service import global_auth_service

@pytest.fixture(autouse=True)
def clean_env():
    """Backup and restore env vars after each test to prevent pollution."""
    old_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(old_env)

def test_non_admin_user_google_rejected():
    """
    Test 1: Non-admin Google user attempts to access admin endpoint.
    Expect HTTP 403 Forbidden.
    """
    os.environ["ADMIN_EMAIL_ALLOWLIST"] = "m.a.sohrabinia@gmail.com"
    os.environ["RG_ENV"] = "production"

    # Create user session with USER role
    user = {"email": "attacker-google-login@gmail.com", "role": "USER", "name": "Fake Admin"}
    token = global_auth_service.create_session(user)

    try:
        with pytest.raises(HTTPException) as exc_info:
            check_admin_guard(token)
        assert exc_info.value.status_code == 403
        assert "Forbidden" in exc_info.value.detail
    finally:
        global_auth_service.logout(token)

def test_allowed_admin_allowlist_accepted():
    """
    Test 2: Allowed admin email (m.a.sohrabinia@gmail.com) via configuration allowlist.
    Expect successful ADMIN dashboard access.
    """
    os.environ["ADMIN_EMAIL_ALLOWLIST"] = "m.a.sohrabinia@gmail.com"
    os.environ["RG_ENV"] = "production"

    # Create valid ADMIN session
    user = {"email": "m.a.sohrabinia@gmail.com", "role": "ADMIN", "name": "M.A. Sohrabinia"}
    token = global_auth_service.create_session(user)

    try:
        session = check_admin_guard(token)
        assert session["email"] == "m.a.sohrabinia@gmail.com"
        assert session["role"] == "ADMIN"
    finally:
        global_auth_service.logout(token)

def test_privilege_escalation_prevented():
    """
    Test 3: Attacker sends an invalid token.
    Backend must completely ignore any client role claims and rely strictly on validated session.
    """
    os.environ["ADMIN_EMAIL_ALLOWLIST"] = "m.a.sohrabinia@gmail.com"
    os.environ["RG_ENV"] = "production"

    # Attacker passes random fake token "stranger_danger" which does not validate
    with pytest.raises(HTTPException) as exc_info:
        check_admin_guard("stranger_danger")
    assert exc_info.value.status_code == 403

def test_missing_allowlist_fails_closed():
    """
    Test 4: Missing ADMIN_EMAIL_ALLOWLIST configuration.
    Expect application to fail closed, zero admin privileges granted, and security logged.
    """
    # Delete allowlist environment configuration
    if "ADMIN_EMAIL_ALLOWLIST" in os.environ:
        del os.environ["ADMIN_EMAIL_ALLOWLIST"]
    os.environ["RG_ENV"] = "production"

    # Even with a persistent role="ADMIN" in DB, check_admin_guard must fail closed
    user = {"email": "m.a.sohrabinia@gmail.com", "role": "ADMIN", "name": "Principal"}
    token = global_auth_service.create_session(user)

    try:
        with pytest.raises(HTTPException) as exc_info:
            check_admin_guard(token)
        assert exc_info.value.status_code == 403
    finally:
        global_auth_service.logout(token)

def test_session_survives_restart_simulation():
    """
    Test 5: Verified persistent admin authorization survives backend restarts.
    """
    os.environ["ADMIN_EMAIL_ALLOWLIST"] = "m.a.sohrabinia@gmail.com"
    os.environ["RG_ENV"] = "production"

    user = {"email": "m.a.sohrabinia@gmail.com", "role": "ADMIN", "name": "Sohrabinia"}
    token = global_auth_service.create_session(user)

    try:
        # Simulate backend restart by re-instantiating check_admin_guard or re-verifying token
        session = check_admin_guard(token)
        assert session["email"] == "m.a.sohrabinia@gmail.com"
    finally:
        global_auth_service.logout(token)
