from enum import Enum
import os

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
    SIMULATION = "simulation"

def get_current_environment() -> EnvironmentType:
    """Retrieves the active environment from environment variables or defaults to DEVELOPMENT."""
    env_str = os.environ.get("TRADEYAR_ENV", os.environ.get("RG_ENV", "development")).lower()
    for env in EnvironmentType:
        if env.value == env_str:
            return env
    return EnvironmentType.DEVELOPMENT
