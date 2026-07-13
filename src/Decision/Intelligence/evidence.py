from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionEvidenceTrail:
    """
    Comprehensive, structured trail detailing the captured inputs justifying a decision.
    Allows complete tracing back to research, features, patterns, strategy, and risk factors.
    """
    ResearchEvidence: List[Any]
    FeatureEvidence: Dict[str, Any]
    PatternEvidence: List[Any]
    StrategyEvidence: List[Any]
    RiskEvidence: List[Any]
    TraceabilityId: str = ""


class DecisionEvidenceCollector:
    """
    Collects, packages, and seals analytical evidence from all pipeline layers to justify decision reasoning.
    """

    def collect_evidence(self, context: DecisionIntelligenceContext) -> DecisionEvidenceTrail:
        """
        Synthesizes and organizes evidence into an explainable audit trail.
        """
        if not context:
            raise ValidationException("DecisionIntelligenceContext cannot be None for evidence collection.")

        # Gather evidence elements
        research_ev = list(context.ResearchInsights)
        feature_ev = dict(context.MarketConditions)
        pattern_ev = list(context.PatternObservations)
        strategy_ev = list(context.StrategyEvaluations)
        risk_ev = list(context.RiskAssessments)

        # Build trace ID
        trace_id = f"ev-{context.Metadata.get('asset', 'generic')}-{len(research_ev)}-{len(strategy_ev)}"

        return DecisionEvidenceTrail(
            ResearchEvidence=research_ev,
            FeatureEvidence=feature_ev,
            PatternEvidence=pattern_ev,
            StrategyEvidence=strategy_ev,
            RiskEvidence=risk_ev,
            TraceabilityId=trace_id
        )
