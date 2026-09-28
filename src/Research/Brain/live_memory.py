"""Shared persistent memory instance for the canonical live cognitive learning loop."""

import os

from src.Research.Brain.memory import MarketMemorySystem


def _live_memory_storage_dir() -> str:
    """Resolve live Brain memory under the canonical YarTrader runtime storage."""
    try:
        from src.Application.Deployment.storage import YarTraderStorageManager
        runtime_dir = YarTraderStorageManager.get_manager().get_runtime_dir()
        return os.path.join(runtime_dir, "brain_memory")
    except Exception:
        # Keep import/startup fail-safe for isolated tests and offline tooling.
        return os.path.join("runtime_logs", "brain_memory")


_global_live_memory = MarketMemorySystem(storage_dir=_live_memory_storage_dir())


def get_live_memory_system() -> MarketMemorySystem:
    """Returns the process-wide memory instance used by live ResearchRuntime and dashboard."""
    return _global_live_memory
