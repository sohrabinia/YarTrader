import os
from typing import Any, Dict
from src.Infrastructure.exceptions import ValidationException

class BaseSettings:
    """Base Configuration Settings defining core runtime variables."""
    def __init__(self, overrides: Dict[str, Any] = None) -> None:
        self._overrides = overrides or {}
        self.simulation_mode: bool = True
        self.lookback_days: int = 10
        self.api_timeout_sec: float = 5.0
        self.max_retries: int = 3
        self.log_level: str = "INFO"
        self.storage_root: str = "C:\\YarTraderAI\\" if os.name == "nt" else "/tmp/YarTraderAI/"
        self.db_token: str = "dev-token-12345"
        self.tick_chart_analysis_enabled: bool = False
        self._load_and_validate()

    def _load_and_validate(self) -> None:
        # Load from env vars or overrides
        self.simulation_mode = bool(self._overrides.get("simulation_mode", os.environ.get("TRADEYAR_SIMULATION_MODE", "True") == "True"))
        if not self.simulation_mode:
            raise ValidationException(
                "APES-FIN Compliance Error: Real trading is strictly prohibited. simulation_mode must be set to True."
            )

        try:
            self.lookback_days = int(self._overrides.get("lookback_days", os.environ.get("RG_LOOKBACK_DAYS", self.lookback_days)))
            self.api_timeout_sec = float(self._overrides.get("api_timeout_sec", os.environ.get("RG_API_TIMEOUT", self.api_timeout_sec)))
            self.max_retries = int(self._overrides.get("max_retries", os.environ.get("RG_MAX_RETRIES", self.max_retries)))
        except ValueError as e:
            raise ValidationException(f"Configuration Error: Numerical parameters must be numeric: {str(e)}")

        if self.lookback_days <= 0 or self.lookback_days > 365:
            raise ValidationException("Configuration Error: Lookback days must be within [1, 365].")
        if self.api_timeout_sec <= 0.0 or self.api_timeout_sec > 60.0:
            raise ValidationException("Configuration Error: API timeout must be within [0.1s, 60.0s].")
        if self.max_retries < 0 or self.max_retries > 10:
            raise ValidationException("Configuration Error: Max connection retries must be within [0, 10].")

        self.log_level = str(self._overrides.get("log_level", os.environ.get("RG_LOG_LEVEL", self.log_level))).upper()
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValidationException(f"Configuration Error: Invalid log level '{self.log_level}'.")

        # Storage Root Isolation
        default_root = "C:\\YarTraderAI\\" if os.name == "nt" else "/tmp/YarTraderAI/"
        self.storage_root = str(self._overrides.get("storage_root", os.environ.get("YarTraderStorageRoot", os.environ.get("TradeYarStorageRoot", default_root))))
        if not self.storage_root:
            self.storage_root = default_root

        self.db_token = str(self._overrides.get("db_token", os.environ.get("RG_DB_SECURE_TOKEN", self.db_token)))

        self.tick_chart_analysis_enabled = self._overrides.get(
            "tick_chart_analysis_enabled",
            os.environ.get("TICK_CHART_ANALYSIS_ENABLED", "False") == "True"
        )

        # Scan for forbidden live trading indicators
        forbidden_keywords = ["buy_signal", "sell_signal", "place_order", "execute_trade", "open_position", "send_transaction"]
        for key, val in self._overrides.items():
            val_str = str(val).lower()
            for kw in forbidden_keywords:
                if kw in val_str:
                    raise ValidationException(f"Safety Violation: Setting contains forbidden active-trading indicator '{kw}'.")

    def to_dict(self) -> Dict[str, Any]:
        """Returns a copy of config settings as a dictionary."""
        return {
            "simulation_mode": self.simulation_mode,
            "lookback_days": self.lookback_days,
            "api_timeout_sec": self.api_timeout_sec,
            "max_retries": self.max_retries,
            "log_level": self.log_level,
            "storage_root": self.storage_root,
            "db_token": self.db_token,
            "tick_chart_analysis_enabled": self.tick_chart_analysis_enabled
        }


class DevelopmentSettings(BaseSettings):
    """Configuration settings specific to Development environments."""
    def __init__(self, overrides: Dict[str, Any] = None) -> None:
        # Default overrides for Dev
        dev_defaults = {
            "log_level": "DEBUG",
            "lookback_days": 5,
            "api_timeout_sec": 10.0,
            "max_retries": 2,
            "db_token": "dev-token-99999"
        }
        if overrides:
            dev_defaults.update(overrides)
        super().__init__(dev_defaults)


class SandboxSettings(BaseSettings):
    """Configuration settings specific to Test environments."""
    def __init__(self, overrides: Dict[str, Any] = None) -> None:
        # Default overrides for Test
        test_defaults = {
            "log_level": "DEBUG",
            "lookback_days": 10,
            "api_timeout_sec": 2.0,
            "max_retries": 1,
            "db_token": "test-token-77777"
        }
        if overrides:
            test_defaults.update(overrides)
        super().__init__(test_defaults)


class ProductionSettings(BaseSettings):
    """Configuration settings specific to Production environments."""
    def __init__(self, overrides: Dict[str, Any] = None) -> None:
        # Default overrides for Prod
        prod_defaults = {
            "log_level": "INFO",
            "lookback_days": 15,
            "api_timeout_sec": 5.0,
            "max_retries": 3,
            "db_token": "prod-token-secure"
        }
        if overrides:
            prod_defaults.update(overrides)
        super().__init__(prod_defaults)


class SimulationSettings(BaseSettings):
    """Configuration settings specific to Simulation environments."""
    def __init__(self, overrides: Dict[str, Any] = None) -> None:
        # Default overrides for Simulation
        sim_defaults = {
            "log_level": "INFO",
            "lookback_days": 30,
            "api_timeout_sec": 5.0,
            "max_retries": 5,
            "db_token": "sim-token-sandbox"
        }
        if overrides:
            sim_defaults.update(overrides)
        super().__init__(sim_defaults)
