from dataclasses import dataclass
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionQualityScore:
    """
    Structured breakdown of decision intelligence quality metrics.
    """
    EvidenceQuality: float  # 0.0 to 1.0
    ConsistencyScore: float  # 0.0 to 1.0
    ReliabilityScore: float  # 0.0 to 1.0
    OverallQualityScore: float  # 0.0 to 1.0


class DecisionQualityEvaluator:
    """
    Evaluates raw context and alignment dimensions to produce detailed quality and consistency scores.
    """

    def evaluate_quality(self, context: DecisionIntelligenceContext) -> DecisionQualityScore:
        """
        Calculates Evidence Quality, Consistency, Reliability, and Overall Quality scores.
        """
        if not context:
            raise ValidationException("DecisionIntelligenceContext cannot be None for quality evaluation.")

        # 1. Evidence Quality
        # Based on count of insights and presence of historical support
        insights_count = len(context.ResearchInsights)
        has_history = 1.0 if context.HistoricalEvidence else 0.5
        evidence_quality = min(1.0, max(0.1, (insights_count * 0.2 + has_history * 0.6)))

        # 2. Consistency Score
        # Based on research vs strategy alignment, strategy vs risk compatibility
        consistency = 0.8
        if context.StrategyEvaluations and context.RiskAssessments:
            first_strat = context.StrategyEvaluations[0]
            first_risk = context.RiskAssessments[0]

            strat_score = 0.8
            if hasattr(first_strat, "Score"):
                strat_score = first_strat.Score.OverallScore
            elif isinstance(first_strat, dict):
                strat_score = first_strat.get("overall_score", 0.8)

            risk_approved = True
            if hasattr(first_risk, "IsApproved"):
                risk_approved = first_risk.IsApproved
            elif isinstance(first_risk, dict):
                risk_approved = first_risk.get("is_approved", True)

            # High strategy score should ideally have approved risk
            if strat_score > 0.8 and not risk_approved:
                consistency = 0.4  # discrepancy
            elif strat_score > 0.8 and risk_approved:
                consistency = 0.95
            elif strat_score <= 0.6 and not risk_approved:
                consistency = 0.90  # both agree on caution
        else:
            consistency = 0.5  # Neutral default due to lack of sources

        # 3. Reliability Score
        # Stability of confidence and metadata completeness
        reliability = 0.85
        if context.Metadata.get("uncertainty", False):
            reliability = 0.5

        # 4. Overall Quality Score
        overall = round((evidence_quality * 0.4 + consistency * 0.4 + reliability * 0.2), 4)

        return DecisionQualityScore(
            EvidenceQuality=round(evidence_quality, 4),
            ConsistencyScore=round(consistency, 4),
            ReliabilityScore=round(reliability, 4),
            OverallQualityScore=overall
        )
