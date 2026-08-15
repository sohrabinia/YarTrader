import os
import time
import base64
import requests
import jwt
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from src.Infrastructure.exceptions import ValidationException

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

# In-memory JWKS cache to avoid hitting Google/Apple on every request
_jwks_cache: Dict[str, Dict[str, Any]] = {
    "google": {"keys": [], "expires_at": 0.0},
    "apple": {"keys": [], "expires_at": 0.0}
}

def decode_base64url(s: str) -> bytes:
    """Safely decodes base64url encoded strings with appropriate padding."""
    s = s.replace("-", "+").replace("_", "/")
    rem = len(s) % 4
    if rem > 0:
        s += '=' * (4 - rem)
    return base64.b64decode(s.encode('utf-8'))

def get_public_key_from_jwks(jwks: list, kid: str):
    """Finds key in jwks list by kid and constructs a cryptography RSA public key object."""
    for key in jwks:
        if key.get("kid") == kid:
            n_b64 = key.get("n")
            e_b64 = key.get("e")
            if not n_b64 or not e_b64:
                raise ValueError("JWK key components 'n' or 'e' missing.")

            n = int.from_bytes(decode_base64url(n_b64), byteorder='big')
            e = int.from_bytes(decode_base64url(e_b64), byteorder='big')

            pub_numbers = rsa.RSAPublicNumbers(e, n)
            return pub_numbers.public_key(default_backend())
    raise ValueError(f"Key ID '{kid}' not found in JWKS.")

def fetch_jwks(provider: str, url: str) -> list:
    """Fetches JWKS keys from provider's endpoint with 1-hour cache expiration."""
    now = time.time()
    cached = _jwks_cache[provider]
    if cached["keys"] and now < cached["expires_at"]:
        return cached["keys"]

    try:
        resp = requests.get(url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        keys = data.get("keys", [])
        if keys:
            _jwks_cache[provider] = {
                "keys": keys,
                "expires_at": now + 3600.0  # cache for 1 hour
            }
            return keys
    except Exception as e:
        # If cache exists, extend its lifetime as fallback during outages
        if cached["keys"]:
            return cached["keys"]
        raise ValidationException(f"Failed to fetch JWKS keys from {provider.upper()} endpoint: {str(e)}")

    return []

def validate_social_token(token: str, provider: str) -> Dict[str, Any]:
    """
    Cryptographically validates Google or Apple OIDC ID token.
    Enforces signature verification, issuer validation, audience verification, and expiration.
    Fails closed on any discrepancy.
    """
    is_production = (os.environ.get("YARTRADER_ENV") == "production" or
                     os.environ.get("RG_ENV") == "production")

    # Fetch configured Client ID from settings or environment
    if provider == "google":
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        expected_issuers = ["accounts.google.com", "https://accounts.google.com"]
        jwks_url = GOOGLE_JWKS_URL
    elif provider == "apple":
        client_id = os.environ.get("APPLE_CLIENT_ID")
        expected_issuers = ["https://appleid.apple.com"]
        jwks_url = APPLE_JWKS_URL
    else:
        raise ValidationException(f"Unsupported social provider '{provider}'.")

    # In development/test mode, accept mock tokens prefixed with 'mock_token_' for test isolation
    if not is_production and token.startswith("mock_token_"):
        # Format of mock_token_: mock_token_<email>_<provider_id>_<name>
        parts = token.split("_")
        if len(parts) >= 5:
            # mock_token_email_provider_id_name
            email = parts[2]
            provider_id = parts[3]
            name = parts[4] if len(parts) > 4 else "Mock User"
            return {
                "email": email,
                "sub": provider_id,
                "name": name,
                "email_verified": True
            }
        raise ValidationException("Malformed mock token payload.")

    # Enforce config presence in production
    if is_production and not client_id:
        raise ValidationException(f"Production Configuration Error: Missing Client ID for {provider.upper()}.")

    try:
        # 1. Decode header to extract Key ID (kid)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise ValidationException("JWT header missing 'kid' (Key ID).")

        # 2. Fetch JWKS and get public key
        jwks = fetch_jwks(provider, jwks_url)
        public_key = get_public_key_from_jwks(jwks, kid)

        # 3. Decode and cryptographically verify JWT
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=client_id,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "require": ["exp", "iss", "aud", "sub"]
            }
        )

        # 4. Validate Issuer specifically
        iss = decoded.get("iss")
        if iss not in expected_issuers:
            raise ValidationException(f"Invalid JWT issuer '{iss}'. Expected one of {expected_issuers}.")

        # 5. Verify email is verified if present
        if "email_verified" in decoded and not decoded["email_verified"]:
            raise ValidationException("Email address in social token is not verified.")

        return decoded

    except jwt.ExpiredSignatureError as e:
        raise ValidationException(f"Social token has expired: {str(e)}")
    except jwt.InvalidSignatureError as e:
        raise ValidationException(f"Social token signature verification failed: {str(e)}")
    except jwt.InvalidTokenError as e:
        raise ValidationException(f"Social token validation error: {str(e)}")
    except Exception as e:
        if isinstance(e, ValidationException):
            raise e
        raise ValidationException(f"Unexpected token validation error: {str(e)}")
