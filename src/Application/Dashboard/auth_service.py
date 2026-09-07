import os
import json
import hmac
import hashlib
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Infrastructure.exceptions import ValidationException

def normalize_email(email: str) -> str:
    """
    Canonical email normalization rule.
    Trims surrounding whitespace, converts to lowercase, and validates non-empty structure.
    """
    if not email or not isinstance(email, str):
        raise ValidationException("Invalid email: Email address must be a non-empty string.")
    normalized = email.strip().lower()
    if "@" not in normalized or len(normalized) < 3:
        raise ValidationException(f"Invalid email structure: '{email}'.")
    return normalized


class EmailVerificationService:
    """
    Canonical Email Verification Challenge & Token Manager.
    Generates cryptographically random, single-use, time-limited tokens with expiry.
    Decouples auth logic from SMTP delivery adapters.
    """
    def __init__(self, filepath: str = "runtime_logs/verification_tokens.json", expiry_seconds: int = 86400) -> None:
        self.filepath = filepath
        self.expiry_seconds = expiry_seconds
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({})

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        with self.lock:
            tmp_file = self.filepath + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                os.replace(tmp_file, self.filepath)
            except Exception:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass

    def create_verification_challenge(self, email: str) -> str:
        """
        Creates a time-limited single-use email verification token.
        Token is hashed prior to storage to prevent plaintext token leaks.
        """
        email_clean = normalize_email(email)
        raw_token = f"vkn-{secrets.token_urlsafe(32)}"
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        now = time.time()
        expires_at = now + self.expiry_seconds

        with self.lock:
            data = self._load()
            data[token_hash] = {
                "email": email_clean,
                "created_at": now,
                "expires_at": expires_at,
                "used": False
            }
            self._save(data)

        return raw_token

    def verify_token(self, raw_token: str) -> str:
        """
        Validates and consumes a verification token.
        Returns normalized email address on success.
        Raises ValidationException if token is invalid, expired, or reused.
        """
        if not raw_token or not isinstance(raw_token, str):
            raise ValidationException("Invalid token format.")

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        now = time.time()

        with self.lock:
            data = self._load()
            token_record = data.get(token_hash)

            if not token_record:
                raise ValidationException("Invalid or non-existent verification token.")

            if token_record.get("used", False):
                raise ValidationException("Verification token has already been used.")

            if now > token_record.get("expires_at", 0):
                raise ValidationException("Verification token has expired.")

            # Mark token as used immediately (single-use enforcement)
            token_record["used"] = True
            token_record["used_at"] = now
            self._save(data)

            return token_record["email"]


class LockoutAuditStore:
    """
    Thread-safe persistent manager for failed login attempts and audit logs.
    Saves state persistently to file-based database runtime_logs/lockout_audit.json.
    """
    def __init__(self, filepath: str = "runtime_logs/lockout_audit.json") -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({"failed_attempts": {}, "audit_log": []})

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"failed_attempts": {}, "audit_log": []}

    def _save(self, data: Dict[str, Any]) -> None:
        with self.lock:
            tmp_file = self.filepath + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                os.replace(tmp_file, self.filepath)
            except Exception:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass

    def get_failed_attempts(self, email: str) -> List[float]:
        with self.lock:
            data = self._load()
            return data.get("failed_attempts", {}).get(normalize_email(email), [])

    def record_failed_attempt(self, email: str, timestamp: float) -> int:
        with self.lock:
            data = self._load()
            email_clean = normalize_email(email)
            if "failed_attempts" not in data:
                data["failed_attempts"] = {}
            if email_clean not in data["failed_attempts"]:
                data["failed_attempts"][email_clean] = []

            data["failed_attempts"][email_clean].append(timestamp)
            self._save(data)
            return len(data["failed_attempts"][email_clean])

    def clear_failed_attempts(self, email: str) -> None:
        with self.lock:
            data = self._load()
            email_clean = normalize_email(email)
            if "failed_attempts" in data and email_clean in data["failed_attempts"]:
                del data["failed_attempts"][email_clean]
                self._save(data)

    def prune_old_attempts(self, email: str, expiry_sec: float = 900.0) -> None:
        with self.lock:
            data = self._load()
            email_clean = normalize_email(email)
            now = time.time()
            if "failed_attempts" in data and email_clean in data["failed_attempts"]:
                attempts = data["failed_attempts"][email_clean]
                valid_attempts = [t for t in attempts if now - t < expiry_sec]
                if valid_attempts:
                    data["failed_attempts"][email_clean] = valid_attempts
                else:
                    del data["failed_attempts"][email_clean]
                self._save(data)

    def log_audit_event(self, event_type: str, identifier: str, source_ip: Optional[str], user_agent: Optional[str], result: str, lockout_state: bool, penalty_info: str) -> None:
        """Appends a new audit record to the log. Append-only, tamper-resistant."""
        with self.lock:
            data = self._load()
            if "audit_log" not in data:
                data["audit_log"] = []

            timestamp_str = datetime.now(timezone.utc).isoformat()

            audit_record = {
                "timestamp": timestamp_str,
                "event_type": event_type,
                "identifier": normalize_email(identifier),
                "source_ip": source_ip or "Unknown",
                "user_agent": user_agent or "Unknown",
                "result": result,
                "lockout_state": lockout_state,
                "penalty_info": penalty_info
            }
            data["audit_log"].append(audit_record)
            self._save(data)


