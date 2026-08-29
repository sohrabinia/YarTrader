import os
import time
import hmac
import hashlib
from typing import Dict, Any, Tuple, Optional
from app.core.logging import log_audit

DEFAULT_TELEGRAM_BOT_TOKEN = "789101112:AAExampleBotTokenForYarTraderAuthSecurity"

def get_telegram_bot_token() -> str:
    """Returns Telegram bot token from environment or config."""
    return os.environ.get("TELEGRAM_BOT_TOKEN") or DEFAULT_TELEGRAM_BOT_TOKEN

def verify_telegram_authorization(auth_data: Dict[str, Any], max_age_seconds: int = 86400) -> Tuple[bool, str]:
    """
    Cryptographically verifies Telegram Login Widget payload.
    Official Telegram Bot API Hash Verification:
    1. Extract 'hash' from payload.
    2. Sort all key=value pairs (excluding 'hash') alphabetically by key, separated by '\n'.
    3. Compute secret_key = sha256(bot_token.encode('utf-8')).digest().
    4. Compute check_hash = hmac_sha256(secret_key, data_check_string).hexdigest().
    5. Constant-time compare check_hash with received hash.
    6. Verify auth_date timestamp freshness for replay attack prevention.
    """
    if not isinstance(auth_data, dict):
        return False, "Invalid payload type."

    received_hash = auth_data.get("hash")
    if not received_hash:
        return False, "Missing Telegram authorization hash."

    # Validate auth_date
    auth_date = auth_data.get("auth_date")
    if not auth_date:
        return False, "Missing auth_date timestamp."

    try:
        auth_timestamp = int(auth_date)
    except (ValueError, TypeError):
        return False, "Invalid auth_date timestamp format."

    current_time = int(time.time())
    if current_time - auth_timestamp > max_age_seconds:
        return False, "Telegram authorization has expired (replay protection)."
    if auth_timestamp > current_time + 300: # 5 min clock skew tolerance
        return False, "Telegram authorization timestamp is in the future."

    # Build data check string for official Telegram widget parameters
    telegram_widget_fields = {"id", "first_name", "last_name", "username", "photo_url", "auth_date"}
    data_check_list = []
    for k, v in sorted(auth_data.items()):
        if k in telegram_widget_fields and v is not None and v != "":
            data_check_list.append(f"{k}={v}")

    data_check_string = "\n".join(data_check_list)

    bot_token = get_telegram_bot_token()
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, str(received_hash).lower()):
        log_audit("TELEGRAM_AUTH_FAILURE", details=f"Invalid hash signature for Telegram user ID {auth_data.get('id')}")
        return False, "Invalid Telegram cryptographic signature."

    return True, "Verified"
