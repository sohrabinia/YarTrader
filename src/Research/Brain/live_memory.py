"""Shared persistent memory instance for the canonical live cognitive learning loop."""
from src.Research.Brain.memory import MarketMemorySystem

_global_live_memory = MarketMemorySystem()

def get_live_memory_system() -> MarketMemorySystem:
    """Returns the process-wide memory instance used by live ResearchRuntime and dashboard."""
    return _global_live_memory
