import os
import json
from typing import Dict, Any

_VERSION_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "version.json")

def get_application_version_info() -> Dict[str, Any]:
    """
    Returns single authoritative application version metadata.
    Reads from config/version.json with environment variable overrides.
    """
    version_data = {
        "application": "YarTrader",
        "version": "7.0",
        "commit": "ac2d3ec98232c098be8a445934b8222aca711a34",
        "environment": "production"
    }

    if os.path.exists(_VERSION_FILE_PATH):
        try:
            with open(_VERSION_FILE_PATH, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                version_data.update(file_data)
        except Exception:
            pass

    # Environment variable overrides if present
    env_version = os.environ.get("APP_VERSION") or os.environ.get("YARTRADER_VERSION")
    if env_version:
        version_data["version"] = env_version

    env_commit = os.environ.get("GIT_COMMIT") or os.environ.get("COMMIT_SHA")
    if env_commit:
        version_data["commit"] = env_commit

    env_type = os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT")
    if env_type:
        version_data["environment"] = env_type

    return version_data

def get_current_version_string() -> str:
    """Returns just the version string (e.g., '7.0')."""
    return str(get_application_version_info().get("version", "7.0"))
