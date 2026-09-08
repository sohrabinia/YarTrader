from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.Application.Intelligence.intelligence_engine import IntelligenceSummary
from src.Application.Learning.learning_engine import LearningInsight
from src.Application.Memory.memory_engine import MemoryRecord
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class DecisionContext:
    """
    Immutable domain representation of compiled historical decision context.
    Combines timestamp, symbol, interval, context counts, and phase summaries.
    Zero AI, zero LLM, zero predictions, zero buy/sell recommendations.
    """
    timestamp: datetime
    symbol: str
    interval: str
    historical_context_count: int
    learning_summary: Dict[str, Any]
    memory_summary: Dict[str, Any]
    intelligence_summary: Dict[str, Any]

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("DecisionContext symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("DecisionContext interval must be a non-empty string.")
        if self.historical_context_count < 0:
            raise ValidationException("DecisionContext historical_context_count must be non-negative.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "interval": self.interval,
            "historical_context_count": self.historical_context_count,
            "learning_summary": self.learning_summary,
            "memory_summary": self.memory_summary,
            "intelligence_summary": self.intelligence_summary
        }


@dataclass(frozen=True)
class DecisionFactor:
    """
    Immutable domain representation of an explainable historical decision factor.
    Pure historical evidence parameter.
    """
    factor_name: str
    factor_value: Any
    source: str
    explanation: str

    def validate(self) -> None:
        if not self.factor_name or not isinstance(self.factor_name, str):
            raise ValidationException("DecisionFactor factor_name must be a non-empty string.")
        if not self.source or not isinstance(self.source, str):
            raise ValidationException("DecisionFactor source must be a non-empty string.")
        if not self.explanation or not isinstance(self.explanation, str):
            raise ValidationException("DecisionFactor explanation must be a non-empty string.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "factor_value": self.factor_value,
            "source": self.source,
            "explanation": self.explanation
        }


@dataclass(frozen=True)
class DecisionContextSummary:
    """
    Immutable root summary produced deterministically by DecisionContextEngine.
    Exposes context_id, factors, reliability_state, data_quality_state, and decision_context.
    """
    context_id: str
    symbol: str
    interval: str
    strategy_type: str
    decision_context: DecisionContext
    factors: List[DecisionFactor]
    reliability_state: str
    data_quality_state: str
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "decision_context": self.decision_context.to_dict(),
            "factors": [f.to_dict() for s in [self.factors] for f in s],
            "reliability_state": self.reliability_state,
            "data_quality_state": self.data_quality_state,
            "compiled_at": self.compiled_at.isoformat()
        }


class DecisionContextEngine:
    """
    Pure, deterministic Decision Context Foundation Engine.
    Combines IntelligenceSummary, LearningInsight, and MemoryRecord objects
    to produce explainable, structured context for future human or AI consumers.
    Does NOT make decisions, generate buy/sell signals, predict outcomes, or execute orders.
    """

    def compile_context_summary(
        self,
        intelligence_summary: IntelligenceSummary,
        learning_insight: LearningInsight,
        memory_records: List[MemoryRecord]
    ) -> DecisionContextSummary:
        if not intelligence_summary:
            raise ValidationException("intelligence_summary cannot be None.")
        if not learning_insight:
            raise ValidationException("learning_insight cannot be None.")

        sym = intelligence_summary.symbol
        tf = intelligence_summary.interval
        strat = intelligence_summary.strategy_type

        tot_obs = intelligence_summary.historical_context_count
        now_utc = datetime.now(timezone.utc)

        context_obj = DecisionContext(
            timestamp=now_utc,
            symbol=sym,
            interval=tf,
            historical_context_count=tot_obs,
            learning_summary={
                "observation_count": learning_insight.observation_count,
                "signal_counts": learning_insight.signal_counts,
                "sample_sufficiency": learning_insight.sample_sufficiency
            },
            memory_summary={
                "records_count": len(memory_records)
            },
            intelligence_summary={
                "active_signals_count": intelligence_summary.context.active_signals_count,
                "sample_sufficiency_status": intelligence_summary.sample_sufficiency_status,
                "statistical_confidence_score": intelligence_summary.statistical_confidence_score
            }
        )
        context_obj.validate()

        factors: List[DecisionFactor] = [
            DecisionFactor(
                factor_name="HistoricalObservationCount",
                factor_value=tot_obs,
                source="Phase 11 Learning",
                explanation=f"Evaluated {tot_obs} historical market bars for {sym} ({tf})."
            ),
            DecisionFactor(
                factor_name="MemoryRecordsCount",
                factor_value=len(memory_records),
                source="Phase 12 Memory Foundation",
                explanation=f"Retrieved {len(memory_records)} structured historical knowledge records."
            ),
            DecisionFactor(
                factor_name="StatisticalSampleSufficiency",
                factor_value=intelligence_summary.sample_sufficiency_status,
                source="Phase 13 Intelligence Foundation",
                explanation=f"Sample size classification is {intelligence_summary.sample_sufficiency_status}."
            ),
            DecisionFactor(
                factor_name="StatisticalConfidenceScore",
                factor_value=intelligence_summary.statistical_confidence_score,
                source="Phase 13 Intelligence Foundation",
                explanation=f"Sample size score relative to 30-bar baseline is {intelligence_summary.statistical_confidence_score}."
            )
        ]
        for f in factors:
            f.validate()

        data_quality = "HIGH_QUALITY" if tot_obs >= 20 else ("MODERATE_QUALITY" if tot_obs >= 5 else "LOW_QUALITY")
        reliability = "STABLE_CONTEXT" if intelligence_summary.sample_sufficiency_status == "VALID_SAMPLE" else "INSUFFICIENT_CONTEXT"

        cid = f"ctx-{sym.upper()}-{strat.upper()}-{now_utc.strftime('%Y%m%d%H%M%S')}"

        return DecisionContextSummary(
            context_id=cid,
            symbol=sym,
            interval=tf,
            strategy_type=strat,
            decision_context=context_obj,
            factors=factors,
            reliability_state=reliability,
            data_quality_state=data_quality,
            compiled_at=now_utc
        )
