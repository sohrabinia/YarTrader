import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

class RangeSignalType(str, Enum):
    NO_SIGNAL = "NO_SIGNAL"
    RANGE = "RANGE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

@dataclass(frozen=True)
class RangeConfig:
    """
    Configuration parameters for deterministic Range Strategy evaluation.

    Formulas:
    - Window W_T = candles strictly <= T (last lookback_period candles)
    - Rolling High = max(High_t for t in W_T)
    - Rolling Low = min(Low_t for t in W_T)
    - Range Width = Rolling High - Rolling Low
    - True Range (TR_t) = max(High_t - Low_t, abs(High_t - Close_{t-1}), abs(Low_t - Close_{t-1}))
    - Mean True Range Baseline (MTR_T) = SMA(TR, lookback_period) for candles prior to T
    - Normalized Range Ratio = Range Width / max(MTR_T, min_volatility_baseline)
    - Range Condition: Normalized Range Ratio <= max_normalized_range AND Range Width >= min_range_width
    """
    lookback_period: int = 20
    max_normalized_range: float = 4.5
    min_range_width: float = 0.5
    min_volatility_baseline: float = 0.1

    def validate(self) -> None:
        if self.lookback_period < 3 or self.lookback_period > 500:
            raise ValidationException("lookback_period must be between 3 and 500")
        if self.max_normalized_range <= 0.0 or self.max_normalized_range > 50.0:
            raise ValidationException("max_normalized_range must be positive and <= 50.0")
        if self.min_range_width < 0.0:
            raise ValidationException("min_range_width must be non-negative")
        if self.min_volatility_baseline < 0.0:
            raise ValidationException("min_volatility_baseline must be non-negative")

@dataclass(frozen=True)
class RangeStrategyResult:
    """
    Immutable, deterministic result object for Range Strategy evaluation at timestamp T.
    """
    symbol: str
    interval: str
    evaluation_time: datetime
    signal_type: RangeSignalType
    rolling_high: float
    rolling_low: float
    range_width: float
    volatility_baseline: float
    normalized_range_ratio: float
    close_position_in_range: float  # 0.0 (at low) to 1.0 (at high)
    config: RangeConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "evaluation_time": self.evaluation_time.isoformat() if hasattr(self.evaluation_time, "isoformat") else str(self.evaluation_time),
            "signal_type": self.signal_type.value,
            "metrics": {
                "rolling_high": round(self.rolling_high, 4),
                "rolling_low": round(self.rolling_low, 4),
                "range_width": round(self.range_width, 4),
                "volatility_baseline": round(self.volatility_baseline, 4),
                "normalized_range_ratio": round(self.normalized_range_ratio, 2),
                "close_position_pct": round(self.close_position_in_range * 100.0, 1)
            },
            "config": {
                "lookback_period": self.config.lookback_period,
                "max_normalized_range": self.config.max_normalized_range,
                "min_range_width": self.config.min_range_width
            }
        }

class RangeStrategyEngine:
    """
    Pure, deterministic Range Strategy decision engine.
    Guarantees strict zero look-ahead bias: evaluation at index T uses ONLY candles <= T.
    """
    def evaluate(
        self,
        symbol: str,
        interval: str,
        candles: List[MarketDataPoint],
        config: Optional[RangeConfig] = None
    ) -> RangeStrategyResult:
        if not config:
            config = RangeConfig()
        config.validate()

        if not candles:
            return RangeStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=datetime.now(timezone.utc),
                signal_type=RangeSignalType.INSUFFICIENT_DATA,
                rolling_high=0.0, rolling_low=0.0, range_width=0.0,
                volatility_baseline=0.0, normalized_range_ratio=0.0,
                close_position_in_range=0.5, config=config
            )

        # Sort candles strictly chronologically by timestamp
        sorted_candles = sorted(candles, key=lambda c: c.Timestamp)

        # Cold start check: require at least lookback_period + 1 candles
        if len(sorted_candles) < config.lookback_period + 1:
            latest_c = sorted_candles[-1]
            return RangeStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=latest_c.Timestamp,
                signal_type=RangeSignalType.INSUFFICIENT_DATA,
                rolling_high=latest_c.High, rolling_low=latest_c.Low,
                range_width=latest_c.High - latest_c.Low,
                volatility_baseline=0.0, normalized_range_ratio=0.0,
                close_position_in_range=0.5, config=config
            )

        # Target candle at index T (latest candle in window)
        target = sorted_candles[-1]

        # Rolling window W_T of last lookback_period candles (including target T)
        window = sorted_candles[-config.lookback_period:]
        rolling_high = max(c.High for c in window)
        rolling_low = min(c.Low for c in window)
        range_width = max(0.0, rolling_high - rolling_low)

        # Compute True Range (TR) for historical candles in window
        # Baseline uses candles strictly prior to target T to guarantee zero look-ahead bias
        tr_list = []
        for i in range(1, len(sorted_candles) - 1):
            curr = sorted_candles[i]
            prev = sorted_candles[i - 1]
            tr = max(
                curr.High - curr.Low,
                abs(curr.High - prev.Close),
                abs(curr.Low - prev.Close)
            )
            tr_list.append(tr)

        if not tr_list:
            effective_mtr = config.min_volatility_baseline
        else:
            baseline_window = tr_list[-config.lookback_period:]
            mtr = sum(baseline_window) / float(len(baseline_window))
            effective_mtr = max(mtr, config.min_volatility_baseline)

        normalized_range_ratio = range_width / effective_mtr if effective_mtr > 0 else 0.0

        # Calculate close position in range (0.0 to 1.0)
        if range_width > 0:
            close_pos = (target.Close - rolling_low) / range_width
            close_pos = max(0.0, min(1.0, close_pos))
        else:
            close_pos = 0.5

        # Range Condition Evaluation
        signal = RangeSignalType.NO_SIGNAL
        if range_width >= config.min_range_width and normalized_range_ratio <= config.max_normalized_range:
            signal = RangeSignalType.RANGE

        return RangeStrategyResult(
            symbol=symbol,
            interval=interval,
            evaluation_time=target.Timestamp,
            signal_type=signal,
            rolling_high=rolling_high,
            rolling_low=rolling_low,
            range_width=range_width,
            volatility_baseline=effective_mtr,
            normalized_range_ratio=normalized_range_ratio,
            close_position_in_range=close_pos,
            config=config
        )
