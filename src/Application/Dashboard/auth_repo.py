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
        import uuid
        is_production = (os.environ.get("YARTRADER_ENV") == "production" or
                         os.environ.get("TRADEYAR_ENV") == "production" or
                         os.environ.get("RG_ENV") == "production")

        if not os.path.exists(self.filepath):
            admin_email = os.environ.get("YARTRADER_DEFAULT_ADMIN_EMAIL", os.environ.get("TRADEYAR_DEFAULT_ADMIN_EMAIL", "admin-disabled@yartrader.app")).strip().lower()
            admin_pw_hash = os.environ.get("YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH", os.environ.get("TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH", ""))

            if is_production:
                if not admin_pw_hash or admin_pw_hash in ("*", "placeholder", ""):
                    raise ValidationException(
                        "Production Configuration Error: YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH / TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH must be configured with a secure, non-empty PBKDF2 hash."
                    )
                if admin_email == "admin-disabled@yartrader.app" or not admin_email:
                    raise ValidationException(
                        "Production Configuration Error: YARTRADER_DEFAULT_ADMIN_EMAIL / TRADEYAR_DEFAULT_ADMIN_EMAIL must be configured with a valid production administrator email."
                    )
                admin_uid = f"usr-{uuid.uuid5(uuid.NAMESPACE_DNS, admin_email)}"
                default_data = {
                    admin_email: {
                        "user_id": admin_uid,
                        "owner_id": admin_uid,
                        "workspace_id": "yartrader-main",
                        "email": admin_email,
                        "password_hash": admin_pw_hash,
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {},
                        "google_sub": None,
                        "is_verified": True,
                        "tier": "INSTITUTIONAL"
                    }
                }
            else:
                admin_uid = f"usr-{uuid.uuid5(uuid.NAMESPACE_DNS, admin_email)}"
                trader_email = "trader@yartrader.app"
                trader_uid = f"usr-{uuid.uuid5(uuid.NAMESPACE_DNS, trader_email)}"
                default_data = {
                    admin_email: {
                        "user_id": admin_uid,
                        "owner_id": admin_uid,
                        "workspace_id": "yartrader-main",
                        "email": admin_email,
                        "password_hash": admin_pw_hash if (admin_pw_hash and admin_pw_hash not in ("*", "placeholder")) else "",
                        "role": "ADMIN",
                        "name": "Principal Supervisor",
                        "social_providers": {},
                        "google_sub": None,
                        "is_verified": True,
                        "tier": "INSTITUTIONAL"
                    },
                    trader_email: {
                        "user_id": trader_uid,
                        "owner_id": trader_uid,
                        "workspace_id": "yartrader-main",
                        "email": trader_email,
                        "password_hash": "",
                        "role": "USER",
                        "name": "Elite Trader",
                        "social_providers": {},
                        "google_sub": None,
                        "is_verified": True,
                        "tier": "FREE"
                    }
                }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            return default_data

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                modified = False
                for email_key, udata in list(data.items()):
                    if not isinstance(udata, dict):
                        continue
                    if "user_id" not in udata or not udata["user_id"]:
                        udata["user_id"] = f"usr-{uuid.uuid5(uuid.NAMESPACE_DNS, email_key.lower())}"
                        modified = True
                    if "owner_id" not in udata or not udata["owner_id"]:
                        udata["owner_id"] = udata["user_id"]
                        modified = True
                    if "workspace_id" not in udata or not udata["workspace_id"]:
                        udata["workspace_id"] = "yartrader-main"
                        modified = True
                    if "google_sub" not in udata:
                        udata["google_sub"] = udata.get("social_providers", {}).get("google")
                        modified = True
                if modified:
                    try:
                        with open(self.filepath, "w", encoding="utf-8") as wf:
                            json.dump(data, wf, indent=4)
                    except Exception as me:
                        logger.error(f"Failed to save migrated auth DB: {me}")
                return data
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

    def get_user_by_google_sub(self, google_sub: str) -> Optional[Dict[str, Any]]:
        """Look up user record by verified Google sub identifier across all users."""
        if not google_sub or not isinstance(google_sub, str):
            return None
        sub_clean = google_sub.strip()
        for user in self.users.values():
            if user.get("google_sub") == sub_clean or user.get("social_providers", {}).get("google") == sub_clean:
                return user
        return None

    def synchronize_admin_credential(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Synchronizes missing password credential for an existing recognized Admin account.
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
            modified = True
        if user.get("tier") != "INSTITUTIONAL":
            user["tier"] = "INSTITUTIONAL"
            modified = True

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

    def create_user(self, email: str, password_hash: str = "", role: str = "USER", name: str = "", user_id: Optional[str] = None, owner_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        import uuid
        email_clean = email.lower()
        uid = user_id or f"usr-{uuid.uuid4()}"
        oid = owner_id or uid
        wid = workspace_id or "yartrader-main"
        user_data = {
            "user_id": uid,
            "owner_id": oid,
            "workspace_id": wid,
            "email": email_clean,
            "password_hash": password_hash,
            "role": role,
            "name": name or email_clean.split("@")[0].capitalize(),
            "social_providers": {},
            "google_sub": None,
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
        email_clean = email.strip().lower()
        user = None
        if provider == "google":
            user = self.get_user_by_google_sub(provider_id)

        if not user:
            user = self.get_user_by_email(email_clean)

        is_admin = self.is_admin_email(email_clean) or (user and self.is_admin_email(user.get("email", "")))
        default_role = "ADMIN" if is_admin else "USER"
        default_tier = "INSTITUTIONAL" if is_admin else "FREE"

        if not user:
            user = self.create_user(email_clean, password_hash="", role=default_role, name="")
            user["tier"] = default_tier
        else:
            if user.get("email") != email_clean:
                existing_conflict = self.get_user_by_email(email_clean)
                if existing_conflict and existing_conflict.get("user_id") != user.get("user_id"):
                    raise ValidationException(f"Email address '{email_clean}' is already associated with another account.")
                old_email = user.get("email")
                user["email"] = email_clean
                if old_email in self.users:
                    del self.users[old_email]
                self.users[email_clean] = user

            if is_admin and user.get("role") != "ADMIN":
                user["role"] = "ADMIN"
                user["tier"] = "INSTITUTIONAL"

        if "social_providers" not in user:
            user["social_providers"] = {}
        user["social_providers"][provider] = provider_id
        if provider == "google":
            user["google_sub"] = provider_id

        self.save_db()
        return user
