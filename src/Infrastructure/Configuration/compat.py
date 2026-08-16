import os
import warnings
import logging
from typing import Optional, Any

logger = logging.getLogger("YarTrader.EnvCompat")

def get_env_compat(
    key_new: str,
    key_old: Optional[str] = None,
    default: Optional[Any] = None
) -> Optional[str]:
    """
    Reads environment variable with primary lookup key_new (e.g. YARTRADER_ENV).
    If key_new is missing, falls back to key_old (e.g. TRADEYAR_ENV).
    Emits a migration fallback warning if key_old is used.
    """
    val_new = os.environ.get(key_new)
    if val_new is not None:
        return val_new

    if key_old:
        val_old = os.environ.get(key_old)
        if val_old is not None:
            msg = (
                f"[DEPRECATION WARNING] Environment variable '{key_old}' is deprecated. "
                f"Please update your deployment environment to use '{key_new}' instead."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            logger.warning(msg)
            return val_old

    return default
