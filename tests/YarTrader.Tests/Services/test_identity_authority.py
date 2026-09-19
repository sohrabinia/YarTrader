import pytest
import time
from src.Application.Dashboard.identity_authority import IdentityAuthority, IdentityKeyManager
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Application.Dashboard.auth_service import AuthService
from src.Infrastructure.exceptions import ValidationException

def test_identity_key_manager_jwks_export(tmp_path):
    key_file = str(tmp_path / "identity_keys.json")
    km = IdentityKeyManager(keypath=key_file)
    jwks = km.get_jwks()
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert key["use"] == "sig"
    assert "n" in key and "e" in key

def test_issue_and_verify_valid_identity_assertion(tmp_path):
    key_file = str(tmp_path / "identity_keys.json")
    km = IdentityKeyManager(keypath=key_file)
    authority = IdentityAuthority(key_manager=km)

    token = authority.issue_identity_assertion(
        user_id="usr-12345",
        google_sub="google-sub-999",
        owner_id="usr-12345",
        workspace_id="yartrader-main",
        audience="yaroperator",
        ttl_seconds=3600
    )
    assert isinstance(token, str) and len(token) > 20

    verified = authority.verify_identity_assertion(
        token=token,
        expected_audience="yaroperator",
        expected_issuer="https://yartrader.app/auth"
    )

    assert verified["sub"] == "usr-12345"
    assert verified["owner_id"] == "usr-12345"
    assert verified["workspace_id"] == "yartrader-main"
    assert verified["google_sub"] == "google-sub-999"
    assert verified["aud"] == "yaroperator"
    assert verified["iss"] == "https://yartrader.app/auth"

def test_verify_assertion_invalid_signature(tmp_path):
    key_file_1 = str(tmp_path / "keys1.json")
    key_file_2 = str(tmp_path / "keys2.json")

    authority_1 = IdentityAuthority(key_manager=IdentityKeyManager(keypath=key_file_1))
    authority_2 = IdentityAuthority(key_manager=IdentityKeyManager(keypath=key_file_2))

    token = authority_1.issue_identity_assertion(user_id="usr-123")

    # Attempting to verify token issued by authority_1 using authority_2 public keys
    with pytest.raises(ValidationException) as exc:
        authority_2.verify_identity_assertion(token)
    assert "Unknown signing key ID" in str(exc.value) or "verification failed" in str(exc.value)

def test_verify_assertion_expired(tmp_path):
    km = IdentityKeyManager(keypath=str(tmp_path / "keys.json"))
    authority = IdentityAuthority(key_manager=km)

    token = authority.issue_identity_assertion(user_id="usr-123", ttl_seconds=-10)
    with pytest.raises(ValidationException) as exc:
        authority.verify_identity_assertion(token)
    assert "expired" in str(exc.value).lower()

def test_verify_assertion_invalid_audience(tmp_path):
    km = IdentityKeyManager(keypath=str(tmp_path / "keys.json"))
    authority = IdentityAuthority(key_manager=km)

    token = authority.issue_identity_assertion(user_id="usr-123", audience="yaroperator")
    with pytest.raises(ValidationException) as exc:
        authority.verify_identity_assertion(token, expected_audience="other_service")
    assert "audience" in str(exc.value).lower()

def test_verify_assertion_invalid_issuer(tmp_path):
    km = IdentityKeyManager(keypath=str(tmp_path / "keys.json"))
    authority = IdentityAuthority(key_manager=km)

    token = authority.issue_identity_assertion(user_id="usr-123")
    with pytest.raises(ValidationException) as exc:
        authority.verify_identity_assertion(token, expected_issuer="https://fake-issuer.com")
    assert "issuer" in str(exc.value).lower()

def test_immutable_user_id_and_email_change(tmp_path):
    db_file = str(tmp_path / "auth.json")
    repo = AuthRepository(filepath=db_file)

    # 1. Link social account with initial email
    user1 = repo.link_social_account(email="alice@example.com", provider="google", provider_id="sub-alice-001")
    uid1 = user1["user_id"]
    assert uid1.startswith("usr-")
    assert user1["google_sub"] == "sub-alice-001"

    # 2. Same Google sub with NEW email address MUST map to the SAME user_id
    user2 = repo.link_social_account(email="alice_new_email@example.com", provider="google", provider_id="sub-alice-001")
    assert user2["user_id"] == uid1
    assert user2["email"] == "alice_new_email@example.com"
    assert repo.get_user_by_google_sub("sub-alice-001")["user_id"] == uid1

def test_client_cannot_control_user_id_or_owner_id(tmp_path):
    db_file = str(tmp_path / "auth.json")
    repo = AuthRepository(filepath=db_file)
    service = AuthService(repo=repo)

    user = repo.link_social_account(email="bob@example.com", provider="google", provider_id="sub-bob-002")
    session_token = service.create_session(user)
    session = service.validate_session(session_token)

    assert session["user_id"] == user["user_id"]
    assert session["owner_id"] == user["owner_id"]
    assert session["workspace_id"] == user["workspace_id"]
    assert session["user_id"] != "client-chosen-admin-id"
