from enum import Enum
import threading

class LifecycleState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    SHUTDOWN = "SHUTDOWN"

class RuntimeLifecycle:
    """Manages the formal state and transition boundaries of the application runtime."""
    def __init__(self) -> None:
        self._state = LifecycleState.UNINITIALIZED
        self._lock = threading.Lock()

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def initialize(self) -> None:
        """Transitions state to INITIALIZED."""
        with self._lock:
            if self._state != LifecycleState.UNINITIALIZED:
                raise ValueError(f"Lifecycle Transition Error: Cannot initialize from state '{self._state}'")
            self._state = LifecycleState.INITIALIZED

    def start(self) -> None:
        """Transitions state to RUNNING."""
        with self._lock:
            if self._state != LifecycleState.INITIALIZED:
                raise ValueError(f"Lifecycle Transition Error: Cannot start from state '{self._state}'")
            self._state = LifecycleState.RUNNING

    def stop(self) -> None:
        """Transitions state to STOPPED."""
        with self._lock:
            if self._state != LifecycleState.RUNNING:
                raise ValueError(f"Lifecycle Transition Error: Cannot stop from state '{self._state}'")
            self._state = LifecycleState.STOPPED

    def shutdown(self) -> None:
        """Transitions state to SHUTDOWN."""
        with self._lock:
            if self._state not in (LifecycleState.STOPPED, LifecycleState.INITIALIZED, LifecycleState.UNINITIALIZED):
                raise ValueError(f"Lifecycle Transition Error: Cannot shutdown from state '{self._state}'")
            self._state = LifecycleState.SHUTDOWN
