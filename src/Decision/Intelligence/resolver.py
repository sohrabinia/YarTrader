from dataclasses import dataclass, field
from typing import List
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class ConflictResolutionResult:
    """
    Represents the logical outcome of a conflict resolution evaluation.
    This is analytical only; it does not authorize or trigger trade executions.
    """
    ConflictType: str  # e.g., "ResearchStrategyMismatch", "StrategyRiskConflict", "None"
    ConflictingSources: List[str]
    ResolutionExplanation: str
    ConfidenceImpact: float  # e.g., -0.2 (degradation factor)


class DecisionConflictResolver:
    """
    Resolves discrepancies or contradictions across research, strategy, and risk inputs logically.
    """

    def resolve_conflicts(self, context: DecisionIntelligenceContext) -> ConflictResolutionResult:
        """
        Analyzes the inputs to identify and resolve intelligence conflicts.
        """
        if not context:
            raise ValidationException("DecisionIntelligenceContext cannot be None for conflict resolution.")

        conflict_type = "None"
        conflicting_sources = []
        explanation = "All intelligence layers are aligned or insufficient data is present to detect conflicts."
        confidence_impact = 0.0

        if context.ResearchInsights and context.StrategyEvaluations:
            # 1. Research vs Strategy Conflict
            first_insight = context.ResearchInsights[0]
            first_strat = context.StrategyEvaluations[0]

            research_conf = 0.8
            if hasattr(first_insight, "Confidence"):
                research_conf = first_insight.Confidence
            elif isinstance(first_insight, dict):
                research_conf = first_insight.get("confidence", 0.8)

            strat_score = 0.8
            if hasattr(first_strat, "Score"):
                strat_score = first_strat.Score.OverallScore
            elif isinstance(first_strat, dict):
                strat_score = first_strat.get("overall_score", 0.8)

            # Conflict: High research confidence but low strategy suitability (or vice versa)
            if research_conf > 0.8 and strat_score < 0.5:
                conflict_type = "ResearchStrategyMismatch"
                conflicting_sources = ["ResearchEngine", "StrategyEvaluator"]
                explanation = "Conflict: High research market confidence does not align with low strategy compatibility score."
                confidence_impact = -0.15

        if context.StrategyEvaluations and context.RiskAssessments:
            # 2. Strategy vs Risk Conflict
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

            # Conflict: High strategy suitability but risk has flagged/rejected the allocation
            if strat_score > 0.8 and not risk_approved:
                conflict_type = "StrategyRiskConflict"
                conflicting_sources = ["StrategyEvaluator", "RiskEngine"]
                explanation = "Conflict: High strategy score is overridden by a failed Risk engine audit. Caution advised."
                confidence_impact = -0.25

        return ConflictResolutionResult(
            ConflictType=conflict_type,
            ConflictingSources=conflicting_sources,
            ResolutionExplanation=explanation,
            ConfidenceImpact=confidence_impact
        )
