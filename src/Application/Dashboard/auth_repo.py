import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("AuthRepository")

class AuthRepository:
    """
    Manages secure user accounts, profiles, and social sign-in bindings.
    Saves state persistently to file-based database runtime_logs/auth.json.
    """
    def __init__(self, filepath: str = "runtime_logs/auth.json") -> None:
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.users: Dict[str, Dict[str, Any]] = self._load_db()

    def _load_db(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            is_production = (os.environ.get("TRADEYAR_ENV") == "production" or
                             os.environ.get("RG_ENV") == "production")

<<<<<<< HEAD
            # Derive primary administrator details safely without exposing personal identities
            admin_email = os.environ.get("TRADEYAR_DEFAULT_ADMIN_EMAIL", "admin-disabled@yartrader.app").lower()
=======
            # Derive primary administrator details
            admin_email = os.environ.get("TRADEYAR_DEFAULT_ADMIN_EMAIL", "m.a.sohrabinia@gmail.com").lower()
>>>>>>> main

            # Seed default admin and user accounts
            if is_production:
                # In production, we do NOT seed weak mock passwords.
                # Admin password must be set securely or configured via environments.
                admin_pw_hash = os.environ.get("TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH", "*")
                default_data = {
                    admin_email: {
                        "email": admin_email,
                        "password_hash": admin_pw_hash,
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {}
                    }
                }
            else:
                default_data = {
                    admin_email: {
                        "email": admin_email,
                        "password_hash": "pbkdf2_sha256$100000$salt123$409c9f7a77e8a9f6d63bc72a4e2ef309f4e24eb87cfd6537dbbfa34563e46c7d", # mock for 'admin123'
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {}
                    },
                    "trader@yartrader.app": {
                        "email": "trader@yartrader.app",
                        "password_hash": "pbkdf2_sha256$100000$salt123$409c9f7a77e8a9f6d63bc72a4e2ef309f4e24eb87cfd6537dbbfa34563e46c7d", # mock for 'trader123'
                        "role": "USER",
                        "name": "Elite Trader",
                        "social_providers": {}
                    }
                }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            return default_data

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading auth database, fallback to empty: {e}")
            return {}

    def save_db(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving auth database: {e}")

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.users.get(email.lower())

    def create_user(self, email: str, password_hash: str, role: str = "USER", name: str = "") -> Dict[str, Any]:
        email_clean = email.lower()
        user_data = {
            "email": email_clean,
            "password_hash": password_hash,
            "role": role,
            "name": name or email_clean.split("@")[0].capitalize(),
            "social_providers": {}
        }
        self.users[email_clean] = user_data
        self.save_db()
        return user_data

    def link_social_account(self, email: str, provider: str, provider_id: str) -> Dict[str, Any]:
        user = self.get_user_by_email(email)
        if not user:
            user = self.create_user(email, password_hash="", name="")

        user["social_providers"][provider] = provider_id
        self.save_db()
        return user
