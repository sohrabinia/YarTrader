import os
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from src.Application.Deployment.storage import YarTraderStorageManager

# Ensure logs/runtime directory exists
RUNTIME_LOG_DIR = os.path.join(YarTraderStorageManager.get_manager().get_log_dir(), "runtime")
os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)

class RuntimeStateManager:
    """Thread-safe centralized manager for storing and querying active runtime statuses with transition logging."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RuntimeStateManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.state_lock = threading.Lock()
        self.state: Dict[str, Any] = {
            "worker_status": "Stopped",
            "research_status": "Stopped",
            "intelligence_status": "Stopped",
            "shadow_status": "Stopped",
            "last_cycle_time": None
        }

    def _log_state_transition(self, key: str, old_val: Any, new_val: Any) -> None:
        """Logs any worker state transition to logs/runtime/runtime_state.log."""
        # Map state keys to friendly worker names as requested
        key_mapping = {
            "worker_status": "ServiceHost",
            "research_status": "ResearchWorker",
            "intelligence_status": "IntelligenceWorker",
            "shadow_status": "ShadowWorker"
        }
        worker_name = key_mapping.get(key, key)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {worker_name} | {old_val} -> {new_val}\n"
        try:
            with open(os.path.join(RUNTIME_LOG_DIR, "runtime_state.log"), "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

    def update_state(self, key: str, value: Any) -> None:
        """Updates a state key safely under lock and logs transitions."""
        with self.state_lock:
            old_val = self.state.get(key)
            if old_val != value:
                self.state[key] = value
                # Only log transitions for status keys
                if key in ["worker_status", "research_status", "intelligence_status", "shadow_status"]:
                    self._log_state_transition(key, old_val, value)

    def update_multiple(self, updates: Dict[str, Any]) -> None:
        """Applies multiple state updates safely under lock and logs transitions."""
        with self.state_lock:
            for key, value in updates.items():
                old_val = self.state.get(key)
                if old_val != value:
                    self.state[key] = value
                    if key in ["worker_status", "research_status", "intelligence_status", "shadow_status"]:
                        self._log_state_transition(key, old_val, value)

    def get_state(self) -> Dict[str, Any]:
        """Returns a snapshot copy of the central runtime state under lock."""
        with self.state_lock:
            return self.state.copy()

    def get_key(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieves a single state key value under lock."""
        with self.state_lock:
            return self.state.get(key, default)


# Global singleton instance of central runtime state
central_runtime_state = RuntimeStateManager()
