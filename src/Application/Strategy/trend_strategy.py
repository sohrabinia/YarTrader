import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

class TrendSignalType(str, Enum):
    NO_SIGNAL = "NO_SIGNAL"
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

@dataclass(frozen=True)
class TrendConfig:
    """
    Configuration parameters for deterministic Trend Strategy evaluation.

    Formulas:
    - Fast SMA (Fast_T) = SMA(Close, fast_period) over window [T-fast_period+1 .. T]
    - Slow SMA (Slow_T) = SMA(Close, slow_period) over window [T-slow_period+1 .. T]
    - Trend Spread (Spread_T) = Fast_T - Slow_T
    - True Range (TR_t) = max(High_t - Low_t, abs(High_t - Close_{t-1}), abs(Low_t - Close_{t-1}))
    - Volatility Baseline (MTR_T) = SMA(TR, slow_period) for candles prior to T
    - Normalized Trend Strength = abs(Spread_T) / max(MTR_T, min_volatility_baseline)
    - Signal Logic:
      - TREND_UP if Fast_T > Slow_T AND Normalized Trend Strength >= minimum_trend_strength
      - TREND_DOWN if Fast_T < Slow_T AND Normalized Trend Strength >= minimum_trend_strength
      - NO_SIGNAL otherwise
    """
    fast_period: int = 5
    slow_period: int = 20
    minimum_trend_strength: float = 0.5
    min_volatility_baseline: float = 0.1

    def validate(self) -> None:
        if self.fast_period < 2 or self.fast_period >= self.slow_period:
            raise ValidationException("fast_period must be >= 2 and strictly less than slow_period")
        if self.slow_period > 500:
            raise ValidationException("slow_period must be <= 500")
        if self.minimum_trend_strength < 0.0 or self.minimum_trend_strength > 50.0:
            raise ValidationException("minimum_trend_strength must be non-negative and <= 50.0")
        if self.min_volatility_baseline < 0.0:
            raise ValidationException("min_volatility_baseline must be non-negative")

@dataclass(frozen=True)
class TrendStrategyResult:
    """
    Immutable, deterministic result object for Trend Strategy evaluation at timestamp T.
    """
    symbol: str
    interval: str
    evaluation_time: datetime
    signal_type: TrendSignalType
    fast_sma: float
    slow_sma: float
    trend_spread: float
    volatility_baseline: float
    normalized_trend_strength: float
    config: TrendConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "evaluation_time": self.evaluation_time.isoformat() if hasattr(self.evaluation_time, "isoformat") else str(self.evaluation_time),
            "signal_type": self.signal_type.value,
            "metrics": {
                "fast_sma": round(self.fast_sma, 4),
                "slow_sma": round(self.slow_sma, 4),
                "trend_spread": round(self.trend_spread, 4),
                "volatility_baseline": round(self.volatility_baseline, 4),
                "normalized_trend_strength": round(self.normalized_trend_strength, 2)
            },
            "config": {
                "fast_period": self.config.fast_period,
                "slow_period": self.config.slow_period,
                "minimum_trend_strength": self.config.minimum_trend_strength
            }
        }

class TrendStrategyEngine:
    """
    Pure, deterministic Trend Strategy decision engine.
    Guarantees strict zero look-ahead bias: evaluation at index T uses ONLY candles <= T.
    """
    def evaluate(
        self,
        symbol: str,
        interval: str,
        candles: List[MarketDataPoint],
        config: Optional[TrendConfig] = None
    ) -> TrendStrategyResult:
        if not config:
            config = TrendConfig()
        config.validate()

        if not candles:
            return TrendStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=datetime.now(timezone.utc),
                signal_type=TrendSignalType.INSUFFICIENT_DATA,
                fast_sma=0.0, slow_sma=0.0, trend_spread=0.0,
                volatility_baseline=0.0, normalized_trend_strength=0.0,
                config=config
            )

        # Sort candles strictly chronologically by timestamp
        sorted_candles = sorted(candles, key=lambda c: c.Timestamp)

        # Cold start check: require at least slow_period + 1 candles
        if len(sorted_candles) < config.slow_period + 1:
            latest_c = sorted_candles[-1]
            return TrendStrategyResult(
                symbol=symbol,
                interval=interval,
                evaluation_time=latest_c.Timestamp,
                signal_type=TrendSignalType.INSUFFICIENT_DATA,
                fast_sma=latest_c.Close, slow_sma=latest_c.Close,
                trend_spread=0.0, volatility_baseline=0.0,
                normalized_trend_strength=0.0, config=config
            )

        # Target candle at index T (latest candle in window)
        target = sorted_candles[-1]

        # Calculate Fast SMA and Slow SMA over window [T-period+1 .. T]
        fast_window = sorted_candles[-config.fast_period:]
        slow_window = sorted_candles[-config.slow_period:]

        fast_sma = sum(c.Close for c in fast_window) / float(config.fast_period)
        slow_sma = sum(c.Close for c in slow_window) / float(config.slow_period)
        trend_spread = fast_sma - slow_sma

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
            baseline_window = tr_list[-config.slow_period:]
            mtr = sum(baseline_window) / float(len(baseline_window))
            effective_mtr = max(mtr, config.min_volatility_baseline)

        normalized_trend_strength = abs(trend_spread) / effective_mtr if effective_mtr > 0 else 0.0

        # Signal Logic
        signal = TrendSignalType.NO_SIGNAL
        if normalized_trend_strength >= config.minimum_trend_strength:
            if trend_spread > 0:
                signal = TrendSignalType.TREND_UP
            elif trend_spread < 0:
                signal = TrendSignalType.TREND_DOWN

        return TrendStrategyResult(
            symbol=symbol,
            interval=interval,
            evaluation_time=target.Timestamp,
            signal_type=signal,
            fast_sma=fast_sma,
            slow_sma=slow_sma,
            trend_spread=trend_spread,
            volatility_baseline=effective_mtr,
            normalized_trend_strength=normalized_trend_strength,
            config=config
        )
