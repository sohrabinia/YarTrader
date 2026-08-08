import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException

class DeviceTracker:
    """
    SaaS Persistent Login Device and Active Session Tracker.
    Saves state persistently to file-based database runtime_logs/sessions.json.
    Enforces secure session revocation, last seen refreshes, and prevents uncontrolled database growth.
    """
    def __init__(self, filepath: str = "runtime_logs/sessions.json") -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({"sessions": {}})

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"sessions": {}}

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

    def record_session(self, token: str, email: str, user_agent: str, ip_address: str) -> None:
        """Saves a new session mapping record and cleans old ones to prevent database expansion."""
        with self.lock:
            data = self._load()
            now = datetime.now(timezone.utc).isoformat()

            # Uncontrolled Database Growth protection: clean old sessions for the user
            email_clean = email.lower()
            user_sessions = [k for k, s in data["sessions"].items() if s["email"] == email_clean]
            # Cap active sessions count per user to 5, revoking oldest
            if len(user_sessions) >= 5:
                # Sort user_sessions by last_seen
                user_sessions.sort(key=lambda k: data["sessions"][k]["last_seen"])
                for old_key in user_sessions[: len(user_sessions) - 4]:
                    data["sessions"][old_key]["state"] = "REVOKED"

            data["sessions"][token] = {
                "session_id": f"sess-{secrets_token()}",
                "email": email_clean,
                "user_agent": user_agent or "Unknown",
                "ip_address": ip_address or "Unknown",
                "first_seen": now,
                "last_seen": now,
                "state": "ACTIVE"
            }
            self._save(data)

    def refresh_last_seen(self, token: str) -> bool:
        """Refreshes last seen timestamp for an active session."""
        with self.lock:
            data = self._load()
            if token in data["sessions"] and data["sessions"][token]["state"] == "ACTIVE":
                data["sessions"][token]["last_seen"] = datetime.now(timezone.utc).isoformat()
                self._save(data)
                return True
            return False

    def is_session_revoked(self, token: str) -> bool:
        """Returns True if the session has been explicitly revoked or is inactive."""
        with self.lock:
            data = self._load()
            session = data["sessions"].get(token)
            if not session or session.get("state") != "ACTIVE":
                return True
            return False

    def revoke_session(self, token: str, email: str) -> None:
        """Revokes an active session. Strictly enforces owner authorization checks."""
        with self.lock:
            data = self._load()
            session = data["sessions"].get(token)
            if not session:
                raise ValidationException("Session token not found.")

            if session["email"] != email.lower():
                raise ValidationException("Unauthorized session access request.")

            session["state"] = "REVOKED"
            self._save(data)

            # Invalidate global_auth_service session token
            try:
                from src.Application.Dashboard.auth_service import global_auth_service
                global_auth_service.logout(token)
            except Exception:
                pass

    def list_active_sessions(self, email: str) -> List[Dict[str, Any]]:
        """Returns a list of all active sessions for the user."""
        with self.lock:
            data = self._load()
            email_clean = email.lower()
            return [
                {
                    "session_id": s["session_id"],
                    "user_agent": s["user_agent"],
                    "ip_address": s["ip_address"],
                    "first_seen": s["first_seen"],
                    "last_seen": s["last_seen"],
                    "token": k  # reference
                }
                for k, s in data["sessions"].items()
                if s["email"] == email_clean and s["state"] == "ACTIVE"
            ]

def secrets_token() -> str:
    import secrets
    return secrets.token_hex(12)
