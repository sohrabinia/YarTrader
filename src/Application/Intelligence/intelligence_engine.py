from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.Application.Learning.learning_engine import LearningInsight
from src.Application.Memory.memory_engine import MemoryRecord
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class IntelligenceContext:
    """
    Immutable domain representation of aggregated historical context for a symbol and strategy.
    Strictly statistical facts and sample counts.
    Zero AI, zero LLM, zero predictions, zero trading suggestions.
    """
    symbol: str
    interval: str
    strategy_type: str
    total_observations: int
    active_signals_count: int
    signal_distribution: Dict[str, int]
    signal_frequencies: Dict[str, float]

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("IntelligenceContext symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("IntelligenceContext interval must be a non-empty string.")
        if not self.strategy_type or not isinstance(self.strategy_type, str):
            raise ValidationException("IntelligenceContext strategy_type must be a non-empty string.")
        if self.total_observations < 0:
            raise ValidationException("IntelligenceContext total_observations must be non-negative.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "total_observations": self.total_observations,
            "active_signals_count": self.active_signals_count,
            "signal_distribution": self.signal_distribution,
            "signal_frequencies": self.signal_frequencies
        }


@dataclass(frozen=True)
class IntelligenceSignal:
    """
    Immutable domain representation of a historical signal summary metric.
    Confidence represents historical sample sufficiency score, NOT future prediction.
    """
    signal_name: str
    historical_count: int
    frequency_ratio: float
    sample_confidence_state: str

    def validate(self) -> None:
        if not self.signal_name or not isinstance(self.signal_name, str):
            raise ValidationException("IntelligenceSignal signal_name must be a non-empty string.")
        if self.historical_count < 0:
            raise ValidationException("IntelligenceSignal historical_count must be non-negative.")
        if self.frequency_ratio < 0.0 or self.frequency_ratio > 1.0:
            raise ValidationException("IntelligenceSignal frequency_ratio must be between 0.0 and 1.0.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "historical_count": self.historical_count,
            "frequency_ratio": self.frequency_ratio,
            "sample_confidence_state": self.sample_confidence_state
        }


@dataclass(frozen=True)
class IntelligenceSummary:
    """
    Immutable root summary object produced deterministically by IntelligenceEngine.
    Pure statistical facts derived from historical Learning and Memory Foundation outputs.
    """
    symbol: str
    interval: str
    strategy_type: str
    historical_context_count: int
    memory_records_count: int
    context: IntelligenceContext
    signal_summaries: List[IntelligenceSignal]
    sample_sufficiency_status: str
    statistical_confidence_score: float
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "historical_context_count": self.historical_context_count,
            "memory_records_count": self.memory_records_count,
            "context": self.context.to_dict(),
            "signal_summaries": [s.to_dict() for s in self.signal_summaries],
            "sample_sufficiency_status": self.sample_sufficiency_status,
            "statistical_confidence_score": self.statistical_confidence_score,
            "compiled_at": self.compiled_at.isoformat()
        }


class IntelligenceEngine:
    """
    Pure, deterministic Intelligence Foundation Engine.
    Consumes LearningInsight and MemoryRecord collections to aggregate historical context.
    Does NOT calculate indicators, query MT5, train ML models, generate LLM prompts, or execute orders.
    Statistical confidence score represents sample size sufficiency relative to a 30-bar baseline.
    """

    def compile_summary(
        self,
        learning_insight: LearningInsight,
        memory_records: List[MemoryRecord]
    ) -> IntelligenceSummary:
        if not learning_insight:
            raise ValidationException("learning_insight cannot be None.")

        sym = learning_insight.symbol
        tf = learning_insight.interval
        strat = learning_insight.strategy_type

        tot_obs = learning_insight.observation_count
        sig_counts = dict(learning_insight.signal_counts or {})
        sig_freqs = dict(learning_insight.signal_frequencies or {})

        act_cnt = sum(c for s, c in sig_counts.items() if s not in ["NO_SIGNAL", "INSUFFICIENT_DATA"])

        context = IntelligenceContext(
            symbol=sym,
            interval=tf,
            strategy_type=strat,
            total_observations=tot_obs,
            active_signals_count=act_cnt,
            signal_distribution=sig_counts,
            signal_frequencies=sig_freqs
        )
        context.validate()

        signals_list: List[IntelligenceSignal] = []
        for s_name, count in sig_counts.items():
            freq = sig_freqs.get(s_name, 0.0)
            conf_state = "HIGH_SAMPLE" if count >= 20 else ("MODERATE_SAMPLE" if count >= 5 else "LOW_SAMPLE")
            sig_obj = IntelligenceSignal(
                signal_name=s_name,
                historical_count=count,
                frequency_ratio=freq,
                sample_confidence_state=conf_state
            )
            sig_obj.validate()
            signals_list.append(sig_obj)

        sample_status = "VALID_SAMPLE" if tot_obs >= 20 else "INSUFFICIENT_DATA"
        # Statistical confidence represents sample size ratio relative to 30 bars (capped at 1.0)
        stat_confidence = min(1.0, round(tot_obs / 30.0, 2))

        summary = IntelligenceSummary(
            symbol=sym,
            interval=tf,
            strategy_type=strat,
            historical_context_count=tot_obs,
            memory_records_count=len(memory_records),
            context=context,
            signal_summaries=signals_list,
            sample_sufficiency_status=sample_status,
            statistical_confidence_score=stat_confidence
        )
        return summary
