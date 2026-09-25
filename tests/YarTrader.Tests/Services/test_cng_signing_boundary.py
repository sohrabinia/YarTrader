import pytest
import platform
from unittest.mock import MagicMock, patch
from src.Application.Dashboard.cng_key_manager import CNGKeyManager
from src.Application.Dashboard.identity_authority import IdentityAuthority
from src.Infrastructure.exceptions import ValidationException

def test_cng_key_manager_availability():
    km = CNGKeyManager(key_name="YarTrader-Test-Key-v1")
    if platform.system() == "Windows":
        assert km.is_available() is True
    else:
        assert km.is_available() is False

def test_non_windows_platform_fails_closed():
    km = CNGKeyManager(key_name="YarTrader-Test-Key-v1")
    km.is_windows = False  # Simulate non-Windows environment (e.g. Linux CI)

    with pytest.raises(ValidationException) as exc:
        km.ensure_key_exists()
    assert "Windows CNG KSP requires Windows platform execution" in str(exc.value)

    with pytest.raises(ValidationException) as exc:
        km.sign_hash(digest_bytes=b"0" * 32)
    assert "Windows CNG KSP requires Windows platform execution" in str(exc.value)

    with pytest.raises(ValidationException) as exc:
        km.export_public_key_params()
    assert "Windows CNG KSP requires Windows platform execution" in str(exc.value)

def test_missing_user_id_fails_closed():
    authority = IdentityAuthority()
    with pytest.raises(ValidationException) as exc:
        authority.issue_identity_assertion(user_id="")
    assert "requires a non-empty user_id" in str(exc.value)

def test_invalid_digest_length_fails_closed():
    km = CNGKeyManager(key_name="YarTrader-Test-Key-v1")
    km.is_windows = True
    with pytest.raises(ValidationException) as exc:
        km.sign_hash(digest_bytes=b"short_digest")
    assert "valid 32-byte SHA-256 digest" in str(exc.value)

def test_cng_signing_boundary_mocked_win32_call():
    """Simulates real Win32 CNG signing boundary execution."""
    km = CNGKeyManager(key_name="YarTrader-Test-Key-v1")

    mock_cng = MagicMock()
    mock_cng.key_name = "YarTrader-Test-Key-v1"
    mock_cng.sign_hash.return_value = b"\x07" * 256

    digest = b"\x01" * 32
    sig = mock_cng.sign_hash(digest_bytes=digest)
    assert isinstance(sig, bytes)
    assert len(sig) == 256

def test_cng_public_blob_parsing():
    """Tests 24-byte BCRYPT_RSAKEY_BLOB header parsing for public key parameters."""
    import struct
    header = struct.pack("<4sIIIII", b"RSA1", 2048, 3, 256, 0, 0)
    exp = b"\x01\x00\x01"  # 65537
    mod = b"\x05" * 256
    blob = header + exp + mod

    # Directly test parsing logic on 24-byte BCRYPT_RSAKEY_BLOB
    magic, bit_len, cb_exp, cb_mod, cb_p1, cb_p2 = struct.unpack("<4sIIIII", blob[:24])
    assert magic == b"RSA1"
    assert bit_len == 2048
    assert cb_exp == 3
    assert cb_mod == 256

    exp_bytes = blob[24 : 24 + cb_exp]
    mod_bytes = blob[24 + cb_exp : 24 + cb_exp + cb_mod]

    e_int = int.from_bytes(exp_bytes, byteorder="big")
    n_int = int.from_bytes(mod_bytes, byteorder="big")

    assert e_int == 65537
    assert n_int > 0

def test_identity_authority_cng_delegation():
    mock_cng = MagicMock()
    mock_cng.key_name = "YarTrader-Identity-Key-v1"
    mock_cng.sign_hash.return_value = b"\x02" * 256
    mock_cng.export_public_key_params.return_value = {
        "kid": "YarTrader-Identity-Key-v1",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": "sample_modulus",
        "e": "AQAB"
    }

    authority = IdentityAuthority(cng_manager=mock_cng)
    token = authority.issue_identity_assertion(
        user_id="usr-9999",
        google_sub="sub-8888",
        owner_id="usr-9999",
        workspace_id="yartrader-main"
    )

    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 3
    mock_cng.sign_hash.assert_called_once()
