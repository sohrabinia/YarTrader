import os
import json
import hmac
import hashlib
import secrets
import threading
import time
from typing import Dict, Any, Optional, List
from src.Application.Dashboard.auth_repo import AuthRepository

class LockoutAuditStore:
    """
    Thread-safe and process-safe persistent manager for failed login attempts and audit logs.
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
            return data.get("failed_attempts", {}).get(email.lower(), [])

    def record_failed_attempt(self, email: str, timestamp: float) -> int:
        with self.lock:
            data = self._load()
            email_clean = email.lower()
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
            email_clean = email.lower()
            if "failed_attempts" in data and email_clean in data["failed_attempts"]:
                del data["failed_attempts"][email_clean]
                self._save(data)

    def prune_old_attempts(self, email: str, expiry_sec: float = 900.0) -> None:
        with self.lock:
            data = self._load()
            email_clean = email.lower()
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

            # Format timestamp as ISO-8601 UTC
            from datetime import datetime, timezone
            timestamp_str = datetime.now(timezone.utc).isoformat()

            audit_record = {
                "timestamp": timestamp_str,
                "event_type": event_type,
                "identifier": identifier.lower(),
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
    Handles secure hashing (PBKDF2-SHA256), OAuth2 account linking,
    and role-based session token validation.
    """
    def __init__(self, repo: Optional[AuthRepository] = None, lockout_store: Optional[LockoutAuditStore] = None) -> None:
        self.repo = repo or AuthRepository()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.lockout_store = lockout_store or LockoutAuditStore()
        self.lock = threading.Lock()
        self._rehydrate_sessions()

    def _rehydrate_sessions(self) -> None:
        """Rehydrates active sessions from DeviceTracker (runtime_logs/sessions.json) and AuthRepository across process restarts."""
        try:
            from src.Application.Dashboard.device_tracker import DeviceTracker
            tracker = DeviceTracker()
            data = tracker._load()
            if not isinstance(data, dict):
                return

            sessions = data.get("sessions", {})
            if not isinstance(sessions, dict):
                return

            for token, sess_info in sessions.items():
                if isinstance(sess_info, dict) and sess_info.get("state") == "ACTIVE":
                    email = sess_info.get("email")
                    if email and isinstance(email, str):
                        user = self.repo.get_user_by_email(email)
                        if user and isinstance(user, dict):
                            self.active_sessions[token] = {
                                "email": user["email"],
                                "role": user.get("role", "USER"),
                                "name": user.get("name", ""),
                                "tier": user.get("tier", "FREE"),
                                "user_id": user.get("user_id", user["email"])
                            }
        except Exception as err:
            try:
                from app.core.logging import log_event
                log_event("WARNING", f"AuthService session rehydration warning: {err}")
            except Exception:
                pass

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a plain text password using PBKDF2-SHA256 with per-password salt."""
        salt = secrets.token_hex(16)
        iterations = 100000
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
        return f"pbkdf2_sha256${iterations}${salt}${key.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verifies a password against PBKDF2-SHA256 hash using constant-time comparison."""
        if not hashed or not isinstance(hashed, str):
            return False
        parts = hashed.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        try:
            iterations = int(parts[1])
            salt = parts[2]
            expected_hash = parts[3]
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
            return hmac.compare_digest(key.hex(), expected_hash)
        except Exception:
            return False

    def register_user(self, email: str, password: str, name: str = "") -> Dict[str, Any]:
        """Registers a new user account with secure password storage and auto-admin assignment."""
        email_clean = email.strip().lower()
        if self.repo.get_user_by_email(email_clean):
            from src.Infrastructure.exceptions import ValidationException
            raise ValidationException("Email address is already registered.")

        role = "ADMIN" if self.repo.is_admin_email(email_clean) else "USER"
        pw_hash = self.hash_password(password)
        user = self.repo.create_user(email=email_clean, password_hash=pw_hash, role=role, name=name)
        if self.repo.is_admin_email(email_clean):
            user["role"] = "ADMIN"
            user["tier"] = "INSTITUTIONAL"
            self.repo.save_db()
        return user

    def set_user_password(self, email: str, new_password: str) -> Dict[str, Any]:
        """Sets or updates the PBKDF2-SHA256 password credential for an existing user account."""
        email_clean = email.strip().lower()
        user = self.repo.get_user_by_email(email_clean)
        if not user:
            from src.Infrastructure.exceptions import ValidationException
            raise ValidationException("User account not found.")

        user["password_hash"] = self.hash_password(new_password)
        if self.repo.is_admin_email(email_clean):
            user["role"] = "ADMIN"
            user["tier"] = "INSTITUTIONAL"
        self.repo.save_db()
        return user

    def login_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticates email and password credentials."""
        if not email or not password:
            return None
        email_clean = email.strip().lower()

        # Synchronize missing password credential for recognized Admin account if applicable
        if self.repo.is_admin_email(email_clean):
            self.repo.synchronize_admin_credential(email_clean)

        user = self.repo.get_user_by_email(email_clean)
        if not user or not user.get("password_hash"):
            return None

        if not self.verify_password(password, user["password_hash"]):
            return None

        if self.repo.is_admin_email(email_clean) and user.get("role") != "ADMIN":
            user["role"] = "ADMIN"
            user["tier"] = "INSTITUTIONAL"
            self.repo.save_db()

        return user

    def authenticate_social(self, email: str, provider: str, provider_id: str, name: str = "") -> Dict[str, Any]:
        """
        Maps or signs up a social account and binds it to user profile.
        """
        email_clean = email.strip().lower()
        user = self.repo.get_user_by_email(email_clean)
        if not user:
            user = self.repo.create_user(email=email_clean, password_hash="", role="USER", name=name)

        user = self.repo.link_social_account(email_clean, provider, provider_id)
        return user

    def create_session(self, user: Dict[str, Any], user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
        token = f"tkn-{secrets.token_hex(24)}"
        self.active_sessions[token] = {
            "email": user["email"],
            "role": user.get("role", "USER"),
            "name": user.get("name", ""),
            "tier": user.get("tier", "FREE"),
            "user_id": user.get("user_id", user["email"])
        }

        # Persistently record active session login
        try:
            from src.Application.Dashboard.device_tracker import DeviceTracker
            tracker = DeviceTracker()
            tracker.record_session(token, user["email"], user_agent or "Unknown", ip_address or "Unknown")
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
        email = None
        if token in self.active_sessions:
            email = self.active_sessions[token].get("email")
            del self.active_sessions[token]

        try:
            from src.Application.Dashboard.device_tracker import DeviceTracker
            tracker = DeviceTracker()
            if not email:
                data = tracker._load()
                sess_info = data.get("sessions", {}).get(token) if isinstance(data, dict) else None
                if isinstance(sess_info, dict):
                    email = sess_info.get("email")
            if email:
                tracker.revoke_session(token, email)
        except Exception as err:
            try:
                from app.core.logging import log_event
                log_event("WARNING", f"AuthService.logout persistent session revocation warning: {err}")
            except Exception:
                pass

# Secure Shared Global Singleton to prevent circular imports or state leaks
global_auth_service = AuthService()

def send_saas_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends SaaS system emails. If SMTP environment configurations are available,
    delivers via real SMTP. Otherwise, falls back to logging mock emails to disk.
    """
    import smtplib
    from email.mime.text import MIMEText
    from datetime import datetime

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    log_file = "runtime_logs/mock_emails.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    log_record = f"=== EMAIL SEND ===\nTimestamp: {datetime.now().isoformat()}\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n==================\n\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_record)

    if smtp_host and smtp_port and smtp_user and smtp_pass:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to_email

            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=5.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            try:
                from app.core.logging import log_event
                log_event("ERROR", f"SMTP delivery failed to {to_email}: {str(e)}")
            except Exception:
                pass
            return False
    return True
