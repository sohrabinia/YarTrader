import os
from typing import Any, Dict, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.deployment import SecretsVault


class ProductionConfig:
    """Production-ready structured configuration settings for RG_V3_AI."""

    def __init__(self, settings_dict: Optional[Dict[str, Any]] = None) -> None:
        self._settings = settings_dict or {}
        self.vault = SecretsVault()
        self._validate_and_initialize()

    def _validate_and_initialize(self) -> None:
        # Load environment-based parameters with safe defaults
        self.environment = os.getenv("RG_ENV", self._settings.get("ENVIRONMENT", "production")).lower()
        if self.environment not in ("production", "staging", "development"):
            raise ValidationException(f"Configuration Error: Invalid environment '{self.environment}'.")

        # Load technical params with safe defaults and validation checks
        try:
            self.lookback_days = int(os.getenv("RG_LOOKBACK_DAYS", self._settings.get("LOOKBACK_DAYS", 15)))
            self.api_timeout_sec = float(os.getenv("RG_API_TIMEOUT", self._settings.get("API_TIMEOUT", 5.0)))
            self.max_retries = int(os.getenv("RG_MAX_RETRIES", self._settings.get("MAX_RETRIES", 3)))
        except ValueError as e:
            raise ValidationException(f"Configuration Error: Numerical parameters must be numeric: {str(e)}")

        # Strict checks on bounds
        if self.lookback_days <= 0 or self.lookback_days > 365:
            raise ValidationException("Configuration Error: Lookback days must be within [1, 365].")
        if self.api_timeout_sec <= 0.0 or self.api_timeout_sec > 60.0:
            raise ValidationException("Configuration Error: API timeout must be within [0.1s, 60.0s].")
        if self.max_retries < 0 or self.max_retries > 10:
            raise ValidationException("Configuration Error: Max connection retries must be within [0, 10].")

        # Log level verification
        self.log_level = os.getenv("RG_LOG_LEVEL", self._settings.get("LOG_LEVEL", "INFO")).upper()
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValidationException(f"Configuration Error: Invalid log level '{self.log_level}'.")

        # Set up a secure default database key in vault
        default_db_key = os.getenv("RG_DB_SECURE_TOKEN", self._settings.get("DB_SECURE_TOKEN", "secure-token-12345"))
        self.vault.store_secret("db_token", default_db_key)

    def runtime_check(self) -> bool:
        """Executes a self-diagnostic check on system configuration parameters."""
        if not self.environment:
            return False
        if self.lookback_days <= 0:
            return False
        if not self.vault.retrieve_secret("db_token"):
            return False
        return True


class ConfigManager:
    """Global manager for production configurations."""
    _instance: Optional[ProductionConfig] = None

    @classmethod
    def get_config(cls, overrides: Optional[Dict[str, Any]] = None) -> ProductionConfig:
        """Returns or instantiates the singleton ProductionConfig."""
        if cls._instance is None or overrides:
            cls._instance = ProductionConfig(overrides)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Resets the config instance."""
        cls._instance = None
