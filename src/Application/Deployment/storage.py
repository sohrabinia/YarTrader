import os
from datetime import datetime, timezone
from typing import Optional

from src.Application.Deployment.artifact_store import YarTraderArtifactStore


def is_research_snapshot_fresh(snapshot: dict, now: Optional[datetime] = None) -> bool:
    """Reject stale or future-dated research snapshots before presenting actionable signals."""
    if not isinstance(snapshot, dict):
        return False
    raw_stamp = snapshot.get("timestamp") or snapshot.get("created_at")
    if not raw_stamp:
        return False
    try:
        stamp = datetime.fromisoformat(str(raw_stamp).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.astimezone()
        stamp = stamp.astimezone(timezone.utc)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.astimezone()
        age_seconds = (current.astimezone(timezone.utc) - stamp).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return False
    if age_seconds < -300:
        return False
    timeframe = str(snapshot.get("timeframe") or "H1").upper()
    max_age_seconds = {
        "M1": 5 * 60, "M5": 15 * 60, "M15": 45 * 60,
        "M30": 90 * 60, "H1": 3 * 3600, "H4": 12 * 3600,
        "D1": 3 * 86400, "W1": 14 * 86400, "MN1": 45 * 86400,
    }.get(timeframe, 3 * 3600)
    return age_seconds <= max_age_seconds


class YarTraderStorageManager:
    """Manages isolated storage paths strictly derived from the configured storage root."""

    _instance: Optional["YarTraderStorageManager"] = None

    def __init__(self, storage_root: Optional[str] = None) -> None:
        if storage_root:
            self._storage_root = storage_root
        else:
            self._storage_root = os.getenv("YarTraderStorageRoot") or os.getenv("TradeYarStorageRoot")
            if not self._storage_root:
                # Default fallback for Windows (C:\YarTraderAI\) or Unix (/tmp/YarTraderAI/)
                if os.name == "nt":
                    self._storage_root = "C:\\YarTraderAI\\"
                else:
                    self._storage_root = "/tmp/YarTraderAI/"

        # Standardized subfolders under YarTraderStorageRoot
        self._logs_dir = os.path.join(self._storage_root, "Logs")
        self._reports_dir = os.path.join(self._storage_root, "Reports")
        self._runtime_dir = os.path.join(self._storage_root, "Runtime")
        self._cache_dir = os.path.join(self._storage_root, "Cache")
        self._data_dir = os.path.join(self._storage_root, "Data")
        self._diagnostics_dir = os.path.join(self._storage_root, "Diagnostics")
        self._temp_dir = os.path.join(self._storage_root, "Temp")

    @classmethod
    def get_manager(cls, root_override: Optional[str] = None) -> "YarTraderStorageManager":
        if cls._instance is None or root_override:
            cls._instance = YarTraderStorageManager(root_override)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @property
    def storage_root(self) -> str:
        return self._storage_root

    def get_log_dir(self) -> str:
        return self._logs_dir

    def get_logs_dir(self) -> str:
        return self._logs_dir

    def get_reports_dir(self) -> str:
        return self._reports_dir

    def get_runtime_dir(self) -> str:
        return self._runtime_dir

    def get_research_snapshots_dir(self) -> str:
        """Resolve the canonical persisted research snapshots directory, with legacy read fallbacks."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        candidates = [
            os.path.join(self._runtime_dir, "research_logs", "research_snapshots"),
            os.path.join(project_root, "storage", "Runtime", "research_logs", "research_snapshots"),
            os.path.join(project_root, "runtime_logs", "research_snapshots"),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]

    def get_cache_dir(self) -> str:
        return self._cache_dir

    def get_data_dir(self) -> str:
        return self._data_dir

    def get_diagnostics_dir(self) -> str:
        return self._diagnostics_dir

    def get_temp_dir(self) -> str:
        return self._temp_dir

    def get_artifact_store(self) -> YarTraderArtifactStore:
        """Return the universal adaptive artifact store under the configured data root."""
        return YarTraderArtifactStore(os.path.join(self._data_dir, "artifacts"))


# Backward compatibility alias
TradeYarStorageManager = YarTraderStorageManager
