import os
from typing import Any, Dict
from src.Infrastructure.exceptions import ConfigurationException

class ConfigurationLoader:
    """Safely loads and validates application configuration variables with environment fallbacks."""
    def __init__(self, defaults: Dict[str, Any] = None) -> None:
        self._config = defaults or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a config key with fallback to env or defaults."""
        env_val = os.environ.get(key)
        if env_val is not None:
            return env_val
        return self._config.get(key, default)

    def get_required(self, key: str) -> Any:
        """Retrieves a config key; immediately throws ConfigurationException if missing."""
        val = self.get(key)
        if val is None:
            raise ConfigurationException(f"Configuration Error: Critical key '{key}' is missing from config environment.")
        return val
