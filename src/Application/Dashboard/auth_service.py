import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.Application.Dashboard.auth_repo import AuthRepository

class AuthService:
    """
    Production-grade Authentication and Session/Token Management service.
    Implements PBKDF2 password hashing, cryptographic token generation, and account recovery.
    """
    def __init__(self, repo: AuthRepository, secret_key: str = "tradeyar-secret-key-993", session_ttl_sec: int = 86400) -> None:
        self.repo = repo
        self.secret_key = secret_key
        self.session_ttl_sec = session_ttl_sec
        # Memory-cached active sessions: token -> {email, expires_at}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hashes password securely using PBKDF2-HMAC-SHA256."""
        if salt is None:
            salt = secrets.token_bytes(16)
        # Use 100,000 iterations for highly secure hashing without extra dependencies
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return f"{salt.hex()}:{pwd_hash.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verifies given password against the stored salt:hash format."""
        try:
            salt_hex, hash_hex = stored_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            expected_pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
            return secrets.compare_digest(expected_pwd_hash.hex(), hash_hex)
        except Exception:
            return False

    def register_user(self, email: str, password: str, role: str = "USER") -> Dict[str, Any]:
        """Registers a new user on the platform. Default role is 'USER'."""
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("Invalid email address format.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        if role not in ("USER", "PRO", "PREMIUM", "ADMIN"):
            raise ValueError(f"Invalid user role registration requested: {role}")

        existing = self.repo.get_user(email_clean)
        if existing:
            raise ValueError("Email address is already registered.")

        # Create production user schema
        user_record = {
            "email": email_clean,
            "password_hash": self._hash_password(password),
            "created_at": datetime.now().isoformat(),
            "status": "ACTIVE",
            "role": role,
            "subscription_plan": role if role != "ADMIN" else "PREMIUM",
            "subscription_start": datetime.now().isoformat() if role != "USER" else None,
            "subscription_end": (datetime.now() + timedelta(days=365)).isoformat() if role != "USER" else None,
            "watchlist": ["XAUUSD", "EURUSD"],
            "saved_analyses": [],
            "notifications": [],
            "recovery_code": None
        }
        self.repo.save_user(user_record)
        return user_record

    def authenticate_user(self, email: str, password: str) -> Optional[str]:
        """Authenticates a user and returns a cryptographically secure session token."""
        email_clean = email.strip().lower()
        user = self.repo.get_user(email_clean)
        if not user or user.get("status") != "ACTIVE":
            return None

        if self._verify_password(password, user.get("password_hash", "")):
            # Generate a highly secure session token
            token = secrets.token_hex(32)
            expires_at = datetime.now() + timedelta(seconds=self.session_ttl_sec)
            self._active_sessions[token] = {
                "email": email_clean,
                "expires_at": expires_at
            }
            return token
        return None

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validates session token and returns associated user details if session is active."""
        if not token:
            return None
        session = self._active_sessions.get(token)
        if not session:
            return None

        if datetime.now() > session["expires_at"]:
            # Expired session
            del self._active_sessions[token]
            return None

        # Return full live user details from repository
        return self.repo.get_user(session["email"])

    def logout_user(self, token: str) -> bool:
        """Revokes an active session token."""
        if token in self._active_sessions:
            del self._active_sessions[token]
            return True
        return False

    def generate_password_recovery_code(self, email: str) -> Optional[str]:
        """Generates a temporary numerical recovery code to recover the account."""
        email_clean = email.strip().lower()
        user = self.repo.get_user(email_clean)
        if not user:
            return None

        # 6-digit random code
        recovery_code = "".join(secrets.choice("0123456789") for _ in range(6))
        user["recovery_code"] = recovery_code
        self.repo.save_user(user)
        return recovery_code

    def reset_password_with_code(self, email: str, recovery_code: str, new_password: str) -> bool:
        """Validates account recovery code and updates the password securely."""
        email_clean = email.strip().lower()
        user = self.repo.get_user(email_clean)
        if not user or not user.get("recovery_code"):
            return False

        if len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        # Constant-time comparison to protect against timing attacks
        if secrets.compare_digest(user["recovery_code"], recovery_code.strip()):
            user["password_hash"] = self._hash_password(new_password)
            user["recovery_code"] = None
            self.repo.save_user(user)
            return True
        return False
