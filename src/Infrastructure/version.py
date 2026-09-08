import os
import json
from typing import Dict, Any

_VERSION_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "version.json")

import subprocess

def _get_git_commit_sha() -> str:
    """Attempts to resolve the current Git repository HEAD commit SHA."""
    try:
        repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def get_application_version_info() -> Dict[str, Any]:
    """
    Returns single authoritative application version metadata.
    Canonical precedence order:
    1. Explicit environment variable (GIT_COMMIT or COMMIT_SHA)
    2. Dynamic Git repository HEAD resolution
    3. config/version.json fallback
    """
    version_data = {
        "application": "YarTrader",
        "version": "7.0",
        "commit": "49546b10db0964da145df24e1d35365f4833d340",
        "environment": "production"
    }

    if os.path.exists(_VERSION_FILE_PATH):
        try:
            with open(_VERSION_FILE_PATH, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                version_data.update(file_data)
        except Exception:
            pass

    # Dynamic Git resolution if available
    git_sha = _get_git_commit_sha()
    if git_sha:
        version_data["commit"] = git_sha

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
