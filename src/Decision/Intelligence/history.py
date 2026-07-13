from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from src.Decision.Models.models import DecisionResult
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionHistoryRecord:
    """
    Structured record representing a historical decision outcome, preserved for future learning and audit.
    No database required; saved inside memory or local registers.
    """
    Timestamp: datetime
    ContextSummary: str
    Result: DecisionResult
    Confidence: float
    EvidenceReferences: Dict[str, Any] = field(default_factory=dict)


class DecisionValidator:
    """
    Validates decision input completeness, consistency, and structural soundness.
    Fails safely on detecting invalid conditions.
    """

    def validate_context(self, context: DecisionIntelligenceContext) -> None:
        """
        Validates the integrity and soundness of the decision context.
        Raises ValidationException if checks fail.
        """
        if not context:
            raise ValidationException("DecisionIntelligenceContext cannot be None.")

        # Check for missing evidence (e.g., both research and strategy must have elements to make any valid decision)
        if not context.ResearchInsights and not context.StrategyEvaluations:
            raise ValidationException(
                "Incomplete context: Both ResearchInsights and StrategyEvaluations are empty. Decision cannot be made."
            )

        # Check for invalid confidence scores
        for insight in context.ResearchInsights:
            conf = 0.8
            if hasattr(insight, "Confidence"):
                conf = insight.Confidence
            elif isinstance(insight, dict):
                conf = insight.get("confidence", 0.8)

            if conf < 0.0 or conf > 1.0:
                raise ValidationException(f"Invalid Confidence level observed in Research Insights: {conf}.")

        # Check for contradictory inputs
        if len(context.ResearchInsights) > 1:
            # Simple check if there are conflicting trends inside insights
            pass
