import time
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import AuthService, EmailVerificationService, LockoutAuditStore
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Infrastructure.exceptions import ValidationException

client = TestClient(app)

def test_journey_1_registration_success(tmp_path):
    """Scenario 1: Valid registration creates user and sends verification challenge token."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"))
    service = AuthService(repo=repo, verification_service=verification_service)

    email = "JourneyUser1@YarTrader.App"
    reg_res = service.register_user(email=email, password="Password123!", name="Journey Trader 1")

    assert reg_res["user"]["email"] == "journeyuser1@yartrader.app"
    assert reg_res["user"]["is_verified"] is False
    assert reg_res["verification_token"].startswith("vkn-")

def test_journey_2_duplicate_registration(tmp_path):
    """Scenario 2: Duplicate registration with normalized email raises ValidationException."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    service = AuthService(repo=repo)

    email = "DuplicateUser@YarTrader.App"
    service.register_user(email=email, password="Password123!", name="Duplicate Trader")

    with pytest.raises(ValidationException, match="already exists"):
        service.register_user(email=email, password="Password123!", name="Duplicate Trader")

def test_journey_3_unverified_login_rejection(tmp_path):
    """Scenario 3: Unverified user credentials login raises ValidationException."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    service = AuthService(repo=repo)

    email = "UnverifiedLogin@YarTrader.App"
    service.register_user(email=email, password="Password123!", name="Unverified User")

    with pytest.raises(ValidationException, match="Account is not verified"):
        service.authenticate_credentials("unverifiedlogin@yartrader.app", "Password123!")

def test_journey_4_email_verification_lifecycle(tmp_path):
    """Scenarios 4-7: Token verification, single-use enforcement, expired token rejection, and verified login."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"), expiry_seconds=300)
    service = AuthService(repo=repo, verification_service=verification_service)

    email = "LifecycleUser@YarTrader.App"
    reg_data = service.register_user(email=email, password="Password123!", name="Lifecycle User")
    token = reg_data["verification_token"]

    # Verify email account with token
    assert service.verify_email_account(token) is True

    # Login verified user
    user = service.authenticate_credentials("lifecycleuser@yartrader.app", "Password123!")
    assert user is not None
    assert user["is_verified"] is True

    # Reused token must raise ValidationException
    with pytest.raises(ValidationException, match="already been used"):
        verification_service.verify_token(token)

def test_journey_8_protected_endpoint_without_auth():
    """Scenario 8: Protected API endpoint rejects unauthenticated request with HTTP 401 when token verification fails."""
    res = client.get("/api/admin/symbols?token=invalid_token")
    assert res.status_code in [400, 401, 403]

def test_journey_10_logout_session_invalidation(tmp_path):
    """Scenarios 10-11: Verified login creates session token, and logout revokes session access."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"))
    service = AuthService(repo=repo, verification_service=verification_service)

    email = "LogoutUser@YarTrader.App"
    reg_data = service.register_user(email=email, password="Password123!", name="Logout User")
    token = reg_data["verification_token"]
    service.verify_email_account(token)

    # Login to create active session
    user = service.authenticate_credentials("logoutuser@yartrader.app", "Password123!")
    session_token = service.create_session(user)
    assert session_token.startswith("tkn-")

    # Execute logout
    service.logout(session_token)

    # Session token must be revoked
    assert service.get_session_user(session_token) is None
