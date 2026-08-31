from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.Application.Agents.context import AgentContext
    from src.Application.Agents.communication import IntelligenceMessage


class IIntelligenceAgent(ABC):
    """
    Standard interface contract that all YarTrader Intelligence Agents must implement.
    Strictly forbids access to any execution/trading/order mechanics.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier of the agent."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the agent."""
        pass

    @property
    @abstractmethod
    def responsibility(self) -> str:
        """Formal responsibility description of the agent."""
        pass

    @property
    def domain(self) -> str:
        """Operating domain of the agent."""
        return getattr(self, "_domain", "general")

    @property
    def version(self) -> str:
        """Version string of the agent."""
        return getattr(self, "_version", "1.0.0")

    @property
    def autonomy_level(self) -> str:
        """Autonomy Level (L0 - L4). Defaults to L1."""
        return getattr(self, "_autonomy_level", "L1")

    @property
    def lifecycle_status(self) -> str:
        """Lifecycle State (PROPOSED, DESIGNED, IMPLEMENTED, TESTED, SHADOW, APPROVED, ACTIVE, SUSPENDED, DEPRECATED)."""
        return getattr(self, "_lifecycle_status", "IMPLEMENTED")

    def set_lifecycle_status(self, status: str) -> None:
        """Updates agent lifecycle status."""
        valid_statuses = {
            "PROPOSED", "DESIGNED", "IMPLEMENTED", "TESTED",
            "SHADOW", "APPROVED", "ACTIVE", "SUSPENDED", "DEPRECATED"
        }
        if status.upper() not in valid_statuses:
            raise ValueError(f"Invalid lifecycle status '{status}'. Allowed: {valid_statuses}")
        self._lifecycle_status = status.upper()

    def set_autonomy_level(self, level: str) -> None:
        """Updates agent autonomy level."""
        valid_levels = {"L0", "L1", "L2", "L3", "L4"}
        if level.upper() not in valid_levels:
            raise ValueError(f"Invalid autonomy level '{level}'. Allowed: {valid_levels}")
        self._autonomy_level = level.upper()

    @abstractmethod
    def process(self, context: "AgentContext", message: "IntelligenceMessage") -> "IntelligenceMessage":
        """
        Processes the shared AgentContext and incoming message,
        and returns a descriptive output IntelligenceMessage.
        """
        pass
