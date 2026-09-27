import os
from typing import Optional, Any


def get_env_compat(
    key_new: str,
    key_old: Optional[str] = None,
    default: Optional[Any] = None
) -> Optional[str]:
    """Read only the canonical environment variable.

    The legacy compatibility fallback has been retired. key_old is retained
    in the signature only to avoid breaking stale callers while ensuring legacy
    environment variables can never influence runtime configuration.
    """
    del key_old
    return os.environ.get(key_new, default)
