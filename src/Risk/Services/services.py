from datetime import datetime
from typing import Dict, List
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


class RiskAssessmentFramework:
    """
    Comprehensive framework enabling deep assessment analytics, multi-portfolio audits,
    and historical risk reporting for future advanced asset management systems.
    """
    def __init__(self) -> None:
        self._analyzer = RiskAnalyzer()
        self._reports: List[RiskAssessment] = []

    def perform_portfolio_audit(self, weights: Dict[str, float], profile: RiskProfile) -> RiskAssessment:
        """Analyzes weights against risk profile and records the assessment report in history."""
        report = self._analyzer.analyze_risk(weights, profile)
        self._reports.append(report)
        return report

    def list_assessment_history(self) -> List[RiskAssessment]:
        """Queries list of all processed risk assessment reports."""
        return self._reports

    def audit_leverage_exposure(self, weights: Dict[str, float]) -> float:
        """Helper to calculate total leverage exposure ratio."""
        return sum(weights.values())
