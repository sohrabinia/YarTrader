import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from src.Infrastructure.exceptions import ValidationException

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
        is_production = (os.environ.get("YARTRADER_ENV") == "production" or
                         os.environ.get("TRADEYAR_ENV") == "production" or
                         os.environ.get("RG_ENV") == "production")

        if not os.path.exists(self.filepath):
            # Derive primary administrator details safely without exposing personal identities
            admin_email = os.environ.get("YARTRADER_DEFAULT_ADMIN_EMAIL", os.environ.get("TRADEYAR_DEFAULT_ADMIN_EMAIL", "admin-disabled@yartrader.app")).strip().lower()
            admin_pw_hash = os.environ.get("YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH", os.environ.get("TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH", ""))

            # Seed default admin and user accounts
            if is_production:
                if not admin_pw_hash or admin_pw_hash in ("*", "placeholder", ""):
                    raise ValidationException(
                        "Production Configuration Error: YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH / TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH must be configured with a secure, non-empty PBKDF2 hash."
                    )
                if admin_email == "admin-disabled@yartrader.app" or not admin_email:
                    raise ValidationException(
                        "Production Configuration Error: YARTRADER_DEFAULT_ADMIN_EMAIL / TRADEYAR_DEFAULT_ADMIN_EMAIL must be configured with a valid production administrator email."
                    )
                default_data = {
                    admin_email: {
                        "email": admin_email,
                        "password_hash": admin_pw_hash,
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {},
                        "is_verified": True,
                        "tier": "INSTITUTIONAL"
                    }
                }
            else:
                default_data = {
                    admin_email: {
                        "email": admin_email,
                        "password_hash": admin_pw_hash if (admin_pw_hash and admin_pw_hash not in ("*", "placeholder")) else "",
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {},
                        "is_verified": True,
                        "tier": "INSTITUTIONAL"
                    },
                    "trader@yartrader.app": {
                        "email": "trader@yartrader.app",
                        "password_hash": "",
                        "role": "USER",
                        "name": "Elite Trader",
                        "social_providers": {},
                        "is_verified": True,
                        "tier": "FREE"
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
        """Pure lookup method returning user record without mutation side-effects."""
        if not email or not isinstance(email, str):
            return None
        return self.users.get(email.strip().lower())

    def synchronize_admin_credential(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Synchronizes missing password credential for an existing recognized Admin account.
        Rules:
        - Applied strictly to recognized Admin identities (is_admin_email).
        - Existing non-empty password_hash is NEVER overwritten.
        - Synchronizes strictly from authoritative environment variables.
        - Fails closed if production admin password hash is missing/unavailable.
        - Preserves user_id, email, social_providers, role, tier, and customer data.
        """
        if not email or not isinstance(email, str):
            return None

        email_clean = email.strip().lower()
        if not self.is_admin_email(email_clean):
            return None

        user = self.users.get(email_clean)
        if not user:
            return None

        modified = False
        if user.get("role") != "ADMIN":
            user["role"] = "ADMIN"
            user["tier"] = "INSTITUTIONAL"
            modified = True

        # Existing password_hash MUST NEVER be overwritten
        if not user.get("password_hash"):
            admin_pw_hash = os.environ.get("YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH", os.environ.get("TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH"))
            if admin_pw_hash and admin_pw_hash not in ("*", "placeholder", ""):
                user["password_hash"] = admin_pw_hash
                modified = True

        if modified:
            self.save_db()

        return user

    def is_admin_email(self, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        email_clean = email.strip().lower()
        default_admin = os.environ.get("YARTRADER_DEFAULT_ADMIN_EMAIL", os.environ.get("TRADEYAR_DEFAULT_ADMIN_EMAIL", "")).strip().lower()
        admin_list = {"m.a.sohrabinia@gmail.com", "m.a.sorabinia@gmail.com", "admin@yartrader.app"}
        if default_admin:
            admin_list.add(default_admin)
        return email_clean in admin_list

    def create_user(self, email: str, password_hash: str = "", role: str = "USER", name: str = "") -> Dict[str, Any]:
        email_clean = email.lower()
        user_data = {
            "email": email_clean,
            "password_hash": password_hash,
            "role": role,
            "name": name or email_clean.split("@")[0].capitalize(),
            "social_providers": {},
            "is_verified": False,
            "tier": "FREE",
            "verification_token_hash": None,
            "verification_token_expires": 0.0,
            "reset_token_hash": None,
            "reset_token_expires": 0.0
        }
        self.users[email_clean] = user_data
        self.save_db()
        return user_data

    def link_social_account(self, email: str, provider: str, provider_id: str) -> Dict[str, Any]:
        user = self.get_user_by_email(email)
        is_admin = self.is_admin_email(email)
        default_role = "ADMIN" if is_admin else "USER"
        default_tier = "INSTITUTIONAL" if is_admin else "FREE"

        if not user:
            user = self.create_user(email, password_hash="", role=default_role, name="")
            user["tier"] = default_tier
        elif is_admin and user.get("role") != "ADMIN":
            user["role"] = "ADMIN"
            user["tier"] = "INSTITUTIONAL"

        user["social_providers"][provider] = provider_id
        self.save_db()
        return user
