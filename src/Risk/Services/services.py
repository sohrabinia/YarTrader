from datetime import datetime
from typing import Dict
from src.Risk.Interfaces.interfaces import IRiskEngine, IRiskEvaluator
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk

class RiskEvaluator(IRiskEvaluator):
    """
    Evaluates proposed portfolio allocation structures against safety boundaries.
    """
    def is_allocation_safe(self, weights: Dict[str, float], profile: RiskProfile) -> bool:
        # Rule 1: No negative weights (short selling)
        if any(w < -0.0001 for w in weights.values()):
            return False

        # Rule 2: Single asset exposure must not exceed threshold
        for symbol, w in weights.items():
            if w > profile.MaxSingleAssetWeight:
                return False

        # Rule 3: Total weights sum must fit leverage limit
        total_w = sum(weights.values())
        if total_w > profile.MaxLeverageFactor:
            return False

        return True


class RiskAnalyzer(IRiskEngine):
    """
    Orchestrates the risk assessment workflow, combining risk evaluators and statistics.
    """
    def __init__(self) -> None:
        self._evaluator = RiskEvaluator()

    def analyze_risk(self, weights: Dict[str, float], profile: RiskProfile) -> RiskAssessment:
        is_safe = self._evaluator.is_allocation_safe(weights, profile)

        # Calculate mock/standard statistical metrics
        metrics = PortfolioRisk(
            ExpectedVolatility=0.155,
            HistoricalDrawdown=0.082,
            VaR=0.045
        )

        notes = (
            f"Portfolio allocation assessed successfully against profile '{profile.RiskToleranceLevel}'. "
            f"Result: {'Approved' if is_safe else 'Rejected'}."
        )

        return RiskAssessment(
            IsApproved=is_safe,
            RiskProfileName=profile.RiskToleranceLevel,
            PortfolioRiskMetrics=metrics,
            AssessmentNotes=notes,
            AssessedAt=datetime.now()
        )
