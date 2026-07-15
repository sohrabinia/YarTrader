import os
import signal
import sys
from typing import Any, Dict, Optional
from src.Infrastructure.Configuration.environment import EnvironmentType, get_current_environment
from src.Application.Runtime.host import RuntimeHost

class RuntimeLauncher:
    """Entry point bootstrapper responsible for launching and orchestrating the active RuntimeHost."""
    def __init__(self) -> None:
        self.active_host: Optional[RuntimeHost] = None

    def launch(self, environment_override: Optional[EnvironmentType] = None, overrides: Optional[Dict[str, Any]] = None) -> RuntimeHost:
        """Launches and boots up the RuntimeHost under the active environment."""
        env = environment_override or get_current_environment()
        host = RuntimeHost(environment=env)
        self.active_host = host

        # Register OS signal handlers
        self._register_signal_handlers()

        # Startup the host
        host.startup(overrides=overrides)
        return host

    def _register_signal_handlers(self) -> None:
        """Registers system SIGINT/SIGTERM handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            if self.active_host:
                try:
                    self.active_host.stop()
                    self.active_host.shutdown()
                except Exception:
                    pass
            sys.exit(0)

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        except (ValueError, OSError):
            # Safe ignore if signals cannot be bound (e.g. running outside of main thread in testing)
            pass
