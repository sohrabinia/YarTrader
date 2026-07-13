from abc import ABC, abstractmethod
from typing import Dict
from src.Risk.Models.models import RiskProfile, RiskAssessment

class IRiskEngine(ABC):
    """Interface defining operations for executing robust risk audit processes."""
    @abstractmethod
    def analyze_risk(self, weights: Dict[str, float], profile: RiskProfile) -> RiskAssessment:
        """Runs thorough multi-factor risk assessments over target weight allocations."""
        pass


class IRiskEvaluator(ABC):
    """Interface defining basic risk threshold checks."""
    @abstractmethod
    def is_allocation_safe(self, weights: Dict[str, float], profile: RiskProfile) -> bool:
        """Returns True if the proposed weights fit strictly inside safety thresholds."""
        pass
