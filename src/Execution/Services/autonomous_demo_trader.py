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
from src.Execution.Models.models import OrderRequest
from src.Infrastructure.exceptions import ValidationException
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
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }
    MIN_CONFIDENCE = 70.0
    MIN_RR = ProductionRiskPolicy.MINIMUM_RR
    RISK_PER_TRADE_PCT = ProductionRiskPolicy.TARGET_RISK_PCT
    MAX_ENTRY_DRIFT_R = 0.35
    MAX_TICK_BAR_GAP_SECONDS = 300

    def __init__(self, adapter: Optional[RealMT5BrokerAdapter] = None) -> None:
        self.adapter = adapter or RealMT5BrokerAdapter(auto_initialize=True)
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
        # MT5 position 0 is the still-forming candle. Strategy structure and
        # Base/M1 triggers must use only fully closed candles, so start at shift 1.
        rows = mt5.copy_rates_from_pos(symbol, timeframe_code, 1, count)
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

    def _evaluate_hierarchical_base_plan(
        self, per_tf: Dict[str, List[Dict[str, Any]]], tick: Dict[str, Any],
        symbol: str = "XAUUSD",
    ) -> Dict[str, Any]:
        """Delegate DEMO decisions to the same Base-only authority used by signals/API."""
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator

        primary_tf = "M1"
        candles = per_tf.get(primary_tf, [])
        try:
            if not candles:
                raise ValidationException("No closed M1 candles are available for canonical Base analysis.")
            report = StrategyOrchestrator().evaluate_all_strategies(
                symbol=symbol,
                primary_timeframe=primary_tf,
                candles=candles,
                all_timeframe_candles=per_tf,
                spread_pip=(
                    max(0.0, float(tick["ask"])-float(tick["bid"])) /
                    (0.1 if "XAU" in symbol.upper() else (1.0 if "BTC" in symbol.upper() else 0.0001))
                ),
            )
            plan = report.get("base_plan") or {}
            hierarchy = report.get("hierarchy") or {}
            reaction = report.get("reaction_analysis") or {}
            candidate = report.get("best_candidate")
            qualified = bool(
                candidate
                and str(candidate.get("strategy_name", "")).upper() == "BASE_HIERARCHY"
                and str(candidate.get("direction", "")).upper() in ("BUY", "SELL")
                and str(plan.get("status", "")).upper() == "PROPOSED"
                and str(report.get("model_status", "")).upper() == "COSTED_REACTION_MODEL_LOADED"
            )
            return {
                "status": "ORDER_PROPOSAL" if qualified else "WAIT",
                "reason": report.get("summary") or plan.get("reason") or
                          "No validated Base-only reaction proposal; no fallback strategy is permitted.",
                "structure": hierarchy.get("structure") or {},
                "hierarchy": hierarchy,
                "reaction_analysis": reaction,
                "model_status": report.get("model_status", "UNKNOWN"),
                "base_plan": plan,
                "order_plan": plan if qualified else {"status": "WAIT", "reason": plan.get("reason") or report.get("summary")},
                "decision_authority": "BASE_HIERARCHY",
                "execution_enabled": False,
                "execution_mode": "CANONICAL_BASE_ONLY_GATE",
            }
        except Exception as exc:
            logger.warning("Canonical Base-only DEMO analysis failed closed: %s", exc)
            return {
                "status": "WAIT",
                "reason": "Base-only analysis failed; no alternative strategy is permitted.",
                "structure": {},
                "hierarchy": {},
                "reaction_analysis": {"status": "WAIT", "execution_enabled": False},
                "model_status": "BASE_ANALYSIS_FAILED",
                "base_plan": {"status": "WAIT"},
                "order_plan": {"status": "WAIT", "reason": str(exc)},
                "decision_authority": "BASE_HIERARCHY",
                "execution_enabled": False,
                "execution_mode": "CANONICAL_BASE_ONLY_GATE",
            }

    @staticmethod
    def _base_behavior_is_primary() -> bool:
        """Hard-lock the autonomous trader to the single Base-behavior strategy.

        Legacy orchestrated strategies are intentionally not selectable from an
        environment override. They remain in the codebase for research/backward
        compatibility, but cannot be used by this autonomous execution worker.
        """
        return True

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

    def _reconcile_base_pending_order(
        self, symbol: str, base_plan: Dict[str, Any], tick: Dict[str, Any],
        account: Dict[str, Any], symbol_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Idempotently reconcile one YarTrader-owned Base pending order for a symbol."""
        orders = self.adapter.get_active_orders(symbol=symbol)
        if orders is None:
            return {"status": "BLOCKED", "reason": "Broker pending-order state is unknown; refusing duplicate or new entry."}
        mt5 = self.adapter._mt5
        owned = [
            order for order in orders
            if int(self._field(order, "magic", 0) or 0) == 100001
            and str(self._field(order, "comment", "") or "").startswith("YarBase")
        ]
        plan = base_plan.get("order_plan") or {}
        valid = base_plan.get("status") == "ORDER_PROPOSAL" and plan.get("status") == "PROPOSED"
        if not valid:
            cancelled = []
            for order in owned:
                ticket = int(self._field(order, "ticket", 0) or 0)
                if ticket <= 0:
                    return {"status": "BLOCKED", "reason": "Owned pending order has no valid broker ticket."}
                response = self.adapter.cancel_pending_order(ticket)
                if response.Status != "Cancelled":
                    return {"status": "BLOCKED", "reason": f"Could not cancel stale Base pending order {ticket}: {response.Comment}"}
                cancelled.append(ticket)
            return {"status": "WAIT", "reason": base_plan.get("reason", "No qualified Base reaction proposal."),
                    "cancelled_pending_orders": cancelled}

        try:
            direction = str(plan["direction"]).upper()
            order_type = str(plan["order_type"]).upper()
            entry, stop, target = float(plan["entry"]), float(plan["stop_loss"]), float(plan["take_profit"])
            expires = int(float(plan["expires_at"])) if plan.get("expires_at") is not None else None
            digits = int(symbol_info["digits"])
            if direction not in ("BUY", "SELL") or order_type not in ("BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"):
                raise ValueError("Unsupported Base pending order type or direction.")
            if not all(math.isfinite(x) and x > 0 for x in (entry, stop, target)):
                raise ValueError("Base plan contains invalid prices.")
            if (direction == "BUY" and not stop < entry < target) or (direction == "SELL" and not target < entry < stop):
                raise ValueError("Base pending order has invalid stop/entry/target geometry.")
            risk_distance = abs(entry - stop)
            reward_distance = abs(target - entry)
            if risk_distance <= 0 or reward_distance / risk_distance <= 1.0:
                raise ValueError("YarTrader requires reward/risk strictly greater than 1.0.")
            bid = float(tick.get("bid") or 0.0)
            ask = float(tick.get("ask") or 0.0)
            if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0.0 or ask < bid:
                raise ValueError("Current broker quote is invalid; pending order blocked.")
            # A pending order whose trigger has already crossed the executable quote
            # is stale: do not let MT5 turn it into an unintended immediate entry.
            trigger_is_valid = {
                "BUY_LIMIT": entry < ask,
                "SELL_LIMIT": entry > bid,
                "BUY_STOP": entry > ask,
                "SELL_STOP": entry < bid,
            }[order_type]
            if not trigger_is_valid:
                raise ValueError(f"{order_type} trigger is no longer valid against the current broker quote.")
            if expires is not None and expires <= int(tick.get("time") or time.time()):
                raise ValueError("Base pending order has expired.")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            return {"status": "BLOCKED", "reason": f"Invalid Base pending order plan: {exc}"}

        desired_type = getattr(mt5, {
            "BUY_LIMIT": "ORDER_TYPE_BUY_LIMIT", "SELL_LIMIT": "ORDER_TYPE_SELL_LIMIT",
            "BUY_STOP": "ORDER_TYPE_BUY_STOP", "SELL_STOP": "ORDER_TYPE_SELL_STOP",
        }[order_type], None)
        if desired_type is None:
            return {"status": "BLOCKED", "reason": "MT5 does not expose the requested pending-order type."}
        for order in owned:
            same = (
                int(self._field(order, "type", -1)) == int(desired_type)
                and abs(float(self._field(order, "price_open", 0.0)) - entry) <= 10 ** (-digits)
                and abs(float(self._field(order, "sl", 0.0)) - stop) <= 10 ** (-digits)
                and abs(float(self._field(order, "tp", 0.0)) - target) <= 10 ** (-digits)
                and (expires is None or int(self._field(order, "time_expiration", 0) or 0) in (0, expires))
            )
            if same:
                return {"status": "ALREADY_PENDING", "ticket": int(self._field(order, "ticket", 0)),
                        "order_type": order_type, "entry": entry}
        # Remove obsolete orders before replacing them; never stack duplicate Base orders.
        for order in owned:
            ticket = int(self._field(order, "ticket", 0) or 0)
            if ticket <= 0:
                return {"status": "BLOCKED", "reason": "Owned pending order has no valid broker ticket."}
            response = self.adapter.cancel_pending_order(ticket)
            if response.Status != "Cancelled":
                return {"status": "BLOCKED", "reason": f"Could not replace stale Base order {ticket}: {response.Comment}"}

        sizing = calculate_demo_volume_by_risk(
            mt5, symbol, direction, entry, stop, symbol_info,
            float(account.get("balance") or 0), float(account.get("equity") or 0),
            float(ProductionRiskPolicy.TARGET_RISK_PCT),
        )
        if not sizing.get("allowed"):
            return {"status": "RISK_BLOCKED", "reason": sizing.get("reason"), "risk": sizing}
        request = OrderRequest(
            Symbol=symbol, OrderType=order_type, Volume=float(sizing["volume"]),
            Price=round(entry, digits), StopLoss=round(stop, digits), TakeProfit=round(target, digits),
            Comment="YarBase", Magic=100001, Expiration=expires,
        )
        response = self.adapter.send_order_to_broker(request)
        self._log_event({
            "event": "base_pending_order_submission", "symbol": symbol,
            "order_type": order_type, "entry": entry, "stop_loss": stop, "take_profit": target,
            "expiration": expires, "risk": sizing, "broker_status": response.Status,
            "broker_order_id": response.OrderId, "broker_retcode": response.Retcode,
        })
        return {"status": "PENDING_PLACED" if response.Status == "Placed" else "ORDER_FAILED",
                "ticket": response.OrderId, "broker_status": response.Status,
                "reason": response.Comment, "risk": sizing, "order_type": order_type}

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
            # H4 Base candidates may remain valid for 8 H4 bars (32 hours).
            # Keep enough closed M1 history to count re-entry episodes over that
            # full horizon, not just the most recent two hours.
            m1 = self._fetch_candles(symbol, "M1", 2001)
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
            if len(positions) > 1:
                return {"status": "BLOCKED", "symbol": symbol, "reason": "Multiple open positions exist; reversal automation requires a single reconciled position."}
            # A single existing position is evaluated against the new, fully-confirmed setup below.
            # It is never blindly duplicated or closed before a qualified opposite setup exists.
            open_positions = positions

            # MT5 position 0 is the still-forming candle. Use it only for quote
            # freshness checks; strategy decisions must use fully closed candles.
            # _fetch_candles starts at MT5 shift=1, so every returned row is
            # already a fully closed candle. Do not drop the newest closed bar.
            per_tf: Dict[str, List[Dict[str, Any]]] = {"M1": m1}
            for timeframe in ("D1", "H4", "H1", "M30", "M15", "M5"):
                per_tf[timeframe] = self._fetch_candles(symbol, timeframe, 201)

            # The only enabled decision path is hierarchical Base behavior.
            # A proposal is not an order: pending-order execution and Base-driven
            # position exits/re-entry management must use a dedicated broker manager.
            base_plan = self._evaluate_hierarchical_base_plan(per_tf, tick, symbol=symbol)
            self._log_event({
                "event": "hierarchical_base_primary_decision",
                "symbol": symbol,
                "base_plan": base_plan,
                "open_positions": len(open_positions),
                "execution_enabled": False,
            })
            if open_positions:
                # Cancel any orphaned entry order before managing an existing position.
                order_state = self._reconcile_base_pending_order(
                    symbol, {"status": "WAIT", "reason": "Position already open; no additional entry."},
                    tick, account, symbol_info,
                )
                if order_state.get("status") == "BLOCKED":
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Pending-order state could not be reconciled; refusing to close/reverse while an orphan entry may still be working.",
                            "pending_order_state": order_state, "base_plan": base_plan, "execution_enabled": False}
                position = open_positions[0]
                position_magic = int(self._field(position, "magic", 0) or 0)
                position_comment = str(self._field(position, "comment", "") or "")
                owned = position_magic == 100001 and position_comment.startswith("YarBase")
                if not owned:
                    return {"status": "MANUAL_POSITION_UNMANAGED", "symbol": symbol,
                            "reason": "Open position is not identified as a YarTrader Base position; it will not be modified or closed.",
                            "pending_order_state": order_state, "base_plan": base_plan, "execution_enabled": False}
                pos_type = int(self._field(position, "type", -1))
                buy_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_BUY", 0))
                sell_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_SELL", 1))
                held_direction = "BUY" if pos_type == buy_type else ("SELL" if pos_type == sell_type else "UNKNOWN")
                structure = base_plan.get("structure") or {}
                child_direction = int(structure.get("child_direction", 0) or 0)
                zone_low = float(structure.get("child_zone_low") or 0.0)
                zone_high = float(structure.get("child_zone_high") or 0.0)
                market_price = float(tick.get("bid") if held_direction == "BUY" else tick.get("ask"))
                structural_invalidation = (
                    held_direction == "BUY" and child_direction < 0 and zone_low > 0 and market_price < zone_low
                ) or (
                    held_direction == "SELL" and child_direction > 0 and zone_high > 0 and market_price > zone_high
                )
                proposal_direction = str((base_plan.get("order_plan") or {}).get("direction", "")).upper()
                qualified_opposite = (
                    base_plan.get("status") == "ORDER_PROPOSAL"
                    and proposal_direction in ("BUY", "SELL") and proposal_direction != held_direction
                )
                if structural_invalidation or qualified_opposite:
                    ticket = int(self._field(position, "ticket", 0) or 0)
                    volume = float(self._field(position, "volume", 0.0) or 0.0)
                    if ticket <= 0 or volume <= 0:
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Owned Base position lacks a valid ticket or volume; cannot close safely.",
                                "base_plan": base_plan, "execution_enabled": False}
                    close_response = self.adapter.send_order_to_broker(OrderRequest(
                        Symbol=symbol, OrderType="CLOSE", Volume=volume, PositionTicket=ticket,
                        Comment="YarBaseExit", Magic=100001,
                    ))
                    self._log_event({"event": "base_position_exit", "symbol": symbol, "ticket": ticket,
                                     "held_direction": held_direction,
                                     "exit_reason": "STRUCTURAL_BASE_INVALIDATION" if structural_invalidation else "QUALIFIED_OPPOSITE_BASE_REACTION",
                                     "broker_status": close_response.Status, "retcode": close_response.Retcode})
                    success_codes = {0, 10009, int(getattr(self.adapter._mt5, "TRADE_RETCODE_DONE", 10009))}
                    if close_response.Status not in ("Placed", "Executed") or int(close_response.Retcode) not in success_codes:
                        return {"status": "EXIT_FAILED", "symbol": symbol, "reason": close_response.Comment,
                                "base_plan": base_plan, "execution_enabled": False}
                    return {"status": "POSITION_CLOSED_BASE_EXIT", "symbol": symbol,
                            "reason": "Base invalidation or a separately qualified opposite Base reaction closed the existing position; a new entry requires a later cycle.",
                            "base_plan": base_plan, "close_response": close_response.__dict__,
                            "execution_enabled": True}
                return {
                    "status": "POSITION_HELD_BASE_STRUCTURE", "symbol": symbol,
                    "reason": "No confirmed Base invalidation or qualified opposite reaction; retain the existing broker SL/TP.",
                    "pending_order_state": order_state, "base_plan": base_plan, "execution_enabled": False,
                }
            order_state = self._reconcile_base_pending_order(symbol, base_plan, tick, account, symbol_info)
            return {
                "status": order_state.get("status", "WAIT"), "symbol": symbol,
                "reason": order_state.get("reason") or base_plan.get("reason") or "No validated hierarchical Base setup.",
                "base_plan": base_plan, "pending_order_state": order_state,
                "execution_enabled": order_state.get("status") in ("PENDING_PLACED", "ALREADY_PENDING"),
            }
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
