from abc import ABC, abstractmethod
from src.Decision.Models.models import DecisionContext, DecisionResult

class IDecisionEngine(ABC):
    """Interface defining operations for evaluating strategy and risk inputs to produce allocation decisions."""
    @abstractmethod
    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        """Processes a DecisionContext to return a finalized DecisionResult."""
        pass
