import os
from typing import Any, Dict

class ConfigurationLoader:
    """Safely loads application configuration variables with environment fallbacks."""
    def __init__(self, defaults: Dict[str, Any] = None) -> None:
        self._config = defaults or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a config key with fallback to env or provided default value."""
        # Check environment first
        env_val = os.environ.get(key)
        if env_val is not None:
            return env_val
        return self._config.get(key, default)
