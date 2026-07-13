from typing import Any, Dict, List, Optional
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Infrastructure.exceptions import ValidationException

class DecisionContextBuilder:
    """
    Builder responsible for synthesizing raw research outputs, strategy evaluations,
    risk assessments, and market contexts into normalized DecisionIntelligenceContext instances.
    """

    def __init__(self) -> None:
        self._research_insights: List[Any] = []
        self._pattern_observations: List[Any] = []
        self._strategy_evaluations: List[Any] = []
        self._risk_assessments: List[Any] = []
        self._market_conditions: Dict[str, Any] = {}
        self._historical_evidence: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}

    def with_research(
        self,
        insights: List[Any],
        observations: Optional[List[Any]] = None
    ) -> 'DecisionContextBuilder':
        """Adds research insights and optional pattern observations."""
        self._research_insights.extend(insights or [])
        self._pattern_observations.extend(observations or [])
        return self

    def with_strategy(self, evaluations: List[Any]) -> 'DecisionContextBuilder':
        """Adds strategy evaluations."""
        self._strategy_evaluations.extend(evaluations or [])
        return self

    def with_risk(self, assessments: List[Any]) -> 'DecisionContextBuilder':
        """Adds risk assessments."""
        self._risk_assessments.extend(assessments or [])
        return self

    def with_market_context(self, conditions: Dict[str, Any]) -> 'DecisionContextBuilder':
        """Adds raw market conditions."""
        self._market_conditions.update(conditions or {})
        return self

    def with_historical_evidence(self, evidence: Dict[str, Any]) -> 'DecisionContextBuilder':
        """Adds historical evidence details."""
        self._historical_evidence.update(evidence or {})
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'DecisionContextBuilder':
        """Adds context metadata."""
        self._metadata.update(metadata or {})
        return self

    def build(self) -> DecisionIntelligenceContext:
        """
        Builds the DecisionIntelligenceContext, normalizing and resolving missing fields safely.
        """
        # Handle defaults / resolve missing information
        if not self._market_conditions:
            self._market_conditions = {"source": "default_fallback", "volatility": 0.15, "trend_direction": "flat"}

        if not self._metadata:
            self._metadata = {"generated_by": "DecisionContextBuilder"}

        return DecisionIntelligenceContext(
            ResearchInsights=list(self._research_insights),
            PatternObservations=list(self._pattern_observations),
            StrategyEvaluations=list(self._strategy_evaluations),
            RiskAssessments=list(self._risk_assessments),
            MarketConditions=dict(self._market_conditions),
            HistoricalEvidence=dict(self._historical_evidence),
            Metadata=dict(self._metadata)
        )
