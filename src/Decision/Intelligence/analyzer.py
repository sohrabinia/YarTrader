from dataclasses import dataclass, field
from typing import Any, Dict
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionAnalysis:
    """
    Structured logical breakdown of decision indicators, evidence quality, and confidence.
    """
    Summary: str
    SupportingEvidence: Dict[str, Any]
    Confidence: float
    ReasoningMetadata: Dict[str, Any] = field(default_factory=dict)


class DecisionAnalyzer:
    """
    Analyzes completeness, alignment, and compatibility of intelligence data points
    to produce a detailed reasoning analysis.
    """

    def analyze_context(self, context: DecisionIntelligenceContext) -> DecisionAnalysis:
        """
        Conducts alignment and risk compatibility analyses over the DecisionIntelligenceContext.
        """
        if not context:
            raise ValidationException("DecisionIntelligenceContext cannot be None for analysis.")

        # Gather counts and scores
        insights_count = len(context.ResearchInsights)
        strategy_count = len(context.StrategyEvaluations)
        risk_count = len(context.RiskAssessments)

        # Baseline defaults
        alignment_status = "Incomplete context"
        completeness = 0.0
        confidence = 0.5

        # Check completeness
        total_sources = (1 if insights_count else 0) + (1 if strategy_count else 0) + (1 if risk_count else 0)
        completeness = total_sources / 3.0

        evidence = {
            "insights_count": insights_count,
            "strategy_count": strategy_count,
            "risk_count": risk_count,
            "completeness_score": completeness
        }

        # Determine alignment and confidence if complete
        if completeness == 1.0:
            # We have Research, Strategy, and Risk!
            research_conf = 0.8
            strat_score = 0.8
            risk_approved = True

            # Extract from first elements if possible
            first_insight = context.ResearchInsights[0]
            if hasattr(first_insight, "Confidence"):
                research_conf = first_insight.Confidence
            elif hasattr(first_insight, "confidence"):
                research_conf = first_insight.confidence
            elif isinstance(first_insight, dict):
                research_conf = first_insight.get("confidence", 0.8)

            first_strat = context.StrategyEvaluations[0]
            if hasattr(first_strat, "Score"):
                strat_score = first_strat.Score.OverallScore
            elif isinstance(first_strat, dict):
                strat_score = first_strat.get("overall_score", 0.8)

            first_risk = context.RiskAssessments[0]
            if hasattr(first_risk, "IsApproved"):
                risk_approved = first_risk.IsApproved
            elif isinstance(first_risk, dict):
                risk_approved = first_risk.get("is_approved", True)

            # Alignment check: Positive market conditions and high strategy compatibility
            if strat_score >= 0.75 and research_conf >= 0.75:
                alignment_status = "Research and Strategy are strongly aligned."
            else:
                alignment_status = "Minor misalignment or low confidence observed."

            if not risk_approved:
                alignment_status += " Warning: Risk check is rejected."

            confidence = round((research_conf + strat_score + (1.0 if risk_approved else 0.4)) / 3.0, 4)
        else:
            alignment_status = "Insufficient intelligence sources present to analyze alignment."

        summary = (
            f"Decision Analysis completed with completeness {round(completeness, 2)}. "
            f"Status: {alignment_status}"
        )

        metadata = {
            "alignment_status": alignment_status,
            "has_warnings": "Warning" in alignment_status
        }

        return DecisionAnalysis(
            Summary=summary,
            SupportingEvidence=evidence,
            Confidence=confidence,
            ReasoningMetadata=metadata
        )
