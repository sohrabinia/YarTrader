import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional

from src.Data.MarketData.Models.models import MarketDataPoint
from src.Application.Strategy.spike_strategy import SpikeStrategyEngine, SpikeConfig
from src.Application.Strategy.range_strategy import RangeStrategyEngine, RangeConfig
from src.Application.Strategy.trend_strategy import TrendStrategyEngine, TrendConfig
from src.Infrastructure.exceptions import ValidationException


class BacktestStrategyType(str, Enum):
    SPIKE = "SPIKE"
    RANGE = "RANGE"
    TREND = "TREND"


@dataclass(frozen=True)
class BacktestConfig:
    """
    Configuration parameters for historical Backtest evaluation.
    """
    symbol: str = "XAUUSD"
    interval: str = "M15"
    strategy_type: BacktestStrategyType = BacktestStrategyType.TREND
    min_history_bars: int = 21

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("Symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("Interval must be a non-empty string.")
        if self.min_history_bars < 2 or self.min_history_bars > 1000:
            raise ValidationException("min_history_bars must be between 2 and 1000.")


@dataclass(frozen=True)
class BacktestEvaluation:
    """
    Single timestamp evaluation result recorded during walk-forward backtesting.
    """
    timestamp: datetime
    signal_type: str
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "signal_type": self.signal_type,
            "metrics": self.metrics
        }


@dataclass(frozen=True)
class BacktestSummary:
    """
    Deterministic summary statistics compiled from walk-forward backtest evaluations.
    """
    total_evaluations: int
    signal_counts: Dict[str, int]
    valid_evaluations: int
    insufficient_data_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "signal_counts": self.signal_counts,
            "valid_evaluations": self.valid_evaluations,
            "insufficient_data_count": self.insufficient_data_count
        }


@dataclass(frozen=True)
class BacktestResult:
    """
    Immutable result object representing completed historical backtest execution.
    """
    symbol: str
    interval: str
    strategy_type: BacktestStrategyType
    evaluations: List[BacktestEvaluation]
    summary: BacktestSummary
    config: BacktestConfig
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type.value,
            "summary": self.summary.to_dict(),
            "config": {
                "symbol": self.config.symbol,
                "interval": self.config.interval,
                "strategy_type": self.config.strategy_type.value,
                "min_history_bars": self.config.min_history_bars
            },
            "evaluations": [e.to_dict() for e in self.evaluations],
            "executed_at": self.executed_at.isoformat() if hasattr(self.executed_at, "isoformat") else str(self.executed_at)
        }


class BacktestEngine:
    """
    Pure, deterministic historical Backtest Engine.
    Executes walk-forward evaluations over historical candles by delegating directly
    to existing strategy engines (Spike, Range, Trend) to prevent duplicated strategy math.
    Strictly guarantees zero look-ahead bias: evaluation at bar T receives candles strictly <= T.
    """
    def __init__(
        self,
        spike_engine: Optional[SpikeStrategyEngine] = None,
        range_engine: Optional[RangeStrategyEngine] = None,
        trend_engine: Optional[TrendStrategyEngine] = None
    ) -> None:
        self.spike_engine = spike_engine or SpikeStrategyEngine()
        self.range_engine = range_engine or RangeStrategyEngine()
        self.trend_engine = trend_engine or TrendStrategyEngine()

    def run_backtest(
        self,
        symbol: str,
        interval: str,
        candles: List[MarketDataPoint],
        config: Optional[BacktestConfig] = None
    ) -> BacktestResult:
        if not config:
            config = BacktestConfig(symbol=symbol, interval=interval)
        config.validate()

        if not candles:
            empty_summary = BacktestSummary(
                total_evaluations=0,
                signal_counts={},
                valid_evaluations=0,
                insufficient_data_count=0
            )
            return BacktestResult(
                symbol=symbol,
                interval=interval,
                strategy_type=config.strategy_type,
                evaluations=[],
                summary=empty_summary,
                config=config
            )

        # Chronological sort to guarantee strict temporal ordering
        sorted_candles = sorted(candles, key=lambda c: c.Timestamp)

        # Deduplicate identical timestamps safely
        unique_candles = []
        seen_ts = set()
        for c in sorted_candles:
            if c.Timestamp not in seen_ts:
                seen_ts.add(c.Timestamp)
                unique_candles.append(c)

        evaluations: List[BacktestEvaluation] = []
        signal_counts: Dict[str, int] = {}
        insufficient_data_count = 0
        valid_evaluations = 0

        min_bars = config.min_history_bars

        # Walk-forward simulation loop: at each bar i (where i >= min_bars),
        # slice historical window up to and including index i (t <= T)
        for i in range(min_bars, len(unique_candles) + 1):
            history_window = unique_candles[:i]
            target_candle = history_window[-1]

            # Delegate directly to existing strategy engines based on strategy_type
            if config.strategy_type == BacktestStrategyType.SPIKE:
                res = self.spike_engine.evaluate(symbol, interval, history_window)
                sig_val = res.signal_type.value
                metrics_dict = {
                    "volatility_baseline": res.volatility_baseline,
                    "spike_ratio": res.spike_ratio,
                    "candle_range": res.candle_range,
                    "candle_body": res.candle_body
                }
            elif config.strategy_type == BacktestStrategyType.RANGE:
                res = self.range_engine.evaluate(symbol, interval, history_window)
                sig_val = res.signal_type.value
                metrics_dict = {
                    "rolling_high": res.rolling_high,
                    "rolling_low": res.rolling_low,
                    "range_width": res.range_width,
                    "normalized_range_ratio": res.normalized_range_ratio
                }
            elif config.strategy_type == BacktestStrategyType.TREND:
                res = self.trend_engine.evaluate(symbol, interval, history_window)
                sig_val = res.signal_type.value
                metrics_dict = {
                    "fast_sma": res.fast_sma,
                    "slow_sma": res.slow_sma,
                    "trend_spread": res.trend_spread,
                    "volatility_baseline": res.volatility_baseline,
                    "normalized_trend_strength": res.normalized_trend_strength
                }
            else:
                raise ValidationException(f"Unsupported backtest strategy type: {config.strategy_type}")

            signal_counts[sig_val] = signal_counts.get(sig_val, 0) + 1

            if sig_val == "INSUFFICIENT_DATA":
                insufficient_data_count += 1
            else:
                valid_evaluations += 1

            evaluations.append(
                BacktestEvaluation(
                    timestamp=target_candle.Timestamp,
                    signal_type=sig_val,
                    metrics=metrics_dict
                )
            )

        summary = BacktestSummary(
            total_evaluations=len(evaluations),
            signal_counts=signal_counts,
            valid_evaluations=valid_evaluations,
            insufficient_data_count=insufficient_data_count
        )

        return BacktestResult(
            symbol=symbol,
            interval=interval,
            strategy_type=config.strategy_type,
            evaluations=evaluations,
            summary=summary,
            config=config
        )
