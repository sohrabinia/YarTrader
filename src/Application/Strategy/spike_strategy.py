import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

class SpikeSignalType(str, Enum):
    NO_SIGNAL = "NO_SIGNAL"
    SPIKE_UP = "SPIKE_UP"
    SPIKE_DOWN = "SPIKE_DOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

@dataclass(frozen=True)
class SpikeConfig:
    """
    Configuration parameters for deterministic Spike Strategy evaluation.

    Formulas:
    - True Range (TR_t) = max(High_t - Low_t, abs(High_t - Close_{t-1}), abs(Low_t - Close_{t-1}))
    - Mean True Range (MTR_t) = SMA(TR, lookback_period) using candles prior to T (t-lookback..t-1).
    - Candle Body (Body_t) = Close_t - Open_t
    - Spike Condition: abs(Body_t) >= spike_threshold * MTR_t AND (High_t - Low_t) >= min_movement
    """
    lookback_period: int = 14
    spike_threshold: float = 2.5
    min_movement: float = 1.0
    min_volatility_baseline: float = 0.1

    def validate(self) -> None:
        if self.lookback_period < 2 or self.lookback_period > 500:
            raise ValidationException("lookback_period must be between 2 and 500")
        if self.spike_threshold <= 0.0 or self.spike_threshold > 50.0:
            raise ValidationException("spike_threshold must be positive and <= 50.0")
        if self.min_movement < 0.0:
            raise ValidationException("min_movement must be non-negative")
        if self.min_volatility_baseline < 0.0:
            raise ValidationException("min_volatility_baseline must be non-negative")

@dataclass(frozen=True)
class SpikeStrategyResult:
    """
    Immutable, deterministic result object for Spike Strategy evaluation at timestamp T.
    """
    symbol: str
    interval: str
    evaluation_time: datetime
    signal_type: SpikeSignalType
    candle_open: float
    candle_high: float
    candle_low: float
    candle_close: float
    candle_range: float
    candle_body: float
    volatility_baseline: float
    spike_ratio: float
    config: SpikeConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "evaluation_time": self.evaluation_time.isoformat() if hasattr(self.evaluation_time, "isoformat") else str(self.evaluation_time),
            "signal_type": self.signal_type.value,
            "candle": {
                "open": self.candle_open,
                "high": self.candle_high,
                "low": self.candle_low,
                "close": self.candle_close,
                "range": round(self.candle_range, 4),
                "body": round(self.candle_body, 4)
            },
            "volatility_baseline": round(self.volatility_baseline, 4),
            "spike_ratio": round(self.spike_ratio, 2),
            "config": {
                "lookback_period": self.config.lookback_period,
                "spike_threshold": self.config.spike_threshold,
                "min_movement": self.config.min_movement
            }
        }

class SpikeStrategyEngine:
    """
    Pure, deterministic Spike Strategy decision engine.
    Guarantees strict zero look-ahead bias: evaluation at index T uses ONLY candles <= T.
    """
    def evaluate(
        self,
        symbol: str,
        interval: str,
        candles: List[MarketDataPoint],
        config: Optional[SpikeConfig] = None
    ) -> SpikeStrategyResult:
        if not config:
            config = SpikeConfig()
        config.validate()

        if not candles:
            return SpikeStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=datetime.now(timezone.utc),
                signal_type=SpikeSignalType.INSUFFICIENT_DATA,
                candle_open=0.0, candle_high=0.0, candle_low=0.0, candle_close=0.0,
                candle_range=0.0, candle_body=0.0, volatility_baseline=0.0, spike_ratio=0.0,
                config=config
            )

        # Ensure candles are strictly sorted chronologically by timestamp
        sorted_candles = sorted(candles, key=lambda c: c.Timestamp)

        # Cold start check: require lookback_period + 1 candles to compute baseline
        if len(sorted_candles) < config.lookback_period + 1:
            latest_c = sorted_candles[-1]
            return SpikeStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=latest_c.Timestamp,
                signal_type=SpikeSignalType.INSUFFICIENT_DATA,
                candle_open=latest_c.Open, candle_high=latest_c.High,
                candle_low=latest_c.Low, candle_close=latest_c.Close,
                candle_range=latest_c.High - latest_c.Low,
                candle_body=latest_c.Close - latest_c.Open,
                volatility_baseline=0.0, spike_ratio=0.0,
                config=config
            )

        # Target candle at index T (the latest candle in the window)
        target = sorted_candles[-1]

        # Compute True Range (TR) for historical candles in window
        # To strictly avoid look-ahead bias, compute baseline MTR using candles prior to target
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

        if len(tr_list) < config.lookback_period:
            # Fallback if window was tight
            mtr = max((sorted_candles[-2].High - sorted_candles[-2].Low), config.min_volatility_baseline)
        else:
            baseline_window = tr_list[-config.lookback_period:]
            mtr = sum(baseline_window) / float(len(baseline_window))

        # Enforce minimum volatility baseline to prevent divide-by-zero or micro-spike false positives
        effective_mtr = max(mtr, config.min_volatility_baseline)

        c_range = target.High - target.Low
        c_body = target.Close - target.Open
        abs_body = abs(c_body)

        spike_ratio = abs_body / effective_mtr if effective_mtr > 0 else 0.0

        # Signal Decision Logic
        signal = SpikeSignalType.NO_SIGNAL
        if c_range >= config.min_movement and spike_ratio >= config.spike_threshold:
            if c_body > 0:
                signal = SpikeSignalType.SPIKE_UP
            elif c_body < 0:
                signal = SpikeSignalType.SPIKE_DOWN

        return SpikeStrategyResult(
            symbol=symbol,
            interval=interval,
            evaluation_time=target.Timestamp,
            signal_type=signal,
            candle_open=target.Open,
            candle_high=target.High,
            candle_low=target.Low,
            candle_close=target.Close,
            candle_range=c_range,
            candle_body=c_body,
            volatility_baseline=effective_mtr,
            spike_ratio=spike_ratio,
            config=config
        )
