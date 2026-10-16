"""Diagnostic price-path experiments; not a substitute for YarTrader strategy backtests.

This module intentionally labels its output as a proxy because it does not invoke
YarTrader's signal, entry/exit, position-sizing, or risk engines. Do not use these
results as evidence of strategy profitability.
"""

import hashlib
import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ExperimentResult:
    experiment_id: str
    strategy_version: str
    dataset_hash: str
    parameter_hash: str
    market: str
    timeframe: str
    perturbations: Dict[str, Any]
    total_trades: int
    win_rate: float
    net_pnl_usd: float
    profit_factor: float
    max_drawdown_usd: float
    executed_at: str
    evaluation_mode: str = "DIAGNOSTIC_LONG_ONLY_PRICE_PATH"
    is_strategy_backtest: bool = False
    max_drawdown_pct: float = 0.0
    max_favorable_excursion_price: float = 0.0
    max_adverse_excursion_price: float = 0.0
    warnings: Optional[List[str]] = None


class PerturbatedExperimentRunner:
    """Run a clearly labelled long-only price-path diagnostic, not a strategy test.

    The legacy interface does not accept a strategy/signal engine, so this class
    cannot honestly claim to execute the supplied strategy_version. Its metrics are
    diagnostic proxies only. Production strategy evaluation belongs in
    BacktestAndLearningEngine / the staged backtest pipeline.
    """

    def run_experiment(
        self,
        strategy_version: str,
        market: str,
        timeframe: str,
        historical_bars: List[Dict[str, Any]],
        slippage_perturbation_pip: float = 0.5,
        spread_perturbation_pip: float = 1.0,
        parameter_overrides: Optional[Dict[str, Any]] = None,
    ) -> ExperimentResult:
        if not isinstance(historical_bars, list) or len(historical_bars) < 6:
            raise ValueError("At least 6 historical bars are required for the 5-bar diagnostic horizon.")
        for name, value in (("slippage_perturbation_pip", slippage_perturbation_pip),
                            ("spread_perturbation_pip", spread_perturbation_pip)):
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
                raise ValueError(f"{name} must be a finite non-negative number.")

        closes: List[float] = []
        highs: List[Optional[float]] = []
        lows: List[Optional[float]] = []
        has_full_ohlc = all(isinstance(bar, dict) and all(k in bar and bar[k] is not None for k in ("open", "high", "low", "close")) for bar in historical_bars)
        for index, bar in enumerate(historical_bars):
            if not isinstance(bar, dict) or "close" not in bar or bar["close"] is None:
                raise ValueError(f"Historical bar {index} is missing a close price; refusing to fabricate data.")
            try:
                close = float(bar["close"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Historical bar {index} has an invalid close price.") from exc
            if not math.isfinite(close) or close <= 0:
                raise ValueError(f"Historical bar {index} close must be finite and greater than zero.")
            closes.append(close)
            high_value = low_value = None
            if isinstance(bar, dict) and bar.get("high") is not None and bar.get("low") is not None:
                try:
                    high_value, low_value = float(bar["high"]), float(bar["low"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Historical bar {index} has invalid high/low prices.") from exc
                if not math.isfinite(high_value) or not math.isfinite(low_value) or low_value <= 0 or high_value < low_value:
                    raise ValueError(f"Historical bar {index} high/low range is invalid.")
                if high_value < close or low_value > close:
                    raise ValueError(f"Historical bar {index} close must lie between low and high.")
            highs.append(high_value)
            lows.append(low_value)

        param_overrides = parameter_overrides or {}
        dataset_payload = json.dumps(historical_bars, sort_keys=True, separators=(",", ":"), default=str)
        dataset_hash = hashlib.sha256(dataset_payload.encode("utf-8")).hexdigest()[:12]
        param_payload = json.dumps({
            "slippage_perturbation_pip": float(slippage_perturbation_pip),
            "spread_perturbation_pip": float(spread_perturbation_pip),
            "overrides": param_overrides,
        }, sort_keys=True, separators=(",", ":"), default=str)
        param_hash = hashlib.sha256(param_payload.encode("utf-8")).hexdigest()[:12]

        wins = 0
        total_pnl = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        total_trades = 0
        equity = 0.0
        peak_equity = 0.0
        max_drawdown = 0.0
        max_favorable_excursion = 0.0
        max_adverse_excursion = 0.0
        friction_cost = (float(spread_perturbation_pip) + float(slippage_perturbation_pip)) * 0.1

        # Fixed-horizon LONG-only diagnostic. It does not consume trading signals.
        step = max(1, len(closes) // 50)
        for i in range(0, len(closes) - 5, step):
            entry_price = closes[i]
            raw_delta = closes[i + 5] - entry_price
            if has_full_ohlc:
                # OHLC extrema over the holding horizon show the path risk hidden by closes.
                horizon_high = max(highs[i + 1:i + 6])
                horizon_low = min(lows[i + 1:i + 6])
                max_favorable_excursion = max(max_favorable_excursion, horizon_high - entry_price)
                max_adverse_excursion = max(max_adverse_excursion, entry_price - horizon_low)
            net_delta = raw_delta - friction_cost
            trade_pnl = net_delta * 100.0  # legacy illustrative conversion; not broker-accurate USD
            total_trades += 1
            if trade_pnl > 0:
                wins += 1
                gross_profit += trade_pnl
            elif trade_pnl < 0:
                gross_loss += abs(trade_pnl)
            total_pnl += trade_pnl
            equity += trade_pnl
            peak_equity = max(peak_equity, equity)
            max_drawdown = max(max_drawdown, peak_equity - equity)

        win_rate = round(wins / total_trades, 4) if total_trades else 0.0
        pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        # Drawdown is measured on the proxy's cumulative PnL path, not hard-coded.
        # Percentage is undefined when the diagnostic equity basis is non-positive;
        # use zero only as a clearly non-investable proxy statistic.
        diagnostic_start_equity = 10000.0
        max_dd_pct = round((max_drawdown / (diagnostic_start_equity + peak_equity)) * 100.0, 4) if diagnostic_start_equity + peak_equity > 0 else 0.0

        return ExperimentResult(
            experiment_id=f"exp-{uuid.uuid4().hex[:8]}",
            strategy_version=strategy_version,
            dataset_hash=dataset_hash,
            parameter_hash=param_hash,
            market=market,
            timeframe=timeframe,
            perturbations={"slippage_pip": float(slippage_perturbation_pip),
                           "spread_pip": float(spread_perturbation_pip),
                           "overrides": param_overrides},
            total_trades=total_trades,
            win_rate=win_rate,
            net_pnl_usd=round(total_pnl, 2),
            profit_factor=pf,
            max_drawdown_usd=round(max_drawdown, 2),
            executed_at=datetime.now(timezone.utc).isoformat(),
            evaluation_mode="DIAGNOSTIC_LONG_ONLY_PRICE_PATH",
            is_strategy_backtest=False,
            max_drawdown_pct=max_dd_pct,
            max_favorable_excursion_price=round(max_favorable_excursion, 6),
            max_adverse_excursion_price=round(max_adverse_excursion, 6),
            warnings=[
                "Not a strategy backtest: strategy_version and parameter_overrides are not executed by this runner.",
                "Long-only fixed-horizon price changes are used instead of YarTrader entry/exit rules.",
                *( ["OHLC unavailable: favorable/adverse intrahorizon excursion was not computed."] if not has_full_ohlc else ["Favorable/adverse excursions use future OHLC extrema for diagnostics only; they do not determine actual fills or trade exits."] ),
                "PnL uses an illustrative fixed multiplier of 100 per price unit; it is not broker-accurate USD.",
                "Spread/slippage perturbations use a generic conversion and omit contract-specific costs, lot sizing, swap and realistic fills.",
                "Use BacktestAndLearningEngine / run_staged_backtest for strategy evaluation; validate costs and execution assumptions separately.",
            ],
        )
