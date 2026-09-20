import os
import sys
import base64
import platform
from typing import Dict, Any, Optional
from src.Infrastructure.exceptions import ValidationException

MS_KEY_STORAGE_PROVIDER = "Microsoft Software Key Storage Provider"
DEFAULT_KEY_NAME_PREFIX = "YarTrader-Identity-Key"

def _int_to_base64url(val: int) -> str:
    """Converts a long integer to a base64url encoded string without padding."""
    hex_str = f"{val:x}"
    if len(hex_str) % 2 == 1:
        hex_str = "0" + hex_str
    raw_bytes = bytes.fromhex(hex_str)
    b64 = base64.b64encode(raw_bytes).decode('utf-8')
    return b64.replace('+', '-').replace('/', '_').rstrip('=')


class CNGKeyManager:
    """
    Windows Cryptography Next Generation (CNG) Key Storage Provider (KSP) Manager.
    Interfaces directly with Win32 ncrypt.dll to manage non-exportable RS256 RSA keys inside MS KSP.
    Strictly fails closed on non-Windows platforms or missing key containers without software/file fallbacks.
    """
    def __init__(self, key_name: str = "YarTrader-Identity-Key-v1") -> None:
        self.key_name = key_name
        self.provider_name = MS_KEY_STORAGE_PROVIDER
        self.is_windows = platform.system() == "Windows"

    def is_available(self) -> bool:
        return self.is_windows

    def ensure_key_exists(self, key_name: Optional[str] = None, key_size: int = 2048) -> str:
        """
        Ensures a non-exportable RSA key container exists in Microsoft Software Key Storage Provider.
        Fails closed on non-Windows platform.
        """
        target_key = key_name or self.key_name
        if not self.is_windows:
            raise ValidationException("Windows CNG KSP requires Windows platform execution.")

        import ctypes
        from ctypes import wintypes

        ncrypt = getattr(ctypes, "windll", None).ncrypt if hasattr(ctypes, "windll") else getattr(self, "_mock_ncrypt", None)
        if not ncrypt:
            raise ValidationException("Windows CNG DLL ncrypt is unavailable on this platform.")

        # 1. Open Storage Provider
        hProvider = wintypes.HANDLE()
        status = ncrypt.NCryptOpenStorageProvider(
            ctypes.byref(hProvider),
            ctypes.c_wchar_p(self.provider_name),
            0
        )
        if status != 0:
            raise ValidationException(f"CNG Error: NCryptOpenStorageProvider failed with status 0x{status:08X}")

        # 2. Try Opening existing Key Container
        hKey = wintypes.HANDLE()
        status = ncrypt.NCryptOpenKey(
            hProvider,
            ctypes.byref(hKey),
            ctypes.c_wchar_p(target_key),
            0,
            0
        )

        if status == 0:
            # Key already exists
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            return target_key

        # 3. Key does not exist -> Create new non-exportable RSA key
        # BCRYPT_RSA_ALGORITHM = "RSA"
        status = ncrypt.NCryptCreatePersistedKey(
            hProvider,
            ctypes.byref(hKey),
            ctypes.c_wchar_p("RSA"),
            ctypes.c_wchar_p(target_key),
            0,
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptCreatePersistedKey failed with status 0x{status:08X}")

        # Set Key Length property (e.g. 2048)
        # NCRYPT_LENGTH_PROPERTY = "Length"
        key_size_bytes = (ctypes.c_ulong)(key_size)
        status = ncrypt.NCryptSetProperty(
            hKey,
            ctypes.c_wchar_p("Length"),
            ctypes.byref(key_size_bytes),
            ctypes.sizeof(key_size_bytes),
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptSetProperty Length failed with status 0x{status:08X}")

        # Explicitly set Export Policy = 0 (NCRYPT_ALLOW_EXPORT_FLAG = 0 -> Strictly Non-Exportable) BEFORE Finalizing Key
        # NCRYPT_EXPORT_POLICY_PROPERTY = L"ExportPolicy"
        export_policy = (ctypes.c_ulong)(0)
        status = ncrypt.NCryptSetProperty(
            hKey,
            ctypes.c_wchar_p("ExportPolicy"),
            ctypes.byref(export_policy),
            ctypes.sizeof(export_policy),
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptSetProperty ExportPolicy failed with status 0x{status:08X}")

        # Finalize Key (key is persisted non-exportable with explicit policy = 0)
        status = ncrypt.NCryptFinalizeKey(hKey, 0)
        if status != 0:
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptFinalizeKey failed with status 0x{status:08X}")

        ncrypt.NCryptFreeObject(hKey)
        ncrypt.NCryptFreeObject(hProvider)
        return target_key

    def sign_hash(self, digest_bytes: bytes, key_name: Optional[str] = None) -> bytes:
        """
        Signs a pre-computed SHA-256 digest using RS256 (PKCS#1 v1.5 with SHA256) inside Windows CNG.
        Private key material NEVER leaves CNG memory or enters application heap.
        Fails closed.
        """
        target_key = key_name or self.key_name
        if not self.is_windows:
            raise ValidationException("Windows CNG KSP requires Windows platform execution.")

        if not digest_bytes or len(digest_bytes) != 32:
            raise ValidationException("RS256 signing requires a valid 32-byte SHA-256 digest.")

        import ctypes
        from ctypes import wintypes

        ncrypt = getattr(ctypes, "windll", None).ncrypt if hasattr(ctypes, "windll") else getattr(self, "_mock_ncrypt", None)
        if not ncrypt:
            raise ValidationException("Windows CNG DLL ncrypt is unavailable on this platform.")

        class BCRYPT_PKCS1_PADDING_INFO(ctypes.Structure):
            _fields_ = [("pszAlgId", ctypes.c_wchar_p)]

        hProvider = wintypes.HANDLE()
        status = ncrypt.NCryptOpenStorageProvider(
            ctypes.byref(hProvider),
            ctypes.c_wchar_p(self.provider_name),
            0
        )
        if status != 0:
            raise ValidationException(f"CNG Error: NCryptOpenStorageProvider failed with status 0x{status:08X}")

        hKey = wintypes.HANDLE()
        status = ncrypt.NCryptOpenKey(
            hProvider,
            ctypes.byref(hKey),
            ctypes.c_wchar_p(target_key),
            0,
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: Key container '{target_key}' not found or inaccessible (status 0x{status:08X}).")

        padding_info = BCRYPT_PKCS1_PADDING_INFO(ctypes.c_wchar_p("SHA256"))
        # BCRYPT_PAD_PKCS1 = 0x00000002
        flags = 0x00000002

        digest_buf = (ctypes.c_ubyte * len(digest_bytes)).from_buffer_copy(digest_bytes)
        sig_len = wintypes.DWORD(0)

        # First call to query signature buffer size
        status = ncrypt.NCryptSignHash(
            hKey,
            ctypes.byref(padding_info),
            ctypes.byref(digest_buf),
            len(digest_bytes),
            None,
            0,
            ctypes.byref(sig_len),
            flags
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptSignHash buffer query failed with status 0x{status:08X}")

        sig_buf = (ctypes.c_ubyte * sig_len.value)()
        status = ncrypt.NCryptSignHash(
            hKey,
            ctypes.byref(padding_info),
            ctypes.byref(digest_buf),
            len(digest_bytes),
            ctypes.byref(sig_buf),
            sig_len.value,
            ctypes.byref(sig_len),
            flags
        )

        ncrypt.NCryptFreeObject(hKey)
        ncrypt.NCryptFreeObject(hProvider)

        if status != 0:
            raise ValidationException(f"CNG Error: NCryptSignHash failed with status 0x{status:08X}")

        return bytes(sig_buf)

    def export_public_key_params(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Exports ONLY the public key components (Modulus 'n' and Exponent 'e') from CNG.
        Fails closed.
        """
        target_key = key_name or self.key_name
        if not self.is_windows:
            raise ValidationException("Windows CNG KSP requires Windows platform execution.")

        import ctypes
        from ctypes import wintypes

        ncrypt = getattr(ctypes, "windll", None).ncrypt if hasattr(ctypes, "windll") else getattr(self, "_mock_ncrypt", None)
        if not ncrypt:
            raise ValidationException("Windows CNG DLL ncrypt is unavailable on this platform.")

        hProvider = wintypes.HANDLE()
        status = ncrypt.NCryptOpenStorageProvider(
            ctypes.byref(hProvider),
            ctypes.c_wchar_p(self.provider_name),
            0
        )
        if status != 0:
            raise ValidationException(f"CNG Error: NCryptOpenStorageProvider failed with status 0x{status:08X}")

        hKey = wintypes.HANDLE()
        status = ncrypt.NCryptOpenKey(
            hProvider,
            ctypes.byref(hKey),
            ctypes.c_wchar_p(target_key),
            0,
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: Key container '{target_key}' not found or inaccessible.")

        # BCRYPT_RSAPUBLIC_BLOB = "RSAPUBLICBLOB"
        blob_type = ctypes.c_wchar_p("RSAPUBLICBLOB")
        blob_len = wintypes.DWORD(0)

        status = ncrypt.NCryptExportKey(
            hKey,
            0,
            blob_type,
            None,
            None,
            0,
            ctypes.byref(blob_len),
            0
        )
        if status != 0:
            ncrypt.NCryptFreeObject(hKey)
            ncrypt.NCryptFreeObject(hProvider)
            raise ValidationException(f"CNG Error: NCryptExportKey public length query failed with status 0x{status:08X}")

        blob_buf = (ctypes.c_ubyte * blob_len.value)()
        status = ncrypt.NCryptExportKey(
            hKey,
            0,
            blob_type,
            None,
            ctypes.byref(blob_buf),
            blob_len.value,
            ctypes.byref(blob_len),
            0
        )

        ncrypt.NCryptFreeObject(hKey)
        ncrypt.NCryptFreeObject(hProvider)

        if status != 0:
            raise ValidationException(f"CNG Error: NCryptExportKey public blob failed with status 0x{status:08X}")

        # Parse BCRYPT_RSAKEY_BLOB structure
        # Header (24 bytes): Magic (4B), BitLength (4B), cbPublicExp (4B), cbModulus (4B), cbPrime1 (4B), cbPrime2 (4B)
        blob_bytes = bytes(blob_buf)
        if len(blob_bytes) < 24:
            raise ValidationException("CNG Error: Invalid RSA public blob length.")

        import struct
        magic, bit_len, cb_exp, cb_mod, cb_p1, cb_p2 = struct.unpack("<4sIIIII", blob_bytes[:24])
        if magic != b"RSA1":
            raise ValidationException("CNG Error: Invalid RSA public blob magic.")

        exp_bytes = blob_bytes[24 : 24 + cb_exp]
        mod_bytes = blob_bytes[24 + cb_exp : 24 + cb_exp + cb_mod]

        e_int = int.from_bytes(exp_bytes, byteorder="big")
        n_int = int.from_bytes(mod_bytes, byteorder="big")

        return {
            "kid": target_key,
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": _int_to_base64url(n_int),
            "e": _int_to_base64url(e_int)
        }
