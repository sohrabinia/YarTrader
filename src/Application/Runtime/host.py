import logging
from typing import Any, Dict, Optional
from src.Infrastructure.Configuration.environment import EnvironmentType
from src.Infrastructure.Configuration.config import ConfigurationManager
from src.Infrastructure.DI.container import container_instance
from src.Infrastructure.DI.registrations import register_services
from src.Application.Runtime.lifecycle import RuntimeLifecycle, LifecycleState

class RuntimeHost:
    """Coordinates application startup, configuration loading, dependency injection registrations, and lifecycle execution."""
    def __init__(self, environment: Optional[EnvironmentType] = None) -> None:
        self.environment = environment
        self.lifecycle = RuntimeLifecycle()
        self.config = None

    def startup(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Starts up the host, initializing configuration, registering services, and executing lifecycle transitions."""
        # 1. Initialize lifecycle
        self.lifecycle.initialize()

        # 2. Load Configuration
        self.config = ConfigurationManager.get_config(environment=self.environment, overrides=overrides)

        # 3. Register DI Services
        register_services(container=container_instance, environment=self.environment)

        # 4. Start lifecycle
        self.lifecycle.start()

    def stop(self) -> None:
        """Stops active host services and updates lifecycle state."""
        self.lifecycle.stop()

    def shutdown(self) -> None:
        """Shuts down and releases host and DI container resources."""
        self.lifecycle.shutdown()
        # Clear DI registrations
        container_instance.clear()
        ConfigurationManager.reset()
