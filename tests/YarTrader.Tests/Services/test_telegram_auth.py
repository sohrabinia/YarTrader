import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Application.Services.telegram_auth import DEFAULT_TELEGRAM_BOT_TOKEN, verify_telegram_authorization

client = TestClient(app)

def make_telegram_payload(
    user_id=123456789,
    first_name="John",
    username="john_doe",
    auth_date=None,
    bot_token=DEFAULT_TELEGRAM_BOT_TOKEN,
    alter_key=None,
    alter_val=None
):
    if auth_date is None:
        auth_date = int(time.time())
    data = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "auth_date": auth_date
    }
    check_list = [f"{k}={v}" for k, v in sorted(data.items()) if v is not None and v != ""]
    check_str = "\n".join(check_list)
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    hash_val = hmac.new(secret_key, check_str.encode("utf-8"), hashlib.sha256).hexdigest()
    data["hash"] = hash_val

    if alter_key:
        data[alter_key] = alter_val

    return data

def test_telegram_auth_verification_valid():
    """Verify cryptographic verification helper with valid payload."""
    payload = make_telegram_payload()
    is_valid, err_msg = verify_telegram_authorization(payload)
    assert is_valid is True
    assert err_msg == "Verified"

def test_telegram_auth_verification_invalid_hash():
    """Verify cryptographic verification failure on altered signature."""
    payload = make_telegram_payload(alter_key="hash", alter_val="invalid_hash_value_12345")
    is_valid, err_msg = verify_telegram_authorization(payload)
    assert is_valid is False
    assert "Invalid Telegram cryptographic signature" in err_msg

def test_telegram_auth_verification_modified_payload():
    """Verify cryptographic failure when payload fields are tampered with after signing."""
    payload = make_telegram_payload()
    payload["first_name"] = "Hacker" # Tamper with field without re-signing
    is_valid, err_msg = verify_telegram_authorization(payload)
    assert is_valid is False
    assert "Invalid Telegram cryptographic signature" in err_msg

def test_telegram_auth_verification_expired():
    """Verify rejection of expired auth_date (>86400 seconds ago)."""
    old_time = int(time.time()) - 90000 # 25 hours ago
    payload = make_telegram_payload(auth_date=old_time)
    is_valid, err_msg = verify_telegram_authorization(payload)
    assert is_valid is False
    assert "expired" in err_msg.lower()

def test_telegram_login_api_success():
    """Verify POST /api/auth/telegram creates session for valid Telegram payload."""
    payload = make_telegram_payload(user_id=987654321, username="tg_user_test")
    res = client.post("/api/auth/telegram", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "Success"
    assert "session_token" in data
    assert data["user"]["telegram_id"] == "987654321"

def test_telegram_login_api_invalid_signature():
    """Verify POST /api/auth/telegram rejects invalid signatures with HTTP 401."""
    payload = make_telegram_payload()
    payload["hash"] = "badhash"
    res = client.post("/api/auth/telegram", json=payload)
    assert res.status_code == 401
    assert "failed" in res.json()["detail"].lower()

def test_telegram_link_account_api():
    """Verify linking Telegram account to an active user session."""
    repo = global_auth_service.repo
    user = repo.create_user("link_tester@yartrader.app", password_hash="hash123", name="Link Tester")
    token = global_auth_service.create_session(user)

    tg_payload = make_telegram_payload(user_id=555666777, username="linked_tg")
    res = client.post(f"/api/user/link-telegram?session_token={token}", json=tg_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "Success"
    assert data["telegram_id"] == "555666777"

    # Verify persistent repository binding
    updated_user = repo.get_user_by_email("link_tester@yartrader.app")
    assert updated_user["telegram_id"] == "555666777"

def test_telegram_link_duplicate_identity_rejection():
    """Verify linking rejection when Telegram ID belongs to another existing user."""
    repo = global_auth_service.repo
    user1 = repo.create_user("owner1@yartrader.app", password_hash="hash123", name="Owner 1")
    repo.link_telegram_account("owner1@yartrader.app", telegram_id="999888777")

    user2 = repo.create_user("owner2@yartrader.app", password_hash="hash123", name="Owner 2")
    token2 = global_auth_service.create_session(user2)

    # Attempt to link user1's Telegram ID (999888777) to user2
    payload = make_telegram_payload(user_id=999888777, username="stolen_tg")
    res = client.post(f"/api/user/link-telegram?session_token={token2}", json=payload)
    assert res.status_code == 400
    assert "already linked" in res.json()["detail"].lower()
