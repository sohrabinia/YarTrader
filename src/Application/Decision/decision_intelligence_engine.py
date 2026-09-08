from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.Application.Decision.decision_context_engine import DecisionContextSummary
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class DecisionIntelligenceMetric:
    """
    Immutable domain representation of an explainable decision intelligence metric.
    Pure historical sample sufficiency / data quality indicator.
    Zero AI, zero LLM, zero predictions, zero buy/sell signals.
    """
    metric_name: str
    metric_value: Any
    category: str
    explanation: str

    def validate(self) -> None:
        if not self.metric_name or not isinstance(self.metric_name, str):
            raise ValidationException("DecisionIntelligenceMetric metric_name must be a non-empty string.")
        if not self.category or not isinstance(self.category, str):
            raise ValidationException("DecisionIntelligenceMetric category must be a non-empty string.")
        if not self.explanation or not isinstance(self.explanation, str):
            raise ValidationException("DecisionIntelligenceMetric explanation must be a non-empty string.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "category": self.category,
            "explanation": self.explanation
        }


@dataclass(frozen=True)
class DecisionIntelligenceSummary:
    """
    Immutable root summary object produced deterministically by DecisionIntelligenceEngine.
    Exposes intelligence_id, readiness_state, context_sufficiency_score, evidence_factor_quality,
    metrics, and compiled_at.
    """
    intelligence_id: str
    symbol: str
    interval: str
    strategy_type: str
    decision_readiness_state: str
    context_sufficiency_score: float
    evidence_factor_quality: str
    metrics: List[DecisionIntelligenceMetric]
    decision_context_summary: DecisionContextSummary
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intelligence_id": self.intelligence_id,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "decision_readiness_state": self.decision_readiness_state,
            "context_sufficiency_score": self.context_sufficiency_score,
            "evidence_factor_quality": self.evidence_factor_quality,
            "metrics": [m.to_dict() for m in self.metrics],
            "decision_context_summary": self.decision_context_summary.to_dict(),
            "compiled_at": self.compiled_at.isoformat()
        }


class DecisionIntelligenceEngine:
    """
    Pure, deterministic Decision Intelligence Foundation Engine.
    Aggregates Phase 14 DecisionContextSummary objects into explainable decision intelligence metrics.
    Does NOT make buy/sell decisions, calculate indicators, query MT5, train ML models,
    or execute orders.
    """

    def compile_intelligence_summary(
        self,
        context_summary: DecisionContextSummary
    ) -> DecisionIntelligenceSummary:
        if not context_summary:
            raise ValidationException("context_summary cannot be None.")

        sym = context_summary.symbol
        tf = context_summary.interval
        strat = context_summary.strategy_type

        d_ctx = context_summary.decision_context
        tot_obs = d_ctx.historical_context_count
        now_utc = datetime.now(timezone.utc)

        # Context sufficiency score capped at 1.0 relative to 30-bar baseline
        suff_score = min(1.0, round(tot_obs / 30.0, 2))

        readiness = "INTELLIGENCE_READY" if context_summary.reliability_state == "STABLE_CONTEXT" else "INSUFFICIENT_CONTEXT"
        quality = context_summary.data_quality_state

        metrics: List[DecisionIntelligenceMetric] = [
            DecisionIntelligenceMetric(
                metric_name="ContextSufficiencyScore",
                metric_value=suff_score,
                category="SAMPLE_DEPTH",
                explanation=f"Sample depth score of {suff_score} relative to 30-bar baseline for {sym} ({tf})."
            ),
            DecisionIntelligenceMetric(
                metric_name="EvidenceFactorQuality",
                metric_value=quality,
                category="DATA_QUALITY",
                explanation=f"Evidence factor quality classified as {quality}."
            ),
            DecisionIntelligenceMetric(
                metric_name="DecisionReadinessState",
                metric_value=readiness,
                category="SYSTEM_READINESS",
                explanation=f"System decision context readiness state is {readiness}."
            )
        ]
        for m in metrics:
            m.validate()

        intel_id = f"intel-{sym.upper()}-{strat.upper()}-{now_utc.strftime('%Y%m%d%H%M%S')}"

        return DecisionIntelligenceSummary(
            intelligence_id=intel_id,
            symbol=sym,
            interval=tf,
            strategy_type=strat,
            decision_readiness_state=readiness,
            context_sufficiency_score=suff_score,
            evidence_factor_quality=quality,
            metrics=metrics,
            decision_context_summary=context_summary,
            compiled_at=now_utc
        )
