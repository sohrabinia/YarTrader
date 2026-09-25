import sys
import pytest
import hashlib
from unittest.mock import MagicMock
from src.Application.Dashboard.cng_key_manager import CNGKeyManager
from src.Infrastructure.exceptions import ValidationException

def test_non_windows_platform_rejection(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    cng_mgr = CNGKeyManager()
    assert cng_mgr.is_available() is False

    with pytest.raises(ValidationException) as exc_info:
        cng_mgr.ensure_key_exists()
    assert "Windows CNG KSP requires Windows platform execution" in str(exc_info.value)


def test_cng_signing_boundary_mocked_win32_call(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    cng_mgr = CNGKeyManager(key_name="Test-CNG-Key")

    mock_ncrypt = MagicMock()
    mock_ncrypt.NCryptOpenStorageProvider.return_value = 0
    mock_ncrypt.NCryptOpenKey.return_value = 0 # key exists
    mock_ncrypt.NCryptSignHash.return_value = 0
    mock_ncrypt.NCryptExportKey.return_value = 0
    mock_ncrypt.NCryptFreeObject.return_value = 0

    cng_mgr._mock_ncrypt = mock_ncrypt

    key_res = cng_mgr.ensure_key_exists()
    assert key_res == "Test-CNG-Key"

    dummy_digest = hashlib.sha256(b"test-payload").digest()
    sig = cng_mgr.sign_hash(dummy_digest)
    assert isinstance(sig, bytes)


@pytest.mark.skipif(sys.platform != "win32", reason="Requires real Windows OS with Microsoft Software Key Storage Provider")
def test_real_windows_cng_ksp_integration():
    """
    Real Windows CNG/KSP integration test executing directly on Win32 (Windows Server 2022).
    Exercises unmocked Microsoft Software Key Storage Provider, persisted non-exportable key creation,
    explicit export policy property = 0, private key export rejection, RS256 hash signing,
    public JWKS parameter extraction, and signature verification via cryptography.
    """
    import ctypes
    from ctypes import wintypes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
    import base64

    test_key_name = "YarTrader-Integration-Test-Key-v1"
    cng_mgr = CNGKeyManager(key_name=test_key_name)

    # 1. Ensure Key Exists (Creates persisted key in MS Software KSP with Export Policy = 0)
    created_key = cng_mgr.ensure_key_exists(key_name=test_key_name, key_size=2048)
    assert created_key == test_key_name

    ncrypt = ctypes.windll.ncrypt
    hProvider = wintypes.HANDLE()
    status = ncrypt.NCryptOpenStorageProvider(
        ctypes.byref(hProvider),
        ctypes.c_wchar_p("Microsoft Software Key Storage Provider"),
        0
    )
    assert status == 0

    hKey = wintypes.HANDLE()
    status = ncrypt.NCryptOpenKey(
        hProvider,
        ctypes.byref(hKey),
        ctypes.c_wchar_p(test_key_name),
        0,
        0
    )
    assert status == 0

    # 2. Assert PRIVATEBLOB Export Fails (Proves key is non-exportable)
    blob_type = ctypes.c_wchar_p("PRIVATEBLOB")
    blob_len = wintypes.DWORD(0)
    export_status = ncrypt.NCryptExportKey(
        hKey,
        0,
        blob_type,
        None,
        None,
        0,
        ctypes.byref(blob_len),
        0
    )
    # Status MUST be non-zero (NCRYPT_E_NOT_SUPPORTED = 0x80090029 or NTE_BAD_KEY)
    assert export_status != 0, "SECURITY VIOLATION: CNG Private Key export succeeded when it MUST fail!"

    # 3. Perform Actual CNG Hash Signing
    payload = b"YarTrader Identity Authority Test Signature Payload"
    digest = hashlib.sha256(payload).digest()
    signature = cng_mgr.sign_hash(digest, key_name=test_key_name)
    assert isinstance(signature, bytes) and len(signature) == 256

    # 4. Export Public Key Params
    pub_params = cng_mgr.export_public_key_params(key_name=test_key_name)
    assert pub_params["kty"] == "RSA"
    assert pub_params["alg"] == "RS256"
    assert "n" in pub_params and "e" in pub_params

    # Helper function to decode base64url to int
    def b64url_to_int(b64_str: str) -> int:
        rem = len(b64_str) % 4
        if rem == 2:
            b64_str += "=="
        elif rem == 3:
            b64_str += "="
        raw = base64.b64decode(b64_str.replace("-", "+").replace("_", "/"))
        return int.from_bytes(raw, byteorder="big")

    n_int = b64url_to_int(pub_params["n"])
    e_int = b64url_to_int(pub_params["e"])

    # 5. Verify Signature using Cryptography Public Key
    public_key = RSAPublicNumbers(e=e_int, n=n_int).public_key()
    public_key.verify(
        signature,
        payload,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # 6. Deterministic Test Key Cleanup
    # NCryptDeleteKey frees and deletes key container
    ncrypt.NCryptDeleteKey(hKey, 0)
    ncrypt.NCryptFreeObject(hProvider)
