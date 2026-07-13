from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.Application.Agents.context import AgentContext
    from src.Application.Agents.communication import IntelligenceMessage


class IIntelligenceAgent(ABC):
    """
    Standard interface contract that all Phase 21 Intelligence Agents must implement.
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

    @abstractmethod
    def process(self, context: "AgentContext", message: "IntelligenceMessage") -> "IntelligenceMessage":
        """
        Processes the shared AgentContext and incoming message,
        and returns a descriptive output IntelligenceMessage.
        """
        pass
