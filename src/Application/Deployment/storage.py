import os
from typing import Optional


class TradeYarStorageManager:
    """Manages isolated storage paths strictly derived from the configured storage root."""

    _instance: Optional["TradeYarStorageManager"] = None

    def __init__(self, storage_root: Optional[str] = None) -> None:
        if storage_root:
            self._storage_root = storage_root
        else:
            self._storage_root = os.getenv("YarTraderStorageRoot") or os.getenv("TradeYarStorageRoot")
            if not self._storage_root:
                # Default fallback for Windows (H:\YarTraderAI\) or Unix (/tmp/YarTraderAI/)
                if os.name == "nt":
                    self._storage_root = "H:\\YarTraderAI\\"
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
    def get_manager(cls, root_override: Optional[str] = None) -> "TradeYarStorageManager":
        if cls._instance is None or root_override:
            cls._instance = TradeYarStorageManager(root_override)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @property
    def storage_root(self) -> str:
        return self._storage_root

    def get_log_dir(self) -> str:
        return self._logs_dir

    def get_reports_dir(self) -> str:
        return self._reports_dir

    def get_runtime_dir(self) -> str:
        return self._runtime_dir

    def get_cache_dir(self) -> str:
        return self._cache_dir

    def get_data_dir(self) -> str:
        return self._data_dir

    def get_diagnostics_dir(self) -> str:
        return self._diagnostics_dir

    def get_temp_dir(self) -> str:
        return self._temp_dir
