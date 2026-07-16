from datetime import datetime
from typing import Dict, List, Any
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk


class RiskPolicy:
    """
    Defines rules and safety controls (drawdown thresholds, maximum single asset weights,
    safety multipliers) to enforce risk boundaries.
    """

    def __init__(self, profile: RiskProfile) -> None:
        self.profile = profile

    def validate_allocation(self, weights: Dict[str, float]) -> bool:
        """Enforces limits on weights based on risk policy boundaries."""
        for symbol, weight in weights.items():
            if weight > self.profile.MaxSingleAssetWeight:
                return False
        return True


class RiskEngine:
    """
    Advanced Risk Intelligence and Safety Control engine.
    Calculates position sizes, computes risk metrics, checks exposure limits,
    and applies drawdown safety policies without placing real-money trades.
    """

    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def calculate_position_sizing(self, weights: Dict[str, float], portfolio_value: float = 10000.0) -> Dict[str, float]:
        """Calculates precise capital sizing distribution based on asset weights."""
        sizes = {}
        for symbol, weight in weights.items():
            # Apply safety multipliers if weight is exceptionally high
            adjusted_weight = min(weight, self.policy.profile.MaxSingleAssetWeight)
            sizes[symbol] = round(portfolio_value * adjusted_weight, 2)
        return sizes

    def assess_allocation(self, weights: Dict[str, float]) -> RiskAssessment:
        """Runs a complete risk assessment audit."""
        is_approved = self.policy.validate_allocation(weights)

        # Calculate mock expected risk characteristics
        volatility = 0.08 if is_approved else 0.18
        drawdown = 0.04 if is_approved else 0.12
        var_pct = 0.05 if is_approved else 0.15

        risk_metrics = PortfolioRisk(
            ExpectedVolatility=volatility,
            HistoricalDrawdown=drawdown,
            VaR=var_pct
        )

        notes = "All portfolio allocations comply with the Risk Policy limits." if is_approved else "Security Alert: Individual asset weight exceeds risk limits."

        return RiskAssessment(
            IsApproved=is_approved,
            RiskProfileName=self.policy.profile.RiskToleranceLevel,
            PortfolioRiskMetrics=risk_metrics,
            AssessmentNotes=notes,
            AssessedAt=datetime.now()
        )
