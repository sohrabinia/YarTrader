import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

class AuthRepository:
    """
    Thread-safe, atomic, file-based JSON repository for persisting user records,
    roles, subscription states, product analytics, and AI cost control limits.
    Ready for production and public monetization.
    """
    def __init__(self, db_path: str = "runtime_logs/auth.json") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "users": {},
            "analytics": {
                "registrations": 0,
                "page_views": 0,
                "analyses_viewed": 0,
                "support_queries": 0,
                "pro_conversions": 0
            },
            "ai_cost_logs": {}  # email -> list of raw request timestamps
        }
        self._load_db()

    def _load_db(self) -> None:
        """Loads database from disk, creating directories and default admin if missing."""
        with self._lock:
            # Ensure directories exist
            dir_name = os.path.dirname(self.db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        # Guarantee top-level fields
                        if "users" in loaded:
                            self._data["users"] = loaded["users"]
                        if "analytics" in loaded:
                            self._data["analytics"] = loaded["analytics"]
                        if "ai_cost_logs" in loaded:
                            self._data["ai_cost_logs"] = loaded["ai_cost_logs"]
                        return
                except Exception:
                    # Fallback to defaults if corrupted
                    pass

            self._save_db_unlocked()

    def _save_db_unlocked(self) -> None:
        """Saves internal database state atomically to disk. (Must be called inside lock)"""
        temp_path = f"{self.db_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, self.db_path)
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise IOError(f"AuthRepository Error: Failed to write database: {str(e)}")

    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves user by email/username (case-insensitive key)."""
        key = email.strip().lower()
        with self._lock:
            user = self._data["users"].get(key)
            if user:
                return dict(user)
            return None

    def save_user(self, user: Dict[str, Any]) -> None:
        """Saves or updates a user record."""
        email = user.get("email", "").strip().lower()
        if not email:
            raise ValueError("AuthRepository Error: User must have a valid email.")
        with self._lock:
            self._data["users"][email] = dict(user)
            self._save_db_unlocked()

    def list_users(self) -> List[Dict[str, Any]]:
        """Lists all registered users."""
        with self._lock:
            return [dict(u) for u in self._data["users"].values()]

    def delete_user(self, email: str) -> bool:
        """Deletes user by email/username."""
        key = email.strip().lower()
        with self._lock:
            if key in self._data["users"]:
                del self._data["users"][key]
                self._save_db_unlocked()
                return True
            return False

    # --- Product Analytics API ---
    def increment_analytic(self, metric: str) -> int:
        """Increments a product analytics counter securely."""
        with self._lock:
            if metric not in self._data["analytics"]:
                self._data["analytics"][metric] = 0
            self._data["analytics"][metric] += 1
            self._save_db_unlocked()
            return self._data["analytics"][metric]

    def get_analytics(self) -> Dict[str, int]:
        """Returns the current product analytics scorecard."""
        with self._lock:
            return dict(self._data["analytics"])

    # --- AI Cost Control API ---
    def log_ai_request(self, email: str) -> int:
        """Logs an AI request timestamp for a user and returns their total request count."""
        key = email.strip().lower()
        now_str = datetime.now().isoformat()
        with self._lock:
            if key not in self._data["ai_cost_logs"]:
                self._data["ai_cost_logs"][key] = []
            self._data["ai_cost_logs"][key].append(now_str)
            self._save_db_unlocked()
            return len(self._data["ai_cost_logs"][key])

    def get_ai_request_count(self, email: str) -> int:
        """Returns the total AI requests made by a user."""
        key = email.strip().lower()
        with self._lock:
            return len(self._data["ai_cost_logs"].get(key, []))

    def clear(self) -> None:
        """Clears all records (primarily for testing isolation)."""
        with self._lock:
            self._data = {
                "users": {},
                "analytics": {
                    "registrations": 0,
                    "page_views": 0,
                    "analyses_viewed": 0,
                    "support_queries": 0,
                    "pro_conversions": 0
                },
                "ai_cost_logs": {}
            }
            self._save_db_unlocked()
