"""Autonomous, DEMO-only MT5 strategy-to-execution loop.

This worker never sends LIVE orders. It only submits a DEMO order when fresh
broker data produces a qualified strategy candidate and all safety gates pass.
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.Data.MarketData.Models.models import MarketDataPoint
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Infrastructure.exceptions import ValidationException
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, ProductionRiskPolicy

logger = logging.getLogger("AutonomousDemoTrader")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_START_LOCK = threading.Lock()
_WORKER: Optional[threading.Thread] = None


def _read_flag() -> bool:
    """Read the explicit opt-in flag from process env or the project env files."""
    value = os.environ.get("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED")
    if value is None:
        value = os.environ.get("AUTONOMOUS_DEMO_TRADING_ENABLED")
    if value is None:
        for filename in (".env.production", ".env"):
            try:
                for line in (_PROJECT_ROOT / filename).read_text(encoding="utf-8-sig").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED="):
                        value = stripped.split("=", 1)[1].strip().strip("\"'").lower()
                        break
            except OSError:
                continue
            if value is not None:
                break
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def calculate_demo_volume_by_risk(
    mt5: Any, symbol: str, direction: str, entry: float, stop_loss: float,
    symbol_info: Dict[str, Any], balance: float, equity: float, risk_pct: float = ProductionRiskPolicy.TARGET_RISK_PCT,
) -> Dict[str, Any]:
    """Size DEMO orders using MT5's authoritative stop-loss PnL calculation."""
    values = (entry, stop_loss, balance, equity, risk_pct)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in values):
        raise ValidationException("Risk sizing received invalid numeric inputs.")
    target_risk_pct = float(ProductionRiskPolicy.TARGET_RISK_PCT)
    min_risk_pct = float(ProductionRiskPolicy.MIN_ADAPTIVE_RISK_PCT)
    max_risk_pct = float(ProductionRiskPolicy.HARD_CEILING_RISK_PCT)
    if (min(float(entry), float(stop_loss), float(balance), float(equity), float(risk_pct)) <= 0
            or risk_pct < min_risk_pct or risk_pct > max_risk_pct):
        raise ValidationException(f"Adaptive risk must be between {min_risk_pct:.2f}% and {max_risk_pct:.2f}% per trade.")
    volume_min = float(symbol_info.get("volume_min") or 0.0)
    volume_max = float(symbol_info.get("volume_max") or 0.0)
    volume_step = float(symbol_info.get("volume_step") or 0.0)
    risk_basis = min(float(balance), float(equity))
    if min(volume_min, volume_max, volume_step, risk_basis) <= 0 or mt5 is None:
        raise ValidationException("Broker contract or current wallet risk facts are incomplete.")
    if direction == "BUY":
        order_type_code = mt5.ORDER_TYPE_BUY
    elif direction == "SELL":
        order_type_code = mt5.ORDER_TYPE_SELL
    else:
        raise ValidationException(f"Unsupported direction for DEMO risk sizing: {direction}")
    risk_budget = risk_basis * (float(risk_pct) / 100.0)
    min_lot_profit = mt5.order_calc_profit(order_type_code, symbol, volume_min, float(entry), float(stop_loss))
    if min_lot_profit is None or not math.isfinite(float(min_lot_profit)):
        raise ValidationException("MT5 order_calc_profit could not validate minimum-lot stop-loss risk; fail closed.")
    minimum_lot_risk = abs(float(min_lot_profit))
    if minimum_lot_risk <= 0 or risk_budget <= 0:
        raise ValidationException("Broker minimum-lot risk or current wallet risk budget is invalid.")
    if minimum_lot_risk > risk_budget * 1.000001:
        return {"allowed": False, "reason": "Broker minimum lot would exceed the adaptive current-wallet risk budget.",
                "risk_basis_usd": round(risk_basis, 2), "risk_budget_usd": round(risk_budget, 4),
                "minimum_lot_risk_usd": round(minimum_lot_risk, 4)}
    risk_per_lot = minimum_lot_risk / volume_min
    raw_volume = risk_budget / risk_per_lot
    volume = min(math.floor((raw_volume + 1e-12) / volume_step) * volume_step, volume_max)
    volume_digits = max(0, min(8, len(str(volume_step).rstrip("0").split(".")[-1]) if "." in str(volume_step) else 0))
    volume = round(volume, volume_digits)
    if volume + 1e-12 < volume_min:
        return {"allowed": False, "reason": "Broker minimum lot would exceed the adaptive current-wallet risk budget.",
                "risk_basis_usd": round(risk_basis, 2), "risk_budget_usd": round(risk_budget, 4),
                "minimum_lot_risk_usd": round(minimum_lot_risk, 4)}
    volume_profit = mt5.order_calc_profit(order_type_code, symbol, volume, float(entry), float(stop_loss))
    if volume_profit is None or not math.isfinite(float(volume_profit)):
        raise ValidationException("MT5 could not verify selected-volume stop-loss risk; fail closed.")
    estimated_risk = abs(float(volume_profit))
    if estimated_risk > risk_budget * 1.000001:
        return {"allowed": False, "reason": "Broker-calculated order risk exceeds the adaptive wallet budget.",
                "risk_basis_usd": round(risk_basis, 2), "risk_budget_usd": round(risk_budget, 4),
                "estimated_risk_usd": round(estimated_risk, 4)}
    return {"allowed": True, "volume": volume, "risk_basis_usd": round(risk_basis, 2),
            "risk_budget_usd": round(risk_budget, 4), "estimated_risk_usd": round(estimated_risk, 4),
            "minimum_lot_risk_usd": round(minimum_lot_risk, 4), "risk_per_trade_pct": float(risk_pct)}


