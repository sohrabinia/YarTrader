from abc import ABC, abstractmethod
from typing import Dict
from src.Core.entities import DecisionReport

class IPendingAllocationTracker(ABC):
    """
    Abstract interface for tracking target portfolio changes over time.
    Strictly passive record-keeping; no live execution or signal generation occurs.
    """
    @abstractmethod
    def record_target_allocation(self, report: DecisionReport) -> None:
        """Saves target asset weights to system logs or configuration stores."""
        pass

    @abstractmethod
    def get_current_target_allocation(self) -> Dict[str, float]:
        """Retrieves the current active target allocation weights."""
        pass