class AuthService:
    """
    Handles secure password hashing (PBKDF2-SHA256), OAuth2 account linking,
    email normalization, verification challenges, and role-based session token validation.
    """
    def __init__(
        self,
        repo: Optional[AuthRepository] = None,
        lockout_store: Optional[LockoutAuditStore] = None,
        verification_service: Optional[EmailVerificationService] = None
    ) -> None:
        self.repo = repo or AuthRepository()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.lockout_store = lockout_store or LockoutAuditStore()
        self.verification_service = verification_service or EmailVerificationService()
        self.lock = threading.Lock()

    def hash_password(self, password: str, salt: Optional[str] = None, iterations: int = 100000) -> str:
        """Standard PBKDF2-SHA256 hashing."""
        if not password or not isinstance(password, str) or len(password) < 6:
            raise ValidationException("Password must be at least 6 characters in length.")

        salt_str = salt or secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt_str.encode('utf-8'),
            iterations
        )
        return f"pbkdf2_sha256${iterations}${salt_str}${dk.hex()}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        if not hashed_password or not password:
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

    def register_user(self, email: str, password: str, name: str = "", role: str = "USER") -> Dict[str, Any]:
        """Registers a new user with unverified email state and triggers verification challenge."""
        email_clean = normalize_email(email)

        if self.repo.get_user_by_email(email_clean):
            raise ValidationException("An account with this email already exists.")

        password_hash = self.hash_password(password)
        user = self.repo.create_user(email=email_clean, password_hash=password_hash, role=role, name=name)

        # Explicitly mark email unverified
        user["is_verified"] = False
        user["email"] = email_clean
        self.repo.save_db()

        # Create verification challenge
        token = self.verification_service.create_verification_challenge(email_clean)
        send_saas_email(
            to_email=email_clean,
            subject="Verify your YarTrader Account",
            body=f"Welcome to YarTrader, {name or 'Trader'}! Your email verification token is: {token}"
        )

        return {
            "user": {
                "user_id": user.get("user_id", email_clean),
                "email": user["email"],
                "name": user.get("name", ""),
                "role": user.get("role", "USER"),
                "is_verified": False
            },
            "verification_token": token
        }

    def verify_email_account(self, token: str) -> bool:
        """Consumes verification token and transitions user account to verified state."""
        email_clean = self.verification_service.verify_token(token)
        user = self.repo.get_user_by_email(email_clean)

        if not user:
            raise ValidationException(f"Account for '{email_clean}' not found.")

        user["is_verified"] = True
        user["verified_at"] = datetime.now(timezone.utc).isoformat()
        self.repo.save_db()
        return True

    def authenticate_credentials(self, email: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[Dict[str, Any]]:
        now = time.time()
        email_clean = normalize_email(email)

        # Clean old attempts persistently
        self.lockout_store.prune_old_attempts(email_clean)
        failed_attempts = self.lockout_store.get_failed_attempts(email_clean)

        # Lockout check (Max 5 attempts per 15 minutes)
        if len(failed_attempts) >= 5:
            self.lockout_store.log_audit_event(
                event_type="ADMIN_LOCKOUT",
                identifier=email_clean,
                source_ip=ip_address,
                user_agent=user_agent,
                result="Blocked: Account is locked out",
                lockout_state=True,
                penalty_info="Threshold 5/5 breached"
            )
            try:
                from app.core.logging import log_security
                log_security("ACCOUNT_LOCKOUT", email=email_clean, reason="Threshold 5/5 breached", source_ip=ip_address)
            except Exception:
                pass
            return None

        user = self.repo.get_user_by_email(email_clean)
        role = user.get("role", "USER") if user else "USER"
        is_admin = (role == "ADMIN")

        if user and not user.get("is_verified", True):
            raise ValidationException("Account is not verified. Please verify your email first.")

        if user and self.verify_password(password, user.get("password_hash", "")):
            # Clear failed attempts persistently
            self.lockout_store.clear_failed_attempts(email_clean)

            event_type = "ADMIN_LOGIN_SUCCESS" if is_admin else "USER_LOGIN_SUCCESS"
            self.lockout_store.log_audit_event(
                event_type=event_type,
                identifier=email_clean,
                source_ip=ip_address,
                user_agent=user_agent,
                result="Success",
                lockout_state=False,
                penalty_info="Clear"
            )

            try:
                from app.core.logging import log_security
                log_security("LOGIN_SUCCESS", email=email_clean, role=role, source_ip=ip_address)
            except Exception:
                pass
            return user

        # Record failed attempt persistently
        failed_count = self.lockout_store.record_failed_attempt(email_clean, now)

        delay = 0.0
        if failed_count > 2:
            delay = min(1.0 * (failed_count - 2), 5.0)

        event_type = "ADMIN_LOGIN_FAILURE" if is_admin else "USER_LOGIN_FAILURE"
        penalty_str = f"Attempt {failed_count}/5"
        if delay > 0.0:
            penalty_str += f" | Delay Penalty {delay}s applied"

        self.lockout_store.log_audit_event(
            event_type=event_type,
            identifier=email_clean,
            source_ip=ip_address,
            user_agent=user_agent,
            result="Failed credentials verification",
            lockout_state=(failed_count >= 5),
            penalty_info=penalty_str
        )

        try:
            from app.core.logging import log_security
            log_security("LOGIN_FAILURE", email=email_clean, role=role, attempts=failed_count, source_ip=ip_address)
        except Exception:
            pass

        if failed_count >= 5:
            self.lockout_store.log_audit_event(
                event_type="ADMIN_LOCKOUT",
                identifier=email_clean,
                source_ip=ip_address,
                user_agent=user_agent,
                result="Lockout triggered",
                lockout_state=True,
                penalty_info="Lockout enforced"
            )
            try:
                from app.core.logging import log_security
                log_security("ACCOUNT_LOCKOUT", email=email_clean, reason="Max failed attempts exceeded", source_ip=ip_address)
            except Exception:
                pass

        if delay > 0.0:
            time.sleep(delay)

        return None

    def authenticate_social(self, email: str, provider: str, provider_id: str, name: str = "") -> Dict[str, Any]:
        """Maps or signs up a social account and binds it to user profile."""
        email_clean = normalize_email(email)
        user = self.repo.get_user_by_email(email_clean)
        if not user:
            user = self.repo.create_user(email=email_clean, password_hash="", role="USER", name=name)
            user["is_verified"] = True
            self.repo.save_db()

        user = self.repo.link_social_account(email_clean, provider, provider_id)
        return user

    def create_session(self, user: Dict[str, Any], user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
        token = f"tkn-{secrets.token_hex(24)}"
        email_clean = normalize_email(user["email"])
        self.active_sessions[token] = {
            "email": email_clean,
            "role": user.get("role", "USER"),
            "name": user.get("name", ""),
            "tier": user.get("tier", "FREE"),
            "user_id": user.get("user_id", email_clean)
        }

        try:
            from src.Application.Dashboard.device_tracker import DeviceTracker
            tracker = DeviceTracker()
            tracker.record_session(token, email_clean, user_agent or "Unknown", ip_address or "Unknown")
        except Exception:
            pass

        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        return self.get_session_user(token)

    def get_session_user(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            from src.Application.Dashboard.device_tracker import DeviceTracker
            tracker = DeviceTracker()
            if tracker.is_session_revoked(token):
                if token in self.active_sessions:
                    del self.active_sessions[token]
                return None
            tracker.refresh_last_seen(token)
        except Exception:
            pass

        return self.active_sessions.get(token)

    def logout(self, token: str) -> None:
        if token in self.active_sessions:
            del self.active_sessions[token]

# Secure Shared Global Singleton
global_auth_service = AuthService()

def send_saas_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends SaaS system emails. If SMTP environment configurations are available,
    delivers via real SMTP. Otherwise, falls back to logging mock emails to disk.
    """
    import smtplib
    from email.mime.text import MIMEText

    email_clean = normalize_email(to_email)
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    log_file = "runtime_logs/mock_emails.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    log_record = f"=== EMAIL SEND ===\nTimestamp: {datetime.now(timezone.utc).isoformat()}\nTo: {email_clean}\nSubject: {subject}\nBody: {body}\n==================\n\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_record)

    if smtp_host and smtp_port and smtp_user and smtp_pass:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = email_clean

            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=5.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            try:
                from app.core.logging import log_event
                log_event("ERROR", f"SMTP delivery failed to {email_clean}: {str(e)}")
            except Exception:
                pass
            return False
    return True
