from abc import ABC, abstractmethod
from typing import Optional
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyDefinition

class IStrategyEngine(ABC):
    """Interface defining operations for high-level strategy workflow management."""
    @abstractmethod
    def process_candidate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        """Processes and runs workflow tracking over a StrategyCandidate."""
        pass


class IStrategyEvaluator(ABC):
    """Interface defining core criteria assessment and scoring contracts."""
    @abstractmethod
    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        """Scores a Candidate based on strict suitability evaluation matrices."""
        pass


class IStrategyRegistry(ABC):
    """Interface defining database registries to store/query approved strategy concepts."""
    @abstractmethod
    def register_strategy(self, definition: StrategyDefinition) -> None:
        """Stores a new StrategyDefinition safely in repository."""
        pass

    @abstractmethod
    def get_strategy(self, strategy_id: str) -> Optional[StrategyDefinition]:
        """Retrieves a StrategyDefinition by unique identifier."""
        pass


class IRuleValidator(ABC):
    """Interface defining structural schema validator for strategy definitions."""
    @abstractmethod
    def validate_structure(self, definition: StrategyDefinition) -> bool:
        """Checks structural attributes only; guarantees no execution/trading rules are embedded."""
        pass
