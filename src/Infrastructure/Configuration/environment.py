from enum import Enum
import os

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
    SIMULATION = "simulation"

def get_current_environment() -> EnvironmentType:
    """
    Retrieves active environment from environment variables.
    Fails closed to EnvironmentType.PRODUCTION if configuration is missing or unrecognized.
    """
    raw_env = os.environ.get("YARTRADER_ENV") or os.environ.get("TRADEYAR_ENV") or os.environ.get("RG_ENV")
    if not raw_env:
        return EnvironmentType.PRODUCTION

    env_str = raw_env.strip().lower()
    for env in EnvironmentType:
        if env.value == env_str:
            return env

    return EnvironmentType.PRODUCTION
