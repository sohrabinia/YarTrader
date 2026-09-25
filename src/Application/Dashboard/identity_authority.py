import os
import json
import time
import base64
import hashlib
from typing import Dict, Any, Optional
import jwt
from src.Infrastructure.exceptions import ValidationException
from src.Application.Dashboard.cng_key_manager import CNGKeyManager

ISSUER_URI = "https://yartrader.app/auth"
DEFAULT_AUDIENCE = "yaroperator"

class IdentityAuthority:
    """
    Authoritative Identity Authority for issuing and verifying cryptographically signed assertions.
    Delegates RS256 token signing strictly to Windows CNG Key Storage Provider (CNGKeyManager).
    Fails closed on missing CNG key containers or unsupported platforms without local file/software fallback.
    """
    def __init__(self, cng_manager: Optional[CNGKeyManager] = None) -> None:
        self.cng_manager = cng_manager or CNGKeyManager()

    def issue_identity_assertion(
        self,
        user_id: str,
        google_sub: Optional[str] = None,
        owner_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        audience: str = DEFAULT_AUDIENCE,
        ttl_seconds: float = 3600.0,
        amr: Optional[list] = None,
        key_name: Optional[str] = None
    ) -> str:
        """
        Issues an RS256-signed identity assertion JWT containing canonical immutable subject fields.
        Private key operations are executed inside Windows CNG KSP.
        Fails closed on missing user_id or inaccessible CNG key container without fallback.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationException("Identity assertion requires a non-empty user_id.")

        target_kid = key_name or self.cng_manager.key_name

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

        # 1. Encode JWT header & payload without signature
        header_dict = {"alg": "RS256", "typ": "JWT", "kid": target_kid}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header_dict, separators=(',', ':')).encode('utf-8')).decode('utf-8').rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8')).decode('utf-8').rstrip('=')

        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')

        # 2. Compute SHA-256 digest
        digest = hashlib.sha256(signing_input).digest()

        # 3. Sign SHA-256 digest inside CNG KSP
        sig_bytes = self.cng_manager.sign_hash(digest_bytes=digest, key_name=target_kid)
        sig_b64 = base64.urlsafe_b64encode(sig_bytes).decode('utf-8').rstrip('=')

        token = f"{header_b64}.{payload_b64}.{sig_b64}"
        return token

    def get_public_jwks(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Exposes ONLY public key components (JWKS) exported from Windows CNG."""
        jwk = self.cng_manager.export_public_key_params(key_name=key_name)
        return {"keys": [jwk]}

    def verify_identity_assertion(
        self,
        token: str,
        expected_audience: str = DEFAULT_AUDIENCE,
        expected_issuer: str = ISSUER_URI,
        jwks: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cryptographically verifies an identity assertion JWT against public JWKS.
        Enforces signature, issuer, audience, and expiry validation. Fails closed.
        """
        if not token or not isinstance(token, str):
            raise ValidationException("Identity assertion token must be a non-empty string.")

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise ValidationException("Identity assertion header missing 'kid'.")

            # Resolve public key from provided JWKS or export public key from CNG
            target_jwks = jwks
            if not target_jwks:
                target_jwks = self.get_public_jwks(key_name=kid)

            from src.Application.Dashboard.oidc_validator import get_public_key_from_jwks
            pub_key = get_public_key_from_jwks(target_jwks.get("keys", []), kid)

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


# Shared global singleton
global_identity_authority = IdentityAuthority()
