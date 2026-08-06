import hmac
import hashlib
import secrets
import threading
import time
from typing import Dict, Any, Optional, List
from src.Application.Dashboard.auth_repo import AuthRepository

class AuthService:
    """
    Handles secure hashing (PBKDF2-SHA256), OAuth2 account linking,
    and role-based session token validation.
    """
    def __init__(self, repo: Optional[AuthRepository] = None) -> None:
        self.repo = repo or AuthRepository()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[float]] = {}
        self.lock = threading.Lock()

    def hash_password(self, password: str, salt: str = "salt123", iterations: int = 100000) -> str:
        """Standard PBKDF2-SHA256 hashing."""
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            algo, iterations, salt, dk_hex = parts
            test_hash = self.hash_password(password, salt=salt, iterations=int(iterations))
            return hmac.compare_digest(test_hash, hashed_password)
        except Exception:
            return False

    def authenticate_credentials(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        now = time.time()

        with self.lock:
            # Cleanup old attempts (older than 15 minutes)
            if email in self.failed_attempts:
                self.failed_attempts[email] = [t for t in self.failed_attempts[email] if now - t < 900]
            else:
                self.failed_attempts[email] = []

            # Lockout check (Max 5 attempts per 15 minutes)
            if len(self.failed_attempts[email]) >= 5:
                try:
                    from app.core.logging import log_event
                    log_event("WARNING", f"Account lockout triggered for email: {email} due to excessive failed attempts.", source="auth_service")
                except Exception:
                    pass
                return None

        user = self.repo.get_user_by_email(email)
        if user and self.verify_password(password, user.get("password_hash", "")):
            with self.lock:
                if email in self.failed_attempts:
                    del self.failed_attempts[email]
            try:
                from app.core.logging import log_event
                log_event("INFO", f"User {email} successfully authenticated.", source="auth_service")
            except Exception:
                pass
            return user

        # Record failed attempt
        with self.lock:
            self.failed_attempts[email].append(now)
            failed_count = len(self.failed_attempts[email])

        # Progressive delay penalty to slow down scanners
        if failed_count > 2:
            time.sleep(min(1.0 * (failed_count - 2), 5.0))

        try:
            from app.core.logging import log_event
            log_event("WARNING", f"Failed authentication attempt for email: {email} (Attempt {failed_count}/5)", source="auth_service")
        except Exception:
            pass
        return None

    def authenticate_social(self, email: str, provider: str, provider_id: str, name: str = "") -> Dict[str, Any]:
        """
        Maps or signs up a social account and binds it to user profile.
        """
        user = self.repo.get_user_by_email(email)
        if not user:
            user = self.repo.create_user(email=email, password_hash="", role="USER", name=name)

        user = self.repo.link_social_account(email, provider, provider_id)
        return user

    def create_session(self, user: Dict[str, Any]) -> str:
        token = f"tkn-{secrets.token_hex(24)}"
        self.active_sessions[token] = {
            "email": user["email"],
            "role": user.get("role", "USER"),
            "name": user.get("name", "")
        }
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        return self.active_sessions.get(token)

    def logout(self, token: str) -> None:
        if token in self.active_sessions:
            del self.active_sessions[token]

# Secure Shared Global Singleton to prevent circular imports or state leaks
global_auth_service = AuthService()
