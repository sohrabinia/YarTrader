import time
import hmac
import hashlib
import pytest
from src.Application.Dashboard.auth_service import AuthService, normalize_email, EmailVerificationService, LockoutAuditStore, CANONICAL_PBKDF2_ITERATIONS
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Application.Services.telegram_auth import verify_telegram_authorization, DEFAULT_TELEGRAM_BOT_TOKEN
from src.Infrastructure.exceptions import ValidationException

def test_email_normalization():
    """Verify that email normalization trims whitespace and lowercases addresses."""
    assert normalize_email("  USER@YarTrader.App  ") == "user@yartrader.app"
    assert normalize_email("Trader.One@Domain.Com") == "trader.one@domain.com"

    with pytest.raises(ValidationException):
        normalize_email("")

    with pytest.raises(ValidationException):
        normalize_email("invalid-email-no-at-sign")

def test_password_hashing_and_verification():
    """Verify PBKDF2-SHA256 password hashing with 600,000 iterations and constant-time verification."""
    service = AuthService(repo=AuthRepository(filepath="runtime_logs/test_auth_repo.json"))
    raw_password = "SecurePassword123!"

    hashed = service.hash_password(raw_password)
    assert f"pbkdf2_sha256${CANONICAL_PBKDF2_ITERATIONS}$" in hashed
    assert raw_password not in hashed  # Plaintext password must never be stored directly

    assert service.verify_password(raw_password, hashed) is True
    assert service.verify_password("WrongPassword123!", hashed) is False

def test_legacy_password_hash_transparent_migration(tmp_path):
    """Verify legacy 100,000-iteration hashes authenticate successfully and transparently rehash to 600,000 iterations."""
    repo_file = str(tmp_path / "auth_legacy_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"))
    service = AuthService(repo=repo, verification_service=verification_service)

    # Manually insert legacy 100,000-iteration user hash
    legacy_email = "legacy@yartrader.app"
    legacy_password = "LegacyPassword123!"
    legacy_hash = service.hash_password(legacy_password, iterations=100000)
    assert "$100000$" in legacy_hash

    user = repo.create_user(email=legacy_email, password_hash=legacy_hash, role="USER", name="Legacy User")
    user["is_verified"] = True
    repo.save_db()

    # Verify initial stored hash is legacy 100k
    stored_before = repo.get_user_by_email(legacy_email)
    assert "$100000$" in stored_before["password_hash"]

    # Authenticate user successfully
    auth_user = service.authenticate_credentials(legacy_email, legacy_password)
    assert auth_user is not None
    assert auth_user["email"] == legacy_email

    # Verify stored hash has been transparently upgraded to 600,000 iterations
    stored_after = repo.get_user_by_email(legacy_email)
    assert f"${CANONICAL_PBKDF2_ITERATIONS}$" in stored_after["password_hash"]

def test_registration_and_unverified_state(tmp_path):
    """Verify user registration sets is_verified=False and returns verification challenge."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"))
    service = AuthService(repo=repo, verification_service=verification_service)

    res = service.register_user(email="NewUser@YarTrader.App", password="MySecretPassword!", name="New Trader")
    assert "user" in res
    assert "verification_token" in res
    assert res["user"]["email"] == "newuser@yartrader.app"
    assert res["user"]["is_verified"] is False
    assert "password_hash" not in res["user"]  # Public user DTO must NEVER expose password_hash
    assert res["verification_token"].startswith("vkn-")

def test_email_verification_lifecycle(tmp_path):
    """Verify challenge token creation, single-use consumption, and account verification transition."""
    repo_file = str(tmp_path / "auth_test.json")
    repo = AuthRepository(filepath=repo_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"), expiry_seconds=300)
    service = AuthService(repo=repo, verification_service=verification_service)

    reg_res = service.register_user(email="VerifyMe@YarTrader.App", password="MyPassword123!", name="Verify User")
    token = reg_res["verification_token"]

    # Attempt login before verification must raise ValidationException
    with pytest.raises(ValidationException, match="Account is not verified"):
        service.authenticate_credentials("verifyme@yartrader.app", "MyPassword123!")

    # Verify email account with token
    assert service.verify_email_account(token) is True

    # User account must now be verified
    user = repo.get_user_by_email("verifyme@yartrader.app")
    assert user["is_verified"] is True

    # Token reuse must fail
    with pytest.raises(ValidationException, match="already been used"):
        verification_service.verify_token(token)

def test_token_expiration(tmp_path):
    """Verify expired token rejection."""
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens_exp.json"), expiry_seconds=-10)
    token = verification_service.create_verification_challenge("exp@yartrader.app")

    with pytest.raises(ValidationException, match="token has expired"):
        verification_service.verify_token(token)

def test_lockout_policy(tmp_path):
    """Verify lockout enforcement after 5 failed authentication attempts."""
    repo_file = str(tmp_path / "auth_test.json")
    lockout_file = str(tmp_path / "lockout_test.json")
    repo = AuthRepository(filepath=repo_file)
    lockout_store = LockoutAuditStore(filepath=lockout_file)
    verification_service = EmailVerificationService(filepath=str(tmp_path / "tokens.json"))
    service = AuthService(repo=repo, lockout_store=lockout_store, verification_service=verification_service)

    service.register_user(email="LockoutTarget@YarTrader.App", password="ValidPassword123!", name="Lockout Target")
    service.verify_email_account(service.verification_service.create_verification_challenge("lockouttarget@yartrader.app"))

    # 4 failed attempts
    for _ in range(4):
        res = service.authenticate_credentials("lockouttarget@yartrader.app", "WrongPassword!")
        assert res is None

    # 5th attempt triggers lockout
    res5 = service.authenticate_credentials("lockouttarget@yartrader.app", "WrongPassword!")
    assert res5 is None

    # 6th attempt even with correct password must be blocked due to lockout
    res_blocked = service.authenticate_credentials("lockouttarget@yartrader.app", "ValidPassword123!")
    assert res_blocked is None

def test_telegram_auth_verification():
    """Verify Telegram login widget payload cryptographic verification."""
    auth_data = {
        "id": "123456789",
        "first_name": "Test",
        "username": "testuser",
        "auth_date": str(int(time.time()))
    }

    # Construct HMAC signature using DEFAULT_TELEGRAM_BOT_TOKEN
    data_check_string = "\n".join([f"{k}={auth_data[k]}" for k in sorted(auth_data.keys())])
    secret_key = hashlib.sha256(DEFAULT_TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
    valid_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    auth_data["hash"] = valid_hash
    is_valid, msg = verify_telegram_authorization(auth_data)
    assert is_valid is True
    assert msg == "Verified"

    # Tampered payload must fail
    tampered_data = dict(auth_data)
    tampered_data["first_name"] = "Attacker"
    is_valid_tampered, _ = verify_telegram_authorization(tampered_data)
    assert is_valid_tampered is False
