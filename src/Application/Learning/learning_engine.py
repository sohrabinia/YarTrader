from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional

from src.Application.Backtest.backtest_engine import (
    BacktestResult,
    BacktestEvaluation,
    BacktestStrategyType
)
from src.Infrastructure.exceptions import ValidationException


class LearningMetricType(str, Enum):
    SIGNAL_DISTRIBUTION = "SIGNAL_DISTRIBUTION"
    HISTORICAL_RELIABILITY = "HISTORICAL_RELIABILITY"
    SAMPLE_SUFFICIENCY = "SAMPLE_SUFFICIENCY"


@dataclass(frozen=True)
class LearningObservation:
    """
    Immutable domain representation of a single historical strategy evaluation
    extracted from backtest output for learning aggregation.
    """
    timestamp: datetime
    symbol: str
    interval: str
    strategy_type: str
    signal_type: str
    metrics: Dict[str, Any]

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("LearningObservation symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("LearningObservation interval must be a non-empty string.")
        if not self.strategy_type or not isinstance(self.strategy_type, str):
            raise ValidationException("LearningObservation strategy_type must be a non-empty string.")
        if not self.signal_type or not isinstance(self.signal_type, str):
            raise ValidationException("LearningObservation signal_type must be a non-empty string.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "signal_type": self.signal_type,
            "metrics": self.metrics
        }


@dataclass(frozen=True)
class LearningDataset:
    """
    Validated collection of historical LearningObservations maintained in strict
    chronological order without look-ahead bias.
    """
    symbol: str
    interval: str
    strategy_type: str
    observations: List[LearningObservation]

    def validate(self) -> None:
        if not self.symbol:
            raise ValidationException("LearningDataset symbol must be non-empty.")
        if not self.interval:
            raise ValidationException("LearningDataset interval must be non-empty.")
        if not self.strategy_type:
            raise ValidationException("LearningDataset strategy_type must be non-empty.")
        for obs in self.observations:
            obs.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "count": len(self.observations),
            "observations": [o.to_dict() for o in self.observations]
        }


@dataclass(frozen=True)
class LearningConfig:
    """
    Configuration parameters for deterministic statistical Learning aggregation.
    """
    symbol: str = "XAUUSD"
    interval: str = "M15"
    strategy_type: str = "TREND"
    min_sample_threshold: int = 10

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("LearningConfig symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("LearningConfig interval must be a non-empty string.")
        if self.min_sample_threshold < 1 or self.min_sample_threshold > 10000:
            raise ValidationException("min_sample_threshold must be between 1 and 10000.")


@dataclass(frozen=True)
class LearningInsight:
    """
    Immutable statistical knowledge object generated deterministically from
    learning observations. Strictly explainable without neural networks or opaque ML.
    """
    symbol: str
    interval: str
    strategy_type: str
    observation_count: int
    signal_counts: Dict[str, int]
    signal_frequencies: Dict[str, float]
    sample_sufficiency: bool
    reliability_summary: Dict[str, Any]
    config: LearningConfig
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "observation_count": self.observation_count,
            "signal_counts": self.signal_counts,
            "signal_frequencies": self.signal_frequencies,
            "sample_sufficiency": self.sample_sufficiency,
            "reliability_summary": self.reliability_summary,
            "config": {
                "symbol": self.config.symbol,
                "interval": self.config.interval,
                "strategy_type": self.config.strategy_type,
                "min_sample_threshold": self.config.min_sample_threshold
            },
            "analyzed_at": self.analyzed_at.isoformat() if hasattr(self.analyzed_at, "isoformat") else str(self.analyzed_at)
        }


class LearningEngine:
    """
    Pure, deterministic statistical Learning Engine.
    Transforms historical BacktestResult evaluations into structured LearningInsights.
    Does NOT modify strategies, train neural networks, optimize parameters, or execute trades.
    Strictly preserves $t <= T$ historical causality.
    """

    def extract_dataset(
        self,
        backtest_result: BacktestResult
    ) -> LearningDataset:
        """
        Converts a BacktestResult into a clean, validated LearningDataset.
        """
        if not backtest_result:
            raise ValidationException("BacktestResult cannot be None.")

        obs_list: List[LearningObservation] = []
        for ev in backtest_result.evaluations:
            obs = LearningObservation(
                timestamp=ev.timestamp,
                symbol=backtest_result.symbol,
                interval=backtest_result.interval,
                strategy_type=backtest_result.strategy_type.value,
                signal_type=ev.signal_type,
                metrics=dict(ev.metrics)
            )
            obs.validate()
            obs_list.append(obs)

        # Ensure strict chronological ordering
        obs_list.sort(key=lambda o: o.timestamp)

        # Deduplicate identical timestamps safely
        unique_obs = []
        seen_ts = set()
        for o in obs_list:
            if o.timestamp not in seen_ts:
                seen_ts.add(o.timestamp)
                unique_obs.append(o)

        dataset = LearningDataset(
            symbol=backtest_result.symbol,
            interval=backtest_result.interval,
            strategy_type=backtest_result.strategy_type.value,
            observations=unique_obs
        )
        dataset.validate()
        return dataset

    def generate_insight(
        self,
        dataset: LearningDataset,
        config: Optional[LearningConfig] = None
    ) -> LearningInsight:
        """
        Calculates deterministic statistical insights from a LearningDataset.
        """
        if not dataset:
            raise ValidationException("LearningDataset cannot be None.")

        if not config:
            config = LearningConfig(
                symbol=dataset.symbol,
                interval=dataset.interval,
                strategy_type=dataset.strategy_type
            )
        config.validate()

        total_obs = len(dataset.observations)
        signal_counts: Dict[str, int] = {}
        for obs in dataset.observations:
            sig = obs.signal_type
            signal_counts[sig] = signal_counts.get(sig, 0) + 1

        signal_freqs: Dict[str, float] = {}
        for sig, count in signal_counts.items():
            freq = (count / float(total_obs)) if total_obs > 0 else 0.0
            signal_freqs[sig] = round(freq, 4)

        sample_sufficiency = total_obs >= config.min_sample_threshold

        active_signal_count = sum(cnt for sig, cnt in signal_counts.items() if sig not in ["NO_SIGNAL", "INSUFFICIENT_DATA"])
        active_signal_ratio = (active_signal_count / float(total_obs)) if total_obs > 0 else 0.0

        reliability_summary = {
            "total_observations": total_obs,
            "active_signal_count": active_signal_count,
            "active_signal_ratio": round(active_signal_ratio, 4),
            "sample_sufficiency": sample_sufficiency,
            "min_sample_threshold": config.min_sample_threshold,
            "status": "VALID_SAMPLE" if sample_sufficiency else "INSUFFICIENT_DATA"
        }

        return LearningInsight(
            symbol=dataset.symbol,
            interval=dataset.interval,
            strategy_type=dataset.strategy_type,
            observation_count=total_obs,
            signal_counts=signal_counts,
            signal_frequencies=signal_freqs,
            sample_sufficiency=sample_sufficiency,
            reliability_summary=reliability_summary,
            config=config
        )