class AutonomousDemoTrader:
    """Small, fail-closed strategy executor with strict DEMO gates."""

    TIMEFRAMES = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "H1": "TIMEFRAME_H1",
    }
    MIN_CONFIDENCE = 70.0
    MIN_RR = 1.8
    RISK_PER_TRADE_PCT = ProductionRiskPolicy.TARGET_RISK_PCT
    MAX_ENTRY_DRIFT_R = 0.35
    MAX_TICK_BAR_GAP_SECONDS = 300

    def __init__(self, adapter: Optional[RealMT5BrokerAdapter] = None) -> None:
        self.adapter = adapter or RealMT5BrokerAdapter(auto_initialize=True)
        self.executor = DemoExecutionEngine(adapter=self.adapter, demo_mode=True)
        self.orchestrator = StrategyOrchestrator()
        self._last_attempt: Dict[str, str] = {}
        self._last_report: Dict[str, Any] = {}

    @staticmethod
    def _field(row: Any, key: str, default: Any = None) -> Any:
        try:
            return row[key]
        except (KeyError, TypeError, IndexError, ValueError):
            return getattr(row, key, default)

    def _fetch_candles(self, symbol: str, timeframe: str, count: int = 200) -> List[Dict[str, Any]]:
        mt5 = self.adapter._mt5
        timeframe_code = getattr(mt5, self.TIMEFRAMES[timeframe])
        rows = mt5.copy_rates_from_pos(symbol, timeframe_code, 0, count)
        if rows is None or len(rows) < 60:
            raise ValidationException(f"Insufficient live broker candles for {symbol} {timeframe}.")
        candles = []
        for row in rows:
            candles.append({
                "timestamp": int(self._field(row, "time", 0)),
                "open": float(self._field(row, "open", 0.0)),
                "high": float(self._field(row, "high", 0.0)),
                "low": float(self._field(row, "low", 0.0)),
                "close": float(self._field(row, "close", 0.0)),
                "volume": float(self._field(row, "tick_volume", 0.0) or 0.0),
            })
        candles.sort(key=lambda candle: candle["timestamp"])
        if any(not all(math.isfinite(c[k]) for k in ("open", "high", "low", "close")) for c in candles):
            raise ValidationException(f"Non-finite OHLC data found for {symbol} {timeframe}.")
        if any(c["low"] <= 0 or c["high"] < c["low"] for c in candles):
            raise ValidationException(f"Invalid OHLC geometry found for {symbol} {timeframe}.")
        return candles

    def _log_event(self, event: Dict[str, Any]) -> None:
        event["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            folder = _PROJECT_ROOT / "runtime_logs"
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "autonomous_demo_trader.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except OSError:
            logger.exception("Unable to persist autonomous DEMO trader event")
        logger.info("Autonomous DEMO trader: %s", event)

    def _evaluate_daily_risk(self, account: Dict[str, Any], broker_tick_time: int) -> Dict[str, Any]:
        from src.Risk.Services.daily_loss_kill_switch import (
            DailyLossKillSwitch, calculate_yartrader_daily_pnl,
        )
        risk_now = datetime.now(timezone.utc)
        equity = float(account.get("equity") or 0.0)
        if not math.isfinite(equity) or equity <= 0:
            return {"allowed": False, "reason": "KILL_SWITCH_ERROR", "meta": {}}
        pnl = calculate_yartrader_daily_pnl(self.adapter, now_utc=risk_now)
        allowed, reason, meta = DailyLossKillSwitch.get_instance().evaluate_daily_loss(
            equity, now_utc=risk_now, bot_daily_pnl=pnl["total_pnl"]
        )
        meta.update({
            "yartrader_daily_realized_pnl": pnl["realized_pnl"],
            "yartrader_daily_floating_pnl": pnl["floating_pnl"],
            "yartrader_daily_total_pnl": pnl["total_pnl"],
            "yartrader_owned_deals": pnl["owned_deal_count"],
            "yartrader_open_positions": pnl["owned_open_positions"],
        })
        return {"allowed": allowed, "reason": reason, "meta": meta, "pnl": pnl}

    @staticmethod
    def _derive_structural_stop(
        candles: List[Dict[str, Any]], direction: str, entry: float,
        lookback: int = 12, atr_period: int = 14,
    ) -> Optional[float]:
        """Derive a stop from closed-bar structure with an ATR buffer; reject unstable geometry."""
        if direction not in ("BUY", "SELL") or not math.isfinite(entry) or entry <= 0:
            return None
        if len(candles) < max(lookback, atr_period) + 1:
            return None
        closed = candles[-(max(lookback, atr_period) + 1):]
        try:
            ranges = []
            for i in range(1, len(closed)):
                c, prev = closed[i], closed[i - 1]
                tr = max(float(c["high"]) - float(c["low"]),
                         abs(float(c["high"]) - float(prev["close"])),
                         abs(float(c["low"]) - float(prev["close"])))
                if not math.isfinite(tr) or tr <= 0:
                    return None
                ranges.append(tr)
            atr = sum(ranges[-atr_period:]) / min(len(ranges), atr_period)
            recent = closed[-lookback:]
            if direction == "BUY":
                swing = min(float(c["low"]) for c in recent)
                stop = swing - 0.15 * atr
                distance = entry - stop
            else:
                swing = max(float(c["high"]) for c in recent)
                stop = swing + 0.15 * atr
                distance = stop - entry
            # Reject stops that are inside the market or so wide that the setup is not actionable.
            if not math.isfinite(stop) or distance <= 0 or distance > 3.0 * atr:
                return None
            return stop
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _m1_entry_confirmed(candles: List[Dict[str, Any]], direction: str) -> bool:
        """Require a closed-M1 micro-structure break before executing a higher-TF setup."""
        if len(candles) < 3 or direction not in ("BUY", "SELL"):
            return False
        previous, latest = candles[-2], candles[-1]
        values = [float(c[key]) for c in (previous, latest) for key in ("open", "high", "low", "close")]
        if any(not math.isfinite(value) for value in values):
            return False
        if direction == "BUY":
            return float(latest["close"]) > float(latest["open"]) and float(latest["close"]) > float(previous["high"])
        return float(latest["close"]) < float(latest["open"]) and float(latest["close"]) < float(previous["low"])

    def run_once(self, symbol_override: Optional[str] = None) -> Dict[str, Any]:
        """Run one read/decide/execute cycle for a selected enabled symbol."""
        if not _read_flag():
            return {"status": "DISABLED", "reason": "Explicit DEMO auto-trading opt-in is disabled."}

        try:
            self.adapter.verify_safety_and_account(operation_type="DEMO")
            account = self.adapter.get_account_info()
            terminal = self.adapter.get_terminal_info()
            if not account or not terminal:
                raise ValidationException("DEMO account or terminal facts are unavailable.")
            if account.get("trade_mode") != 0:
                raise ValidationException("Refusing execution because active account is not MT5 DEMO.")
            if not terminal.get("connected") or not terminal.get("trade_allowed") or terminal.get("tradeapi_disabled"):
                raise ValidationException("MT5 terminal is disconnected or trading permissions are disabled.")

            symbol = str(symbol_override or os.environ.get("YARTRADER_MT5_SYMBOL", "XAUUSD")).strip().upper()
            symbol_info = self.adapter.get_symbol_info(symbol)
            tick = self.adapter.get_symbol_tick(symbol)
            if not symbol_info or not tick or float(tick.get("bid") or 0) <= 0 or float(tick.get("ask") or 0) <= 0:
                raise ValidationException(f"Valid live quote and symbol contract are unavailable for {symbol}.")

            # Compare MT5 server timestamps to one another; local PC clock may use a different zone.
            m1 = self._fetch_candles(symbol, "M1", 120)
            tick_time = int(tick.get("time") or 0)
            bar_time = int(m1[-1]["timestamp"])
            if tick_time <= 0 or abs(tick_time - bar_time) > self.MAX_TICK_BAR_GAP_SECONDS:
                raise ValidationException(
                    f"Quote/data freshness mismatch: MT5 tick and latest M1 bar differ by {abs(tick_time - bar_time)} seconds."
                )

            daily_guard = self._evaluate_daily_risk(account, tick_time)
            if not daily_guard["allowed"]:
                meta = daily_guard.get("meta", {})
                return {
                    "status": "BLOCKED",
                    "reason": daily_guard.get("reason") or "DAILY_LOSS_LIMIT_REACHED",
                    "daily_loss_pct": meta.get("loss_pct"),
                    "current_equity": meta.get("current_equity"),
                    "yartrader_daily_pnl": meta.get("yartrader_daily_total_pnl"),
                }

            positions = self.adapter.get_positions(symbol=symbol)
            if positions is None:
                raise ValidationException("Open-position state is unknown; fail-closed.")
            if positions:
                return {"status": "SKIPPED", "reason": "An open position already exists for this symbol."}

            # MT5 position 0 is the still-forming candle. Use it only for quote
            # freshness checks; strategy decisions must use fully closed candles.
            per_tf: Dict[str, List[Dict[str, Any]]] = {"M1": m1[:-1]}
            for timeframe in ("M5", "M15", "H1"):
                fetched = self._fetch_candles(symbol, timeframe, 201)
                per_tf[timeframe] = fetched[:-1]

            candidates = []
            for timeframe in ("M5", "M15", "H1"):
                report = self.orchestrator.evaluate_all_strategies(
                    symbol=symbol,
                    primary_timeframe=timeframe,
                    candles=per_tf[timeframe],
                    all_timeframe_candles=per_tf,
                    spread_pip=(float(tick["ask"]) - float(tick["bid"])) /
                               ProfessionalRiskEngine().get_pip_size(symbol),
                    account_balance=float(account.get("balance") or 0.0),
                )
                report_candidates = report.get("candidates") or []
                if not report_candidates and report.get("best_candidate"):
                    report_candidates = [report["best_candidate"]]
                # Do not let a mediocre top-ranked candidate hide another valid
                # strategy on the same timeframe. Keep the strongest candidate that
                # already clears the common execution-quality gates for this symbol.
                qualified_for_timeframe = [
                    candidate for candidate in report_candidates
                    if candidate.get("direction") in ("BUY", "SELL")
                    and float(candidate.get("confidence") or 0.0) >= self.MIN_CONFIDENCE
                    and float(candidate.get("risk_reward") or 0.0) >= self.MIN_RR
                    and float(candidate.get("entry") or 0.0) > 0
                    and float(candidate.get("stop_loss") or 0.0) > 0
                    and float(candidate.get("take_profit") or 0.0) > 0
                ]
                qualified_for_timeframe.sort(
                    key=lambda item: float(item.get("confidence") or 0.0) * float(item.get("risk_reward") or 0.0),
                    reverse=True,
                )
                if qualified_for_timeframe:
                    candidates.append(qualified_for_timeframe[0])

            # Shared regime-aware policy: do not blindly reverse in trends, fade
            # range edges only, and freeze a volatility-based target before spike entry.
            from src.Decision.Intelligence.market_behavior_policy import MarketBehaviorPolicy
            behavior = MarketBehaviorPolicy().evaluate(per_tf["M15"])
            self._log_event({"event": "market_behavior", "symbol": symbol, **behavior.to_dict()})
            if behavior.regime in ("TRANSITION", "UNCERTAIN") or behavior.direction == "WAIT":
                return {"status": "WAIT", "symbol": symbol, "market_regime": behavior.regime,
                        "reason": behavior.reason}
            regime_candidates = []
            for item in candidates:
                item = dict(item)
                item["market_regime"] = behavior.regime
                proposed_direction = str(item.get("direction", "")).upper()
                if proposed_direction != behavior.direction:
                    continue
                if behavior.regime == "SPIKE":
                    # Target is fixed before submission; SL remains mandatory and broker-risk sized.
                    live_entry = float(tick["ask"] if proposed_direction == "BUY" else tick["bid"])
                    item["take_profit"] = live_entry + behavior.spike_target_distance * (1 if proposed_direction == "BUY" else -1)
                    item["spike_target_precomputed"] = True
                elif behavior.regime == "RANGE":
                    live_price = float(tick["ask"] if proposed_direction == "BUY" else tick["bid"])
                    if proposed_direction == "BUY" and live_price > behavior.entry_zone_low + 0.25*(behavior.channel_high-behavior.channel_low):
                        continue
                    if proposed_direction == "SELL" and live_price < behavior.entry_zone_high - 0.25*(behavior.channel_high-behavior.channel_low):
                        continue
                    item["take_profit"] = behavior.channel_low + 0.5*(behavior.channel_high-behavior.channel_low)
                regime_candidates.append(item)
            candidates = regime_candidates

            eligible = [
                c for c in candidates
                if c.get("direction") in ("BUY", "SELL")
                and float(c.get("confidence") or 0.0) >= self.MIN_CONFIDENCE
                and float(c.get("risk_reward") or 0.0) >= self.MIN_RR
                and float(c.get("entry") or 0.0) > 0
                and float(c.get("stop_loss") or 0.0) > 0
                and float(c.get("take_profit") or 0.0) > 0
            ]
            if not eligible:
                return {"status": "WAIT", "symbol": symbol, "reason": "No candidate passed confidence, R/R and price-level checks."}

            # One high-quality candidate is sufficient when no other candidate also
            # clears the same confidence/RR gates in the opposite direction. Requiring
            # two qualifying candidates caused permanent WAIT states for sparse setups.
            directions = {str(c["direction"]).upper() for c in eligible}
            if len(directions) != 1:
                return {"status": "WAIT", "reason": "High-confidence qualified candidates conflict across timeframes."}

            direction = next(iter(directions))
            # M15/H1 determine direction; a closed M1 structure break times the entry.
            if not self._m1_entry_confirmed(per_tf["M1"], direction):
                return {
                    "status": "WAIT",
                    "symbol": symbol,
                    "direction": direction,
                    "reason": "M1 entry confirmation is absent; wait for a closed-candle micro-structure break.",
                }
            entry = float(tick["ask"] if direction == "BUY" else tick["bid"])
            balance = float(account.get("balance") or 0.0)
            equity = float(account.get("equity") or 0.0)
            ranked = sorted(eligible, key=lambda c: float(c["confidence"]) * float(c["risk_reward"]), reverse=True)
            candidate = None
            sizing = None
            actual_rr = 0.0
            selection_reason = "All qualified setups failed current-quote, R/R, or broker-risk checks."

            # Try qualified setups in rank order. A wide stop or broker minimum-lot
            # mismatch on one timeframe must not hide a tighter valid setup on another.
            for option in ranked:
                original_entry = float(option["entry"])
                timeframe = str(option.get("timeframe") or "M15")
                stop_candles = per_tf.get(timeframe, per_tf["M15"])
                option_sl = self._derive_structural_stop(stop_candles, direction, entry)
                if option_sl is None:
                    selection_reason = "No valid structure/ATR stop found; refusing a guessed stop."
                    continue
                option_tp = float(option["take_profit"])
                original_risk = abs(original_entry - float(option.get("stop_loss") or 0.0))
                if original_risk <= 0 or abs(entry - original_entry) > original_risk * self.MAX_ENTRY_DRIFT_R:
                    selection_reason = "Current quote has moved too far from the qualified setup entry."
                    continue
                if direction == "BUY" and not (option_sl < entry < option_tp):
                    selection_reason = "BUY stop/entry/target geometry is no longer valid at the live quote."
                    continue
                if direction == "SELL" and not (option_tp < entry < option_sl):
                    selection_reason = "SELL stop/entry/target geometry is no longer valid at the live quote."
                    continue
                option_rr = abs(option_tp - entry) / abs(entry - option_sl)
                if not math.isfinite(option_rr) or option_rr < self.MIN_RR:
                    selection_reason = "Live quote no longer supports the minimum risk/reward ratio."
                    continue
                # Allocate more risk only to stronger setups; weaker setups receive less.
                # This is a sizing heuristic, not a claimed calibrated win probability.
                confidence = max(0.0, min(100.0, float(option.get("confidence") or 0.0)))
                rr_quality = max(0.0, min(1.0, (option_rr - self.MIN_RR) / max(self.MIN_RR, 1e-9)))
                confidence_quality = max(0.0, min(1.0, (confidence - self.MIN_CONFIDENCE) / max(100.0 - self.MIN_CONFIDENCE, 1e-9)))
                quality = 0.7 * confidence_quality + 0.3 * rr_quality
                adaptive_risk_pct = ProductionRiskPolicy.MIN_ADAPTIVE_RISK_PCT + quality * (ProductionRiskPolicy.HARD_CEILING_RISK_PCT - ProductionRiskPolicy.MIN_ADAPTIVE_RISK_PCT)
                option_sizing = calculate_demo_volume_by_risk(
                    self.adapter._mt5, symbol, direction, entry, option_sl, symbol_info,
                    balance, equity, adaptive_risk_pct,
                )
                if not option_sizing["allowed"]:
                    selection_reason = str(option_sizing.get("reason") or "Broker risk budget rejected this setup.")
                    continue
                candidate = option
                sl, tp = option_sl, option_tp
                actual_rr = option_rr
                sizing = option_sizing
                break

            if candidate is None or sizing is None:
                return {"status": "WAIT", "symbol": symbol, "reason": selection_reason}

            volume = float(sizing["volume"])
            risk_budget = float(sizing["risk_budget_usd"])
            risk_basis = float(sizing["risk_basis_usd"])
            estimated_min_risk = float(sizing["estimated_risk_usd"])

            attempt_key = f"{symbol}:{candidate.get('timeframe')}:{candidate.get('strategy_name')}:{direction}:{per_tf[str(candidate.get('timeframe') if candidate.get('timeframe') in per_tf else 'M15')][-1]['timestamp']}"
            if self._last_attempt.get(symbol) == attempt_key:
                return {"status": "SKIPPED", "reason": "This setup candle has already been attempted."}

            result = self.executor.execute_demo_decision(
                symbol=symbol,
                direction=direction,
                volume=volume,
                price=entry,
                sl=sl,
                tp=tp,
                comment="YarTrader Auto DEMO",
                magic=143056,
                decision_id=str(candidate.get("strategy_id") or attempt_key),
            )
            self._last_attempt[symbol] = attempt_key
            payload = {
                "status": result.Status,
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "confidence": candidate.get("confidence"),
                "risk_reward": round(actual_rr, 3),
                "estimated_risk_usd": round(estimated_min_risk, 4),
                "risk_budget_usd": round(risk_budget, 4),
                "risk_basis_usd": round(risk_basis, 2),
                "risk_per_trade_pct": sizing["risk_per_trade_pct"],
                "strategy": candidate.get("strategy_name"),
                "timeframe": candidate.get("timeframe"),
                "market_regime": candidate.get("market_regime"),
                "spike_target_precomputed": bool(candidate.get("spike_target_precomputed", False)),
                "order_id": result.OrderId,
                "deal_ticket": result.DealTicket,
                "comment": result.Comment,
            }
            self._log_event(payload)
            return payload
        except Exception as exc:
            result = {"status": "ERROR", "reason": str(exc)}
            self._log_event(result)
            return result


def _enabled_demo_symbols() -> List[str]:
    """Return enabled MT5 symbols from the canonical registry, ordered gold-first."""
    from src.Market.Universe.symbol_registry import SymbolRegistry
    registry = SymbolRegistry.get_instance()
    active_matrix = registry.get_active_matrix()
    symbols = sorted({str(item[0]).upper() for item in active_matrix},
                     key=lambda symbol: (symbol != "XAUUSD", symbol))
    # Only symbols present in the active MT5 registry may reach DEMO evaluation.
    return [symbol for symbol in symbols
            if str(registry.get_all_registered().get(symbol, {}).get("provider", "MT5")).upper() == "MT5"]


def run_autonomous_demo_trading_loop() -> None:
    """Crash-resistant multi-symbol polling loop; all orders remain broker-risk gated."""
    logger.info("Autonomous DEMO trader worker started.")
    trader: Optional[AutonomousDemoTrader] = None
    while True:
        try:
            if not _read_flag():
                time.sleep(10)
                continue
            if trader is None:
                trader = AutonomousDemoTrader()
            try:
                symbols = _enabled_demo_symbols()
            except Exception as exc:
                logger.error("Cannot resolve canonical DEMO symbol universe; failing closed: %s", exc)
                symbols = []
            results = []
            for symbol in symbols:
                result = trader.run_once(symbol_override=symbol)
                results.append(result)
                # Never open multiple fresh positions in one polling cycle. If a
                # trade is placed, the next cycle re-evaluates the whole universe.
                if result.get("status") not in ("WAIT", "SKIPPED", "BLOCKED", "ERROR", "DISABLED"):
                    break
                if result.get("status") in ("BLOCKED", "DISABLED") and (
                    result.get("daily_loss_pct") is not None
                    or result.get("status") == "DISABLED"
                    or "daily" in str(result.get("reason", "")).lower()
                ):
                    break
            result = results[-1] if results else {
                "status": "BLOCKED",
                "reason": "No enabled MT5 symbols are available in the canonical market registry.",
            }
            if result.get("status") in ("WAIT", "SKIPPED", "BLOCKED", "ERROR"):
                signature = (result.get("symbol"), result.get("status"), result.get("reason"), result.get("daily_loss_pct"))
                if trader._last_report.get("signature") != signature:
                    trader._log_event({**result, "event": "cycle_status"})
                    trader._last_report = {"signature": signature}
            else:
                logger.info("Autonomous DEMO cycle result: %s", result)
            time.sleep(30)
        except BaseException:
            logger.exception("Autonomous DEMO trader worker recovered from an unexpected failure")
            trader = None
            time.sleep(10)


def start_autonomous_demo_trader() -> None:
    """Start exactly one daemon worker."""
    global _WORKER
    with _START_LOCK:
        if _WORKER is not None and _WORKER.is_alive():
            return
        _WORKER = threading.Thread(
            target=run_autonomous_demo_trading_loop,
            name="AutonomousDemoTrader",
            daemon=True,
        )
        _WORKER.start()
