import threading
from typing import Dict, Any, Optional
from datetime import datetime

class RuntimeStateManager:
    """Thread-safe centralized manager for storing and querying active runtime statuses."""
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

    def update_state(self, key: str, value: Any) -> None:
        """Updates a state key safely under lock."""
        with self.state_lock:
            self.state[key] = value

    def update_multiple(self, updates: Dict[str, Any]) -> None:
        """Applies multiple state updates safely under lock."""
        with self.state_lock:
            self.state.update(updates)

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
