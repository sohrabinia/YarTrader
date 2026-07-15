from typing import Any, Dict, Optional
from src.Infrastructure.Configuration.environment import EnvironmentType, get_current_environment
from src.Infrastructure.Configuration.settings import (
    BaseSettings,
    DevelopmentSettings,
    SandboxSettings,
    ProductionSettings,
    SimulationSettings
)

class ConfigurationManager:
    """Manages active runtime configuration as a singleton with environment support."""
    _instance: Optional[BaseSettings] = None
    _active_env: Optional[EnvironmentType] = None

    @classmethod
    def get_config(cls, environment: Optional[EnvironmentType] = None, overrides: Optional[Dict[str, Any]] = None) -> BaseSettings:
        """Retrieves or instantiates the configuration settings for the active/requested environment."""
        if cls._instance is None or overrides is not None or environment is not None:
            env = environment or get_current_environment()
            cls._active_env = env
            if env == EnvironmentType.DEVELOPMENT:
                cls._instance = DevelopmentSettings(overrides)
            elif env == EnvironmentType.TEST:
                cls._instance = SandboxSettings(overrides)
            elif env == EnvironmentType.PRODUCTION:
                cls._instance = ProductionSettings(overrides)
            elif env == EnvironmentType.SIMULATION:
                cls._instance = SimulationSettings(overrides)
            else:
                cls._instance = BaseSettings(overrides)
        return cls._instance

    @classmethod
    def get_active_environment(cls) -> Optional[EnvironmentType]:
        """Gets the active environment."""
        if cls._active_env is None:
            cls._active_env = get_current_environment()
        return cls._active_env

    @classmethod
    def reset(cls) -> None:
        """Resets the singleton configuration instance."""
        cls._instance = None
        cls._active_env = None
