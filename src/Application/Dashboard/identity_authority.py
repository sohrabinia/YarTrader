import os
import json
import time
import base64
import threading
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
from src.Infrastructure.exceptions import ValidationException

ISSUER_URI = "https://yartrader.app/auth"
DEFAULT_AUDIENCE = "yaroperator"

def _int_to_base64url(val: int) -> str:
    """Converts a long integer to a base64url encoded string without padding."""
    hex_str = f"{val:x}"
    if len(hex_str) % 2 == 1:
        hex_str = "0" + hex_str
    raw_bytes = bytes.fromhex(hex_str)
    b64 = base64.b64encode(raw_bytes).decode('utf-8')
    return b64.replace('+', '-').replace('/', '_').rstrip('=')


class IdentityKeyManager:
    """
    Manages persistent RS256 key pair generation, key storage, rotation, and JWKS exporting.
    Saves private keys securely to runtime_logs/identity_keys.json.
    """
    def __init__(self, keypath: str = "runtime_logs/identity_keys.json") -> None:
        self.keypath = keypath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.keypath), exist_ok=True)
        self._ensure_keys()

    def _ensure_keys(self) -> None:
        with self.lock:
            if not os.path.exists(self.keypath):
                self._generate_and_save_new_key(kid="key-v1")

    def _generate_and_save_new_key(self, kid: str) -> Dict[str, Any]:
        with self.lock:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            pem_private = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')

            keys_data = self._load_keys_file()
            keys_data[kid] = {
                "kid": kid,
                "private_pem": pem_private,
                "created_at": time.time(),
                "active": True
            }
            # Set older keys active flag to False if generating new primary key
            for k, v in keys_data.items():
                if k != kid:
                    v["active"] = False

            self._save_keys_file(keys_data)
            return keys_data[kid]

    def _load_keys_file(self) -> Dict[str, Any]:
        with self.lock:
            if os.path.exists(self.keypath):
                try:
                    with open(self.keypath, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return {}

    def _save_keys_file(self, data: Dict[str, Any]) -> None:
        with self.lock:
            tmp = self.keypath + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp, self.keypath)

    def get_active_key(self) -> Dict[str, Any]:
        with self.lock:
            keys_data = self._load_keys_file()
            for kid, key_info in keys_data.items():
                if key_info.get("active"):
                    return key_info
            # Fallback if no key is active
            if keys_data:
                first_kid = next(iter(keys_data))
                return keys_data[first_kid]
            return self._generate_and_save_new_key(kid="key-v1")

    def get_key_by_kid(self, kid: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            keys_data = self._load_keys_file()
            return keys_data.get(kid)

    def rotate_keys(self) -> Dict[str, Any]:
        with self.lock:
            new_kid = f"key-v{int(time.time())}"
            return self._generate_and_save_new_key(kid=new_kid)

    def get_jwks(self) -> Dict[str, Any]:
        """Exports public key components formatted as a standard JWKS object."""
        with self.lock:
            keys_data = self._load_keys_file()
            jwk_list = []
            for kid, key_info in keys_data.items():
                pem = key_info.get("private_pem", "")
                if not pem:
                    continue
                try:
                    priv_key = serialization.load_pem_private_key(
                        pem.encode('utf-8'),
                        password=None,
                        backend=default_backend()
                    )
                    pub_key = priv_key.public_key()
                    numbers = pub_key.public_numbers()
                    jwk_list.append({
                        "kty": "RSA",
                        "alg": "RS256",
                        "use": "sig",
                        "kid": kid,
                        "n": _int_to_base64url(numbers.n),
                        "e": _int_to_base64url(numbers.e)
                    })
                except Exception:
                    continue
            return {"keys": jwk_list}


class IdentityAuthority:
    """
    Authoritative Identity Authority for issuing and verifying cryptographically signed assertions.
    """
    def __init__(self, key_manager: Optional[IdentityKeyManager] = None) -> None:
        self.key_manager = key_manager or IdentityKeyManager()

    def issue_identity_assertion(
        self,
        user_id: str,
        google_sub: Optional[str] = None,
        owner_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        audience: str = DEFAULT_AUDIENCE,
        ttl_seconds: float = 3600.0,
        amr: Optional[list] = None
    ) -> str:
        """
        Issues an RS256-signed identity assertion JWT containing canonical immutable subject fields.
        Fails closed on missing user_id.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationException("Identity assertion requires a non-empty user_id.")

        active_key = self.key_manager.get_active_key()
        kid = active_key["kid"]
        pem_str = active_key["private_pem"]

        now = time.time()
        payload = {
            "iss": ISSUER_URI,
            "sub": user_id,
            "aud": audience,
            "iat": int(now),
            "exp": int(now + ttl_seconds),
            "owner_id": owner_id or user_id,
            "workspace_id": workspace_id or "yartrader-main",
            "google_sub": google_sub,
            "amr": amr or ["google_oidc"]
        }

        headers = {"kid": kid}
        token = jwt.encode(payload, pem_str, algorithm="RS256", headers=headers)
        return token

    def verify_identity_assertion(
        self,
        token: str,
        expected_audience: str = DEFAULT_AUDIENCE,
        expected_issuer: str = ISSUER_URI,
        jwks: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cryptographically verifies an identity assertion JWT using public key JWKS or KeyManager.
        Enforces signature, issuer, audience, and expiry validation. Fails closed.
        """
        if not token or not isinstance(token, str):
            raise ValidationException("Identity assertion token must be a non-empty string.")

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise ValidationException("Identity assertion header missing 'kid'.")

            pub_key = None
            # If explicit JWKS is provided (e.g. downstream consumer), resolve public key from JWKS
            if jwks and isinstance(jwks, dict) and "keys" in jwks:
                from src.Application.Dashboard.oidc_validator import get_public_key_from_jwks
                pub_key = get_public_key_from_jwks(jwks.get("keys", []), kid)
            else:
                key_info = self.key_manager.get_key_by_kid(kid)
                if not key_info:
                    raise ValidationException(f"Unknown signing key ID '{kid}'.")

                pem_str = key_info["private_pem"]
                priv_key = serialization.load_pem_private_key(
                    pem_str.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                pub_key = priv_key.public_key()

            decoded = jwt.decode(
                token,
                pub_key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=expected_issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "require": ["exp", "iss", "aud", "sub", "owner_id", "workspace_id"]
                }
            )
            return decoded
        except jwt.ExpiredSignatureError as e:
            raise ValidationException(f"Identity assertion has expired: {str(e)}")
        except jwt.InvalidSignatureError as e:
            raise ValidationException(f"Identity assertion signature verification failed: {str(e)}")
        except jwt.InvalidAudienceError as e:
            raise ValidationException(f"Identity assertion audience mismatch: {str(e)}")
        except jwt.InvalidIssuerError as e:
            raise ValidationException(f"Identity assertion issuer mismatch: {str(e)}")
        except jwt.InvalidTokenError as e:
            raise ValidationException(f"Identity assertion error: {str(e)}")
        except Exception as e:
            if isinstance(e, ValidationException):
                raise e
            raise ValidationException(f"Unexpected error verifying identity assertion: {str(e)}")


# Shared singleton instance
global_identity_authority = IdentityAuthority()
