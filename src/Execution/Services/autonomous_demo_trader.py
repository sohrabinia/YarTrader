"""Autonomous, DEMO-only MT5 strategy-to-execution loop.

This worker never sends LIVE orders. It only submits a DEMO order when fresh
broker data produces a qualified strategy candidate and all safety gates pass.
"""
from __future__ import annotations

import hashlib
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
from src.Execution.Services.market_session_engine import MarketSessionEngine
from src.Execution.Safety.demo_exploration_policy import demo_exploration_autonomy_enabled
from src.Infrastructure.exceptions import ValidationException
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, ProductionRiskPolicy
from src.Application.Deployment.sqlite_event_store import SQLiteEventStore

logger = logging.getLogger("AutonomousDemoTrader")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_START_LOCK = threading.Lock()
_WORKER: Optional[threading.Thread] = None


def _demo_config_value(name: str, default: str) -> str:
    """Resolve DEMO settings consistently with the execution gate."""
    value = os.environ.get(name)
    if value is not None:
        return value
    for filename in (".env.production", ".env"):
        try:
            for line in (_PROJECT_ROOT / filename).read_text(encoding="utf-8-sig").splitlines():
                stripped = line.strip()
                if stripped.startswith(name + "="):
                    return stripped.split("=", 1)[1].strip().strip("\"'")
        except OSError:
            continue
    return default


def _demo_exploration_enabled() -> bool:
    """Exploration is opt-in and can only run when autonomous execution is DEMO-only."""
    enabled = _demo_config_value("YARTRADER_DEMO_EXPLORATION_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    autonomous = _demo_config_value("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    mode = _demo_config_value("YARTRADER_TRADING_MODE", "DEMO").strip().upper()
    live_enabled = _demo_config_value("LIVE_TRADING_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    return enabled and autonomous and mode == "DEMO" and not live_enabled


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


def _pending_order_matches_current_plan(
    order: Any, expected_type: int, entry: float, stop: float, target: float,
    point: float, spread: float = 0.0, direction: str = "BUY",
) -> tuple[bool, float, float, float]:
    """Compare an active pending order with the current plan using price-aware tolerances.

    A fraction of one broker point was too strict and could trigger cancel/re-submit
    churn from harmless quote/rounding noise. Material structural changes still
    require a separately risk-validated replacement.
    """
    def value(name: str, default: Any = None) -> Any:
        return order.get(name, default) if isinstance(order, dict) else getattr(order, name, default)
    entry_tolerance = max(float(point) * 10.0, max(0.0, float(spread)) * 3.0, abs(float(entry)) * 0.0001)
    risk_distance = abs(float(entry) - float(stop))
    tight_stop_tolerance = max(float(point) * 3.0, abs(float(stop)) * 0.00002)
    direction_upper = str(direction or "").strip().upper()
    try:
        order_sl_for_tolerance = float(value("sl", 0.0) or 0.0)
        existing_stop_is_safer = (
            direction_upper == "BUY" and order_sl_for_tolerance >= float(stop)
        ) or (
            direction_upper == "SELL" and order_sl_for_tolerance <= float(stop)
        )
    except (TypeError, ValueError, OverflowError):
        existing_stop_is_safer = False
    protection_tolerance = (
        max(tight_stop_tolerance, float(point) * 10.0, max(0.0, float(spread)) * 3.0,
            abs(float(stop)) * 0.0001, risk_distance * 0.05)
        if existing_stop_is_safer else tight_stop_tolerance
    )
    try:
        order_entry_for_tolerance = float(value("price_open", 0.0) or 0.0)
        order_tp_for_tolerance = float(value("tp", 0.0) or 0.0)
        existing_target_valid = (
            direction_upper == "BUY" and order_tp_for_tolerance > order_entry_for_tolerance
        ) or (
            direction_upper == "SELL" and 0.0 < order_tp_for_tolerance < order_entry_for_tolerance
        )
    except (TypeError, ValueError, OverflowError):
        existing_target_valid = False
    target_tolerance = (
        max(float(point) * 10.0, max(0.0, float(spread)) * 3.0,
            abs(float(target)) * 0.0001, risk_distance)
        if existing_target_valid else tight_stop_tolerance
    )
    try:
        order_entry = float(value("price_open", 0.0) or 0.0)
        order_sl = float(value("sl", 0.0) or 0.0)
        order_tp = float(value("tp", 0.0) or 0.0)
        order_type = int(value("type", -1) if value("type", -1) is not None else -1)
        matches = (
            order_type == int(expected_type) and order_entry > 0.0 and order_sl > 0.0 and order_tp > 0.0
            and abs(order_entry - float(entry)) <= entry_tolerance
            and abs(order_sl - float(stop)) <= protection_tolerance
            and abs(order_tp - float(target)) <= target_tolerance
        )
        return matches, entry_tolerance, protection_tolerance, target_tolerance
    except (TypeError, ValueError, OverflowError):
        return False, entry_tolerance, protection_tolerance, target_tolerance


def _strategy_broker_comment(strategy_name: str) -> str:
    """Return a stable unique MT5 comment that survives broker sanitization/truncation."""
    name = str(strategy_name or "BASE_HIERARCHY").strip().upper()
    readable = {
        "BASE_HIERARCHY": "YarBase",
        "NONE": "YarBase",
        "RTM": "YarBaseRTM",
        "TREND": "YarBaseTREND",
        "RANGE": "YarBaseRANGE",
        "BASE_ENGULF_REVERSAL": "YarBaseENGULF",
        "PRICE_ACTION": "YarBasePRICE",
        "BREAKOUT": "YarBaseBRKOUT",
        "MEAN_REVERSION": "YarBaseMEANREV",
        "MOMENTUM": "YarBaseMOMENT",
    }
    if name in readable:
        return readable[name]
    slug = "".join(ch for ch in name if ch.isalnum())
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:4].upper()
    return ("YarBase" + (slug[:4] or "STR") + digest)[:15]


def _legacy_strategy_comment_matches(comment: str, strategy_name: str) -> bool:
    """Recognize broker-truncated comments written by older YarTrader versions."""
    value = str(comment or "").strip().upper()
    name = str(strategy_name or "").strip().upper()
    if name == "BASE_ENGULF_REVERSAL":
        return value.startswith("YARBASEBASE_ENG")
    if name == "PRICE_ACTION":
        return value.startswith("YARBASEPRICE")
    return False


def _acquire_symbol_execution_lock(symbol: str) -> tuple[Optional[int], Path]:
    """Acquire an atomic cross-process DEMO order-submission lock per symbol."""
    lock_dir = _PROJECT_ROOT / "runtime_logs" / "base_behavior_runtime" / "execution_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{str(symbol).strip().upper()}.lock"
    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()} timestamp={time.time():.3f}".encode("ascii"))
            return fd, lock_path
        except FileExistsError:
            try:
                # A worker killed mid-submit may leave a stale lock; normal order
                # reconciliation should never take remotely close to this long.
                if time.time() - lock_path.stat().st_mtime > 120.0:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            return None, lock_path
        except OSError:
            return None, lock_path
    return None, lock_path


def calculate_demo_volume_by_risk(
    mt5: Any, symbol: str, direction: str, entry: float, stop_loss: float,
    symbol_info: Dict[str, Any], balance: float, equity: float, risk_pct: float = ProductionRiskPolicy.TARGET_RISK_PCT,
    allow_portfolio_allocation: bool = False,
) -> Dict[str, Any]:
    """Size DEMO orders using MT5's authoritative stop-loss PnL calculation."""
    values = (entry, stop_loss, balance, equity, risk_pct)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in values):
        raise ValidationException("Risk sizing received invalid numeric inputs.")
    target_risk_pct = float(ProductionRiskPolicy.TARGET_RISK_PCT)
    min_risk_pct = float(ProductionRiskPolicy.MIN_ADAPTIVE_RISK_PCT)
    max_risk_pct = float(ProductionRiskPolicy.HARD_CEILING_RISK_PCT)
    lower_risk_invalid = (risk_pct <= 0 or (risk_pct < min_risk_pct and not allow_portfolio_allocation))
    if (min(float(entry), float(stop_loss), float(balance), float(equity)) <= 0
            or lower_risk_invalid or risk_pct > max_risk_pct):
        raise ValidationException(
            f"Adaptive risk must be positive and no greater than the legacy {max_risk_pct:.2f}% calculation ceiling; "
            f"minimum is {min_risk_pct:.2f}% unless equal-share portfolio allocation is explicit. "
            "The MT5 adapter independently enforces the global 1% execution ceiling."
        )
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
        "W1": "TIMEFRAME_W1",
        "MN1": "TIMEFRAME_MN1",
    }
    MIN_CONFIDENCE = 70.0
    MIN_RR = ProductionRiskPolicy.MINIMUM_RR
    RISK_PER_TRADE_PCT = ProductionRiskPolicy.TARGET_RISK_PCT
    MAX_ENTRY_DRIFT_R = 0.35
    MAX_TICK_BAR_GAP_SECONDS = 300
    MAX_STOP_ATR_MULTIPLE = 3.0
    ESTIMATED_COMMISSION_PER_LOT_USD = 7.0

    def __init__(self, adapter: Optional[RealMT5BrokerAdapter] = None) -> None:
        self.adapter = adapter or RealMT5BrokerAdapter(auto_initialize=True)
        self._last_attempt: Dict[str, str] = {}
        self._last_report: Dict[str, Any] = {}
        self._last_learning_sync_epoch = 0

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
                exploration_mode=_demo_exploration_enabled(),
            )
            # Preserve the planner's actual TP target all the way to broker execution.
            # It must not be downgraded into a diagnostic-only reward estimate.
            plan = dict(report.get("base_plan") or {})
            hierarchy = dict(report.get("hierarchy") or {})
            reaction = dict(report.get("reaction_analysis") or {})
            candidate = report.get("best_candidate")
            hierarchy_structure = hierarchy.get("structure") or {}
            # Fail closed: DEMO exploration is still multi-timeframe Base trading.
            # Never let a reaction-only fallback bypass a missing parent or M1 chain.
            complete_hierarchy = bool(
                hierarchy_structure.get("hierarchy_complete_to_m1")
                and hierarchy_structure.get("parent_base_id")
                and hierarchy_structure.get("child_base_id")
                and hierarchy_structure.get("micro_base_id")
            )
            base_qualified = bool(
                complete_hierarchy
                and candidate
                and str(candidate.get("strategy_name", "")).upper() == "BASE_HIERARCHY"
                and str(candidate.get("direction", "")).upper() in ("BUY", "SELL")
                and str(plan.get("status", "")).upper() == "PROPOSED"
                and (
                    str(report.get("model_status", "")).upper() == "COSTED_REACTION_MODEL_LOADED"
                    or _demo_exploration_enabled()
                )
            )
            # Evaluate independent RTM and pure Price Action candidates on the same
            # closed MN1->M1 candle set. In autonomous DEMO/backtest, a qualified
            # strategy may act on its own; do not require a cross-strategy selector.
            strategy_results: Dict[str, Any] = {
                "BASE_HIERARCHY": {
                    "strategy_name": "BASE_HIERARCHY",
                    "status": "ENTRY_PROPOSAL" if base_qualified else "WAIT",
                    "direction": str(plan.get("direction", "WAIT")).upper() if base_qualified else "WAIT",
                    "confidence": float((candidate or {}).get("confidence", 0.0) or 0.0),
                    "order_plan": plan if base_qualified else None,
                    "reason": (candidate or {}).get("reasoning", [plan.get("reason", "")])[0]
                    if base_qualified else (plan.get("reason") or "Base hierarchy/model gate not satisfied."),
                    "timeframe_analysis": {},
                }
            }
            try:
                from src.Intelligence.Execution.multi_timeframe_style_analyzer import MultiTimeframeStyleAnalyzer
                styles = MultiTimeframeStyleAnalyzer().evaluate(
                    symbol=symbol,
                    timeframe_candles=per_tf,
                    quote={"bid": float(tick.get("bid", 0.0)), "ask": float(tick.get("ask", 0.0))},
                    now=float(tick.get("time") or time.time()),
                    spread_allowance=max(0.0, float(tick.get("ask", 0.0))-float(tick.get("bid", 0.0))),
                )
                strategy_results.update(styles)
                from src.Intelligence.Execution.market_behavior_strategy import evaluate_market_behavior_strategy
                market_behavior_result = evaluate_market_behavior_strategy(
                    symbol=symbol, timeframe_candles=per_tf,
                    quote={"bid": float(tick.get("bid", 0.0)), "ask": float(tick.get("ask", 0.0))},
                    now=float(tick.get("time") or time.time()),
                    spread_allowance=max(0.0, float(tick.get("ask", 0.0))-float(tick.get("bid", 0.0))),
                )
                strategy_results[str(market_behavior_result.get("strategy_name") or "MARKET_BEHAVIOR").upper()] = market_behavior_result
            except Exception as style_exc:
                logger.exception("RTM/Price Action analysis failed closed: %s", style_exc)
                strategy_results["RTM"] = {"strategy_name": "RTM", "status": "WAIT", "direction": "WAIT",
                                             "confidence": 0.0, "order_plan": None, "reason": "RTM analysis failed closed."}
                strategy_results["PRICE_ACTION"] = {"strategy_name": "PRICE_ACTION", "status": "WAIT", "direction": "WAIT",
                                                     "confidence": 0.0, "order_plan": None, "reason": "Price Action analysis failed closed."}
                strategy_results["MARKET_BEHAVIOR"] = {"strategy_name": "MARKET_BEHAVIOR", "status": "WAIT", "direction": "WAIT",
                                                        "confidence": 0.0, "order_plan": None, "reason": "Market-behavior analysis failed closed."}

            # Keep each candidate independent. The selected plan is a compatibility
            # view for single-slot mode; multi-strategy DEMO mode consumes all qualified
            # proposals below and assigns one broker slot per strategy name.
            proposals = []
            for strategy_name, result in strategy_results.items():
                order_plan = result.get("order_plan")
                if (result.get("status") == "ENTRY_PROPOSAL"
                        and isinstance(order_plan, dict)
                        and str(order_plan.get("status", "")).upper() == "PROPOSED"
                        and str(result.get("direction", "")).upper() in ("BUY", "SELL")):
                    proposals.append((strategy_name, result, order_plan))
            selected = proposals[0] if proposals else None
            selected_name = selected[0] if selected else "NONE"
            selected_result = selected[1] if selected else {}
            selected_plan = selected[2] if selected else {
                "status": "WAIT",
                "reason": "No strategy produced a fully qualified multi-timeframe proposal."}
            return {
                "status": "ORDER_PROPOSAL" if selected else "WAIT",
                "reason": (selected_result.get("reason") if selected else selected_plan["reason"]),
                "structure": hierarchy.get("structure") or {},
                "hierarchy": hierarchy,
                "reaction_analysis": reaction,
                "model_status": report.get("model_status", "UNKNOWN"),
                "base_plan": plan,
                "order_plan": selected_plan,
                "decision_authority": selected_name,
                "selected_strategy": selected_name,
                "strategy_results": strategy_results,
                "strategy_proposals_count": len(proposals),
                "execution_enabled": False,
                "execution_mode": "INDEPENDENT_STRATEGIES_SHARED_RISK_GATE",
            }
        except Exception as exc:
            logger.exception("Canonical Base-only DEMO analysis failed closed: %s", exc)
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

    def _dedupe_owned_pending_orders(
        self, symbol: str, active_orders: Optional[List[Any]], symbol_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Cancel exact duplicate YarTrader-owned pending orders and verify broker state.

        Orders with different price, stop, target, volume, side, or strategy comment
        remain independent. Unknown broker state fails closed; manual orders are untouched.
        """
        if active_orders is None:
            return {"ok": False, "orders": None, "reason": "Broker pending-order state is unknown; duplicate reconciliation cannot proceed."}
        try:
            digits = int(symbol_info["digits"])
            if digits < 0 or digits > 10:
                raise ValueError("invalid price precision")
        except (KeyError, TypeError, ValueError, OverflowError):
            return {"ok": False, "orders": None, "reason": "Broker price precision is unavailable for duplicate-order reconciliation."}
        seen: Dict[tuple, Any] = {}
        cancelled = []
        for order in active_orders:
            comment = str(self._field(order, "comment", "") or "")
            try:
                magic = int(self._field(order, "magic", 0) or 0)
                ticket = int(self._field(order, "ticket", 0) or 0)
                order_type = int(self._field(order, "type", -1))
                entry = float(self._field(order, "price_open", 0.0) or 0.0)
                stop = float(self._field(order, "sl", 0.0) or 0.0)
                target = float(self._field(order, "tp", 0.0) or 0.0)
                volume = float(self._field(order, "volume_current", self._field(order, "volume_initial", 0.0)) or 0.0)
            except (TypeError, ValueError, OverflowError):
                continue
            if magic != 100001 or not comment.startswith("YarBase"):
                continue
            if ticket <= 0 or min(entry, volume) <= 0 or min(stop, target) < 0:
                continue
            signature = (comment, order_type, round(entry, digits), round(stop, digits),
                         round(target, digits), round(volume, 8))
            keeper = seen.get(signature)
            if keeper is None:
                seen[signature] = order
                continue
            keeper_ticket = int(self._field(keeper, "ticket", 0) or 0)
            response = self.adapter.cancel_pending_order(ticket)
            status = str(getattr(response, "Status", ""))
            event = {
                "event": "duplicate_pending_order_reconciled", "symbol": symbol,
                "strategy": comment.split(":", 1)[1] if ":" in comment else comment,
                "duplicate_ticket": ticket, "kept_ticket": keeper_ticket,
                "order_type": order_type, "entry": entry, "stop_loss": stop,
                "take_profit": target, "volume": volume,
                "broker_status": status, "broker_retcode": getattr(response, "Retcode", None),
                "broker_confirmed": status == "Cancelled",
                "reason": "Exact duplicate of a YarTrader-owned pending order; retaining one copy to avoid duplicate exposure.",
            }
            self._log_event(event)
            if status != "Cancelled":
                return {"ok": False, "orders": None,
                        "reason": f"Could not cancel duplicate YarTrader pending order {ticket}; broker state must be reconciled before any new entry."}
            cancelled.append(ticket)
        if cancelled:
            refreshed = self.adapter.get_active_orders(symbol=symbol)
            if refreshed is None:
                return {"ok": False, "orders": None,
                        "reason": "Duplicate cancellation was requested but refreshed broker order state is unknown."}
            return {"ok": True, "orders": refreshed, "cancelled_tickets": cancelled}
        return {"ok": True, "orders": active_orders, "cancelled_tickets": []}

    @staticmethod
    def _base_behavior_is_primary() -> bool:
        """Hard-lock the autonomous trader to the single Base-behavior strategy.

        Legacy orchestrated strategies are intentionally not selectable from an
        environment override. They remain in the codebase for research/backward
        compatibility, but cannot be used by this autonomous execution worker.
        """
        return False

    def _candidate_structural_trailing_stop(
        self, position: Any, candles: List[Dict[str, Any]], tick: Dict[str, Any],
        symbol_info: Dict[str, Any],
    ) -> Optional[float]:
        """Use the latest confirmed M5 swing to protect earned profit without a fixed TP.

        Only closed candles are passed in. A candidate must be beyond entry, tighter
        than the existing SL, and safely on the protective side of the current quote.
        """
        if len(candles) < 4:
            return None
        mt5 = self.adapter._mt5
        buy_type = int(getattr(mt5, "POSITION_TYPE_BUY", 0))
        sell_type = int(getattr(mt5, "POSITION_TYPE_SELL", 1))
        position_type = int(self._field(position, "type", -1))
        entry = float(self._field(position, "price_open", 0.0) or 0.0)
        old_sl = float(self._field(position, "sl", 0.0) or 0.0)
        if entry <= 0 or old_sl <= 0 or position_type not in (buy_type, sell_type):
            return None
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", 0.0) or 0.0)
        point = float(symbol_info.get("point", 0.0) or 0.0)
        if bid <= 0 or ask < bid or point <= 0:
            return None
        # Do not trail a losing/flat position into an arbitrary stop. Structure must
        # have advanced far enough that the new stop locks a positive result.
        if position_type == buy_type and bid <= entry:
            return None
        if position_type == sell_type and ask >= entry:
            return None
        opened_msc = int(self._field(position, "time_msc", 0) or 0)
        opened_at = opened_msc // 1000 if opened_msc > 0 else int(self._field(position, "time", 0) or 0)
        spread = max(0.0, ask - bid)
        buffer = max(2.0 * spread, 2.0 * point)
        min_distance = max(float(symbol_info.get("trade_stops_level", 0.0) or 0.0) * point, point)
        # The right-hand candle confirms each swing; the forming candle is never used.
        first = max(1, len(candles) - 32)
        for i in range(len(candles) - 2, first - 1, -1):
            candle = candles[i]
            if int(candle.get("timestamp", 0) or 0) <= opened_at:
                continue
            previous, following = candles[i - 1], candles[i + 1]
            if position_type == buy_type:
                pivot = float(candle["low"])
                if not (pivot < float(previous["low"]) and pivot <= float(following["low"])):
                    continue
                candidate = pivot - buffer
                if candidate <= entry or candidate <= old_sl + point * 0.5:
                    continue
                if candidate >= bid - min_distance:
                    continue
                return candidate
            else:
                pivot = float(candle["high"])
                if not (pivot > float(previous["high"]) and pivot >= float(following["high"])):
                    continue
                candidate = pivot + buffer
                if candidate >= entry or candidate >= old_sl - point * 0.5:
                    continue
                if candidate <= ask + min_distance:
                    continue
                return candidate
        return None

    def _log_event(self, event: Dict[str, Any]) -> None:
        # Append-only forensic journal: each decision/order/management/close event
        # gets UTC calendar/session metadata and is written independently of snapshots.
        now = datetime.now(timezone.utc)
        event = dict(event)
        event.setdefault("event", "journal_event_unclassified")
        event.setdefault("symbol", "UNKNOWN")
        event.setdefault("timestamp_utc", now.isoformat())
        event.setdefault("trade_type", "DEMO")
        event.setdefault("strategy_style", event.get("selected_strategy") or event.get("strategy") or "BASE_HIERARCHY")
        event_name = str(event.get("event", ""))
        review_decision = str(event.get("review_decision", ""))
        event_status = str(event.get("status", "")).upper()
        compact_context = (
            event_name == "pending_order_review_cycle"
            or (
                event_name == "hierarchical_base_primary_decision"
                and isinstance(event.get("base_plan_summary"), dict)
                and str(event["base_plan_summary"].get("status", "")).upper()
                not in {"ORDER_PROPOSAL", "ENTRY_PROPOSAL"}
            )
            or (event_name == "pending_order_review" and review_decision in {
                "KEEP_EXISTING", "KEEP_EXISTING_WITHIN_RISK_BUDGET",
                "KEEP_UNTIL_EXPIRY_NO_QUALIFIED_REPLACEMENT",
                "KEEP_EXISTING_RISK_BLOCKED_REPLACEMENT",
            })
            or (event_name == "entry_execution_outcome" and event_status in {"WAIT", "PENDING_ORDER_ACTIVE"})
        )
        base_plan = event.get("base_plan") if isinstance(event.get("base_plan"), dict) else {}
        hierarchy = base_plan.get("hierarchy") if isinstance(base_plan.get("hierarchy"), dict) else {}
        structure = (
            event.get("hierarchy_structure") if isinstance(event.get("hierarchy_structure"), dict)
            else event.get("structure") if isinstance(event.get("structure"), dict)
            else base_plan.get("structure") if isinstance(base_plan.get("structure"), dict)
            else hierarchy.get("structure") if isinstance(hierarchy.get("structure"), dict)
            else {}
        )
        historical_structure = (
            event.get("historical_structure_analysis")
            if isinstance(event.get("historical_structure_analysis"), dict)
            else base_plan.get("historical_structure_analysis")
            if isinstance(base_plan.get("historical_structure_analysis"), dict)
            else hierarchy.get("historical_structure_analysis")
            if isinstance(hierarchy.get("historical_structure_analysis"), dict)
            else {}
        )
        cache = getattr(self, "_journal_structure_context_by_symbol", {})
        symbol_key = str(event.get("symbol", "UNKNOWN")).upper()
        inherited = cache.get(symbol_key, {})
        # Frequent keep/review outcomes reference the last full structural snapshot
        # instead of duplicating every timeframe/level in every 30-second cycle.
        # Full structure remains attached to primary decisions and actual order events.
        if compact_context:
            if not historical_structure or historical_structure.get("status") != "OK":
                historical_structure = inherited.get("analysis", {}) if inherited else {}
            event.pop("base_plan", None)
            event.pop("historical_structure_analysis", None)
            event.pop("structural_levels", None)
            event.pop("structural_hierarchy", None)
            event.pop("level_reaction_evidence", None)
            event.pop("structure", None)
            event.setdefault("structure_context_inherited", bool(inherited))
            event.setdefault("structure_context_source_timestamp_utc", inherited.get("timestamp_utc"))
        else:
            # Carry the latest observed structure context through important order,
            # position and close events so the lifecycle journal can be joined later.
            if not historical_structure or historical_structure.get("status") != "OK":
                if inherited:
                    historical_structure = inherited.get("analysis", {})
                    event.setdefault("structure_context_inherited", True)
                    event.setdefault("structure_context_source_timestamp_utc", inherited.get("timestamp_utc"))
            else:
                cache[symbol_key] = {"analysis": historical_structure, "timestamp_utc": event.get("timestamp_utc")}
                self._journal_structure_context_by_symbol = cache
                event.setdefault("structure_context_inherited", False)
        tf_research = historical_structure.get("timeframes", {}) if isinstance(historical_structure, dict) else {}
        flattened_levels = []
        reaction_summary_by_tf = {}
        for tf_name, tf_data in tf_research.items():
            if not isinstance(tf_data, dict):
                continue
            reaction_summary_by_tf[tf_name] = tf_data.get("reaction_summary", {})
            for level in tf_data.get("levels", []) or []:
                if isinstance(level, dict):
                    flattened_levels.append({"source_timeframe": tf_name, **level})
        event.setdefault("journal_schema_version", 2)
        event.setdefault("structure_research_schema_version", 1)
        event.setdefault("structural_research_status", historical_structure.get("status", "NOT_ATTACHED"))
        if compact_context:
            event.setdefault("structural_level_count", len(flattened_levels))
            event.setdefault("level_reaction_evidence_summary", {
                tf_name: {key: summary.get(key) for key in ("touches", "rejections", "breakouts", "visits") if key in summary}
                for tf_name, summary in reaction_summary_by_tf.items() if isinstance(summary, dict)
            })
            event.setdefault("entry_level_context", historical_structure.get("current_price_context", {}))
            event.setdefault("structural_hierarchy_summary", {
                key: structure.get(key) for key in (
                    "parent_base_id", "child_base_id", "parent_timeframe", "child_timeframe",
                    "selected_child_timeframe", "micro_timeframe", "direction", "zone_low", "zone_high",
                ) if key in structure
            })
        else:
            event.setdefault("historical_structure_analysis", historical_structure)
            event.setdefault("structural_levels", flattened_levels)
            event.setdefault("structural_hierarchy", structure)
            event.setdefault("level_reaction_evidence", reaction_summary_by_tf)
            event.setdefault("entry_level_context", historical_structure.get("current_price_context", {}))
        # This remains empty until an observed outcome is available; never fabricate a
        # breakout/rejection label from a planned order or an unconfirmed touch.
        event.setdefault("breakout_rejection_outcome", event.get("level_outcome") or {})
        event.setdefault(
            "decision_timeframe",
            event.get("primary_timeframe") or ("MULTI_TIMEFRAME" if structure else event.get("timeframe") or "UNKNOWN")
        )
        event.setdefault("setup_timeframe", event.get("setup_tf") or structure.get("child_timeframe") or "UNKNOWN")
        event.setdefault(
            "entry_timeframe",
            event.get("trigger_timeframe") or structure.get("micro_timeframe") or "UNKNOWN"
        )
        event.setdefault(
            "execution_timeframe",
            event.get("execution_tf") or structure.get("micro_timeframe") or "UNKNOWN"
        )
        event.setdefault(
            "context_timeframes",
            structure.get("hierarchy_timeframes_considered") or event.get("timeframes_used") or []
        )
        event.setdefault("weekday_utc", now.strftime("%A"))
        event.setdefault("day_of_month", now.day)
        event.setdefault("month", now.month)
        event.setdefault("year", now.year)
        minute = now.hour * 60 + now.minute
        event.setdefault("session_utc", (
            "ASIA" if minute < 7 * 60 else
            "LONDON" if minute < 12 * 60 else
            "NEW_YORK_OVERLAP" if minute < 16 * 60 else
            "NEW_YORK" if minute < 21 * 60 else "LATE_US_OR_ROLLOVER"
        ))
        # Entry calendar metadata must follow broker-confirmed entry time, not close/review time.
        entry_timestamp = event.get("opened_at_utc") or event.get("entry_time_utc") or event.get("open_time")
        if entry_timestamp:
            try:
                entry_dt = datetime.fromisoformat(str(entry_timestamp).replace("Z", "+00:00"))
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                entry_dt = entry_dt.astimezone(timezone.utc)
                event.setdefault("entry_time_utc", entry_dt.isoformat())
                event.setdefault("entry_weekday", entry_dt.strftime("%A"))
                event.setdefault("entry_day_of_month", entry_dt.day)
                event.setdefault("entry_month", entry_dt.month)
                event.setdefault("entry_year", entry_dt.year)
                entry_minute = entry_dt.hour * 60 + entry_dt.minute
                event.setdefault("entry_session_utc", (
                    "ASIA" if entry_minute < 420 else "LONDON" if entry_minute < 720 else
                    "NEW_YORK_OVERLAP" if entry_minute < 960 else
                    "NEW_YORK" if entry_minute < 1260 else "LATE_US_OR_ROLLOVER"
                ))
            except (TypeError, ValueError, OverflowError):
                event.setdefault("entry_calendar_metadata_status", "INVALID_ENTRY_TIMESTAMP")
        # Tests use mock adapters; never let test fixtures contaminate real runtime journals.
        if (getattr(self, "adapter", None) is not None
                and type(self.adapter) is not RealMT5BrokerAdapter
                and _PROJECT_ROOT == Path(__file__).resolve().parents[3]):
            logger.info("Autonomous DEMO trader test event (not persisted to production logs): %s", event)
            return
        try:
            folder = _PROJECT_ROOT / "runtime_logs"
            folder.mkdir(parents=True, exist_ok=True)
            # The real runtime writes each event once to the canonical SQLite ledger.
            # Test fixtures retain their JSONL compatibility outputs in isolated temp roots.
            is_real_runtime = (
                type(getattr(self, "adapter", None)) is RealMT5BrokerAdapter
                and _PROJECT_ROOT == Path(__file__).resolve().parents[3]
            )
            if is_real_runtime:
                SQLiteEventStore(folder / "yartrader_events.sqlite3").append_event(
                    event, source="autonomous_demo_trader"
                )
            else:
                payload = json.dumps(event, ensure_ascii=False, default=str, sort_keys=True) + "\n"
                runtime_event = dict(event)
                for large_key in (
                    "base_plan", "plan", "base_analysis", "hierarchy_structure", "structure",
                    "historical_structure_analysis", "structural_levels", "structural_hierarchy",
                    "level_reaction_evidence", "entry_level_context", "breakout_rejection_outcome",
                ):
                    runtime_event.pop(large_key, None)
                runtime_event["runtime_log_payload"] = (
                    "COMPACT; canonical event and available structure context are stored in "
                    "yartrader_events.sqlite3"
                )
                runtime_payload = json.dumps(runtime_event, ensure_ascii=False, default=str, sort_keys=True) + "\n"
                for filename, line in (
                    ("autonomous_demo_trader.jsonl", runtime_payload),
                    ("trade_journal_events_v2.jsonl", payload),
                ):
                    with (folder / filename).open("a", encoding="utf-8") as handle:
                        handle.write(line)
                        handle.flush()
                        os.fsync(handle.fileno())
        except Exception as exc:
            # An event that cannot be durably journaled must not be treated as safely processed.
            logger.exception("Unable to persist autonomous DEMO trader event/journal")
            raise RuntimeError("Autonomous DEMO event persistence failed; stopping this cycle safely.") from exc
        logger.info("Autonomous DEMO trader: %s", event)

    def _trade_review_file(self) -> Path:
        return _PROJECT_ROOT / "runtime_logs" / "autonomous_trade_review_state.json"

    def _load_trade_review_state(self) -> Dict[str, Any]:
        path = self._trade_review_file()
        # Unit tests use mock adapters; never let them consume production review state.
        if type(self.adapter) is not RealMT5BrokerAdapter and _PROJECT_ROOT == Path(__file__).resolve().parents[3]:
            payload = {}
        else:
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError, TypeError) as exc:
                    # Never silently replace a damaged/unreadable state file with an
                    # empty state: that can erase pending post-close evidence and the
                    # idempotency ledger, causing duplicate processing on the next cycle.
                    raise RuntimeError(f"Trade review state could not be loaded safely: {path}") from exc
            else:
                payload = {}
        if not isinstance(payload, dict):
            raise RuntimeError(f"Trade review state has an invalid root object: {path}")
        payload.setdefault("open_positions", {})
        payload.setdefault("last_closed_setup_by_symbol", {})
        payload.setdefault("last_submitted_setup_by_symbol", {})
        payload.setdefault("processed_position_ids", {})
        payload.setdefault("ignored_untracked_position_ids", {})
        payload.setdefault("post_close_followups", {})
        payload.setdefault("post_close_followups_completed", {})
        return payload

    def _update_post_close_followups(self, state: Dict[str, Any], symbol: str, now: datetime) -> None:
        """Persist the first five fully closed M1 bars after each broker-confirmed exit.

        This is post-trade outcome evidence only; it must never feed the entry decision
        or be merged into pre-trade features. Pending items live in the atomic review
        state so a restart does not lose the follow-up window.
        """
        pending = state.setdefault("post_close_followups", {})
        completed = state.setdefault("post_close_followups_completed", {})
        symbol_upper = str(symbol or "").upper()
        mt5 = self.adapter._mt5
        timeframe = getattr(mt5, "TIMEFRAME_M1", None)
        if timeframe is None:
            return
        now_epoch = int(now.timestamp())
        for key, item in list(pending.items()):
            if not isinstance(item, dict) or str(item.get("symbol", "")).upper() != symbol_upper:
                continue
            try:
                close_epoch = int(item["closed_at_epoch"])
                first_bar_epoch = ((close_epoch + 59) // 60) * 60
                # Wait until five complete one-minute bars could exist. Actual bars are
                # queried below, so weekend/session gaps do not get fabricated.
                if now_epoch < first_bar_epoch + 5 * 60:
                    continue
                rates = mt5.copy_rates_range(
                    symbol_upper, timeframe,
                    datetime.fromtimestamp(first_bar_epoch, timezone.utc),
                    now,
                )
                if rates is None:
                    continue
                rows = []
                for rate in rates:
                    bar_time = int(self._field(rate, "time", 0) or 0)
                    if bar_time < first_bar_epoch or bar_time + 60 > now_epoch:
                        continue
                    rows.append({
                        "time_utc": datetime.fromtimestamp(bar_time, timezone.utc).isoformat(),
                        "time_epoch": bar_time,
                        "open": float(self._field(rate, "open", 0.0)),
                        "high": float(self._field(rate, "high", 0.0)),
                        "low": float(self._field(rate, "low", 0.0)),
                        "close": float(self._field(rate, "close", 0.0)),
                        "tick_volume": int(self._field(rate, "tick_volume", 0) or 0),
                    })
                rows.sort(key=lambda row: row["time_epoch"])
                # Require five distinct M1 candles; missing bars are not synthesized.
                deduped = {row["time_epoch"]: row for row in rows}
                rows = [deduped[t] for t in sorted(deduped)][:5]
                if len(rows) < 5:
                    continue
                exit_price = float(item["exit_price"])
                sign = 1.0 if str(item.get("direction", "")).upper() == "BUY" else -1.0
                favorable = max(
                    max(sign * (bar["high"] - exit_price), sign * (bar["low"] - exit_price))
                    for bar in rows
                )
                adverse = max(
                    max(-sign * (bar["high"] - exit_price), -sign * (bar["low"] - exit_price))
                    for bar in rows
                )
                result = {
                    "event": "trade_post_close_m1_followup_completed",
                    "schema_version": 1,
                    "position_id": item.get("position_id"),
                    "symbol": symbol_upper,
                    "direction": item.get("direction"),
                    "exit_reason": item.get("exit_reason"),
                    "closed_at_utc": item.get("closed_at_utc"),
                    "closed_at_epoch": close_epoch,
                    "exit_price": exit_price,
                    "followup_window_start_utc": rows[0]["time_utc"],
                    "followup_window_end_utc": rows[-1]["time_utc"],
                    "requested_closed_m1_bars": 5,
                    "stored_closed_m1_bars": len(rows),
                    "bars": rows,
                    "post_close_max_favorable_price_move": round(max(0.0, favorable), 10),
                    "post_close_max_adverse_price_move": round(max(0.0, adverse), 10),
                    "close_after_five_m1_bars": rows[-1]["close"],
                    "signed_close_move_after_five_bars": round(sign * (rows[-1]["close"] - exit_price), 10),
                    "data_source": "MT5_CLOSED_M1_BARS",
                    "usage": "POST_TRADE_OUTCOME_ONLY_NOT_A_PRE_TRADE_FEATURE",
                    "recorded_at_utc": now.astimezone(timezone.utc).isoformat(),
                }
                # Persist the event before removing the pending item from state.
                # If event construction/logging raises, the pending item remains retryable.
                self._log_event(result)
                completed[str(key)] = result
                del pending[key]
            except Exception:
                # Broker API/data-shape failures must not discard this pending follow-up.
                logger.exception("Post-close M1 follow-up failed for position %s; keeping it pending", key)

    def _save_trade_review_state(self, state: Dict[str, Any]) -> None:
        # Test doubles must not mutate the real runtime journal.
        if type(self.adapter) is not RealMT5BrokerAdapter and _PROJECT_ROOT == Path(__file__).resolve().parents[3]:
            return
        path = self._trade_review_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        serialized = json.dumps(state, ensure_ascii=False, indent=2, default=str)
        # Flush the complete JSON snapshot to disk before atomically replacing the
        # previous state. A crash must not leave a truncated review/follow-up file.
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)

    def _minimum_net_rr_for_plan(self, base_plan: Dict[str, Any]) -> float:
        """Use a lower R:R floor only for explicitly enabled DEMO exploration."""
        if _demo_exploration_enabled() and str(base_plan.get("execution_mode") or "").upper() == "DEMO_STYLE_DISCOVERY":
            return 0.20
        return float(self.MIN_RR)

    @staticmethod
    def _planned_target(base_plan: Dict[str, Any]) -> float:
        """Return the best positive target supplied by the current strategy analysis."""
        plan = base_plan.get("order_plan") or {}
        reaction = base_plan.get("reaction_analysis") or {}
        hierarchy = base_plan.get("hierarchy") or {}
        strategy = (base_plan.get("strategy_results") or {}).get(
            str(base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "").upper(), {}
        )
        candidates = (
            plan.get("take_profit"),
            (reaction.get("order_plan") or {}).get("take_profit"),
            (reaction.get("scenario") or {}).get("target"),
            (hierarchy.get("order_plan") or {}).get("take_profit"),
            (strategy.get("order_plan") or {}).get("take_profit"),
            strategy.get("target"),
            strategy.get("research_target"),
            (strategy.get("market_behavior") or {}).get("target_price"),
        )
        for value in candidates:
            try:
                target = float(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(target) and target > 0:
                return target
        return 0.0

    @staticmethod
    def _best_structural_target_for_net_rr(
        candidates: List[Dict[str, Any]], direction: str, entry: float,
        risk_distance: float, cost_allowance: float, min_net_rr: float,
        decision_time: float,
    ) -> Optional[Tuple[float, Dict[str, Any], float]]:
        """Pick the nearest causally confirmed structural target clearing net R:R."""
        eligible: List[Tuple[float, float, Dict[str, Any], float]] = []
        for candidate in candidates or []:
            try:
                candidate_price = float(candidate.get("price"))
                candidate_confirmation = int(candidate.get("confirmation_time", 0) or 0)
            except (AttributeError, TypeError, ValueError, OverflowError):
                continue
            if (not math.isfinite(candidate_price) or candidate_price <= 0
                    or candidate_confirmation > decision_time):
                continue
            reward = candidate_price - entry if direction == "BUY" else entry - candidate_price
            if reward <= 0 or risk_distance <= 0:
                continue
            net_rr = max(0.0, reward - cost_allowance) / (risk_distance + cost_allowance)
            if net_rr > min_net_rr:
                eligible.append((reward, candidate_price, candidate, net_rr))
        if not eligible:
            return None
        _, price, evidence, net_rr = min(eligible, key=lambda item: item[0])
        return price, evidence, net_rr

    def _setup_signature(self, symbol: str, base_plan: Dict[str, Any]) -> str:
        """Fingerprint the actual strategy/structure/entry-risk plan, excluding clock time."""
        import hashlib
        plan = base_plan.get("order_plan") or {}
        structure = base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {}
        chain = structure.get("hierarchy_chain") or []
        structure_ids = [str(item.get("event_id") or item.get("base_id") or "") for item in chain if isinstance(item, dict)]
        structure_ids.extend(str(structure.get(key) or "") for key in ("parent_base_id", "child_base_id", "micro_base_id"))
        payload = {
            "symbol": str(symbol).upper(),
            "strategy": str(base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY").upper(),
            "direction": str(plan.get("direction") or "").upper(),
            "entry": round(float(plan.get("entry") or 0.0), 8),
            "stop_loss": round(float(plan.get("stop_loss") or 0.0), 8),
            "take_profit": round(self._planned_target(base_plan), 8),
            "structure_ids": structure_ids,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _remember_submitted_setup(self, symbol: str, base_plan: Dict[str, Any], plan: Dict[str, Any], response: Any) -> None:
        """Persist the exact decision that caused an accepted real broker entry."""
        # Mock adapters are used heavily in unit tests; they must never write into
        # the production review journal or poison its next-entry guard.
        if type(self.adapter) is not RealMT5BrokerAdapter:
            return
        try:
            state = self._load_trade_review_state()
            state["last_submitted_setup_by_symbol"][symbol.upper()] = {
                "signature": self._setup_signature(symbol, base_plan),
                "symbol": symbol.upper(),
                "strategy": str(base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY").upper(),
                "direction": str(plan.get("direction") or "").upper(),
                "entry": float(plan.get("entry") or 0.0),
                "stop_loss": float(plan.get("stop_loss") or 0.0),
                "take_profit": self._planned_target(base_plan),
                "order_id": str(getattr(response, "OrderId", "") or ""),
                "deal_ticket": str(getattr(response, "DealTicket", "") or ""),
                "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
                "analysis_reason": str(base_plan.get("reason") or ""),
                "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
            }
            self._save_trade_review_state(state)
        except Exception:
            logger.exception("Unable to persist submitted trade analysis; broker execution remains recorded separately")

    def _sync_trade_review(self, symbol: str, positions: List[Any], tick: Dict[str, Any],
                           base_plan: Optional[Dict[str, Any]] = None) -> None:
        """Track each DEMO position, review its evolving setup, and learn from broker-confirmed exits."""
        try:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            state = self._load_trade_review_state()
            tracked = state["open_positions"]
            active_ids = set()
            mt5 = self.adapter._mt5
            self._update_post_close_followups(state, symbol, now)
            buy_type = int(getattr(mt5, "POSITION_TYPE_BUY", 0))
            deal_buy = int(getattr(mt5, "DEAL_TYPE_BUY", 0))
            deal_sell = int(getattr(mt5, "DEAL_TYPE_SELL", 1))
            entry_in = int(getattr(mt5, "DEAL_ENTRY_IN", 0))
            exit_entries = {int(getattr(mt5, "DEAL_ENTRY_OUT", 1)), int(getattr(mt5, "DEAL_ENTRY_OUT_BY", 3))}
            reason_sl = int(getattr(mt5, "DEAL_REASON_SL", 4))
            reason_tp = int(getattr(mt5, "DEAL_REASON_TP", 5))
            bid, ask = float(tick.get("bid") or 0.0), float(tick.get("ask") or 0.0)
            analysis = base_plan or {}
            analysis_signature = self._setup_signature(symbol, analysis) if analysis else ""
            for pos in positions or []:
                if int(self._field(pos, "magic", 0) or 0) != 100001:
                    continue
                comment = str(self._field(pos, "comment", "") or "")
                if not comment.startswith("YarBase"):
                    continue
                ticket = int(self._field(pos, "ticket", 0) or 0)
                identifier = int(self._field(pos, "identifier", 0) or ticket)
                if identifier <= 0:
                    continue
                key = str(identifier)
                active_ids.add(key)
                direction = "BUY" if int(self._field(pos, "type", -1)) == buy_type else "SELL"
                entry = float(self._field(pos, "price_open", 0.0) or 0.0)
                current = bid if direction == "BUY" else ask
                move = (current - entry) if direction == "BUY" else (entry - current)
                record = tracked.get(key)
                if not isinstance(record, dict):
                    submitted = state["last_submitted_setup_by_symbol"].get(symbol.upper(), {})
                    record = {
                        "position_id": identifier, "ticket": ticket, "symbol": symbol.upper(),
                        "direction": direction, "strategy": comment.split(":", 1)[1].upper() if ":" in comment else "BASE_HIERARCHY",
                        "entry_price": entry, "initial_stop_loss": float(self._field(pos, "sl", 0.0) or 0.0),
                        "initial_take_profit": float(self._field(pos, "tp", 0.0) or 0.0),
                        "volume": float(self._field(pos, "volume", 0.0) or 0.0),
                        "opened_epoch": int(self._field(pos, "time", 0) or now.timestamp()),
                        "opened_at_utc": datetime.fromtimestamp(
                            int(self._field(pos, "time", 0) or now.timestamp()), timezone.utc
                        ).isoformat(), "max_favorable_excursion": 0.0,
                        "max_adverse_excursion": 0.0, "analysis_reviews": [],
                        "setup_signature": submitted.get("signature") or (analysis_signature if analysis.get("status") == "ORDER_PROPOSAL" else ""),
                        "setup_snapshot": submitted or ({
                            "signature": analysis_signature, "symbol": symbol.upper(),
                            "strategy": analysis.get("selected_strategy") or analysis.get("decision_authority") or "BASE_HIERARCHY",
                            "direction": (analysis.get("order_plan") or {}).get("direction"),
                            "entry": (analysis.get("order_plan") or {}).get("entry"),
                            "stop_loss": (analysis.get("order_plan") or {}).get("stop_loss"),
                            "take_profit": self._planned_target(analysis),
                            "analysis_reason": analysis.get("reason"),
                            "structure": analysis.get("structure") or (analysis.get("hierarchy") or {}).get("structure") or {},
                        } if analysis.get("status") == "ORDER_PROPOSAL" else {}),
                    }
                    tracked[key] = record
                    snapshot = record.get("setup_snapshot") or {}
                    structure = snapshot.get("structure") or {}
                    self._log_event({
                        "event": "trade_review_started", "symbol": symbol.upper(),
                        "position_id": identifier, "ticket": ticket, "direction": direction,
                        "entry_price": entry, "initial_stop_loss": record["initial_stop_loss"],
                        "initial_take_profit": record["initial_take_profit"], "volume": record["volume"],
                        "opened_at_utc": record["opened_at_utc"],
                        "strategy_style": record.get("strategy") or snapshot.get("strategy") or "BASE_HIERARCHY",
                        "decision_timeframe": "MULTI_TIMEFRAME",
                        "setup_timeframe": structure.get("child_timeframe") or structure.get("selected_child_timeframe") or "UNKNOWN",
                        "entry_timeframe": snapshot.get("entry_timeframe") or "M1",
                        "execution_timeframe": "M1",
                        "context_timeframes": structure.get("hierarchy_timeframes_considered") or snapshot.get("context_timeframes") or ["H4", "H1", "M15", "M5", "M1"],
                        "setup_signature": record["setup_signature"],
                        "setup_description": snapshot.get("analysis_reason") or snapshot.get("reason") or "",
                        "hierarchy_structure": structure, "setup_snapshot": snapshot,
                        "data_source": "MT5_DEMO_BROKER",
                    })
                record["last_price"] = current
                record["last_seen_at_utc"] = now.isoformat()
                record["current_stop_loss"] = float(self._field(pos, "sl", 0.0) or 0.0)
                record["current_take_profit"] = float(self._field(pos, "tp", 0.0) or 0.0)
                record["max_favorable_excursion"] = max(float(record.get("max_favorable_excursion", 0.0)), move, 0.0)
                record["max_adverse_excursion"] = max(float(record.get("max_adverse_excursion", 0.0)), -move, 0.0)
                if analysis:
                    current_style = str(analysis.get("selected_strategy") or analysis.get("decision_authority") or record.get("strategy") or "BASE_HIERARCHY").upper()
                    previous_reviews = record.get("analysis_reviews") or []
                    previous_style = str(
                        record.get("last_reviewed_strategy")
                        or (previous_reviews[-1].get("strategy") if previous_reviews else "")
                        or ""
                    ).upper()
                    if previous_style and current_style and current_style != previous_style:
                        transition = {
                            "timestamp_utc": now.isoformat(), "position_id": identifier,
                            "symbol": symbol.upper(), "from_style": previous_style, "to_style": current_style,
                            "reason": str(analysis.get("reason") or "Strategy authority changed during open trade")[:600],
                            "risk_revalidation_required": True,
                            "entry_style_remains_immutable": True,
                        }
                        record.setdefault("style_transitions", []).append(transition)
                        self._log_event({"event": "trade_style_transition", **transition})
                    record["last_reviewed_strategy"] = current_style
                    review = {
                        "timestamp_utc": now.isoformat(), "setup_signature": analysis_signature,
                        "status": analysis.get("status"), "strategy": current_style,
                        "reason": str(analysis.get("reason") or "")[:600],
                        "direction": str((analysis.get("order_plan") or {}).get("direction") or "WAIT"),
                        "entry": (analysis.get("order_plan") or {}).get("entry"),
                        "stop_loss": (analysis.get("order_plan") or {}).get("stop_loss"),
                        "take_profit": (analysis.get("order_plan") or {}).get("take_profit"),
                    }
                    reviews = record.setdefault("analysis_reviews", [])
                    if not reviews or reviews[-1].get("setup_signature") != analysis_signature or (
                            now.timestamp() - datetime.fromisoformat(reviews[-1]["timestamp_utc"]).timestamp() >= 60):
                        reviews.append(review)
                        record["analysis_reviews"] = reviews[-100:]
                        self._log_event({"event": "open_trade_analysis_review", "symbol": symbol.upper(),
                                         "position_id": identifier, "ticket": ticket, **review})

            # Read authoritative deal history and process each fully closed position once.
            deals = self.adapter.get_history_deals(date_from=now - timedelta(days=30), date_to=now)
            if deals is not None:
                grouped: Dict[str, List[Any]] = {}
                for deal in deals:
                    if str(self._field(deal, "symbol", "")).upper() != symbol.upper() or int(self._field(deal, "magic", 0) or 0) != 100001:
                        continue
                    position_id = int(self._field(deal, "position_id", 0) or 0)
                    if position_id > 0:
                        grouped.setdefault(str(position_id), []).append(deal)
                for position_id, history in grouped.items():
                    if (position_id in active_ids or position_id in state["processed_position_ids"]
                            or position_id in state["ignored_untracked_position_ids"]):
                        continue
                    entries = [d for d in history if int(self._field(d, "entry", -1)) == entry_in]
                    exits = [d for d in history if int(self._field(d, "entry", -1)) in exit_entries]
                    if not entries or not exits:
                        continue
                    entry_deal = min(entries, key=lambda d: int(self._field(d, "time", 0) or 0))
                    exit_deal = max(exits, key=lambda d: int(self._field(d, "time", 0) or 0))
                    record = tracked.get(position_id)
                    if not isinstance(record, dict):
                        submitted_candidate = state["last_submitted_setup_by_symbol"].get(symbol.upper(), {})
                        entry_ticket = str(self._field(entry_deal, "ticket", "") or "")
                        entry_order = str(self._field(entry_deal, "order", "") or "")
                        matches_submission = bool(submitted_candidate) and (
                            (entry_ticket and entry_ticket == str(submitted_candidate.get("deal_ticket", "")))
                            or (entry_order and entry_order == str(submitted_candidate.get("order_id", "")))
                        )
                        if not matches_submission:
                            # This position closed before continuous monitoring began.
                            # Its result is real broker history, but its original SL/TP
                            # and analysis were not captured; do not fabricate a lesson.
                            state["ignored_untracked_position_ids"][position_id] = {
                                "symbol": symbol.upper(), "reason": "closed_before_continuous_trade_review_started",
                                "exit_time": int(self._field(exit_deal, "time", 0) or 0),
                            }
                            continue
                        record = {
                            "position_id": int(position_id), "symbol": symbol.upper(),
                            "direction": submitted_candidate.get("direction"),
                            "entry_price": float(self._field(entry_deal, "price", 0.0) or 0.0),
                            "initial_stop_loss": float(submitted_candidate.get("stop_loss") or 0.0),
                            "initial_take_profit": float(submitted_candidate.get("take_profit") or 0.0),
                            "strategy": submitted_candidate.get("strategy", "BASE_HIERARCHY"),
                            "setup_signature": submitted_candidate.get("signature", ""),
                            "setup_snapshot": submitted_candidate, "max_favorable_excursion": 0.0,
                            "max_adverse_excursion": 0.0, "analysis_reviews": [],
                        }
                    entry_type = int(self._field(entry_deal, "type", -1))
                    direction = "BUY" if entry_type == deal_buy else ("SELL" if entry_type == deal_sell else str(record.get("direction", "UNKNOWN")))
                    if direction not in ("BUY", "SELL"):
                        continue
                    entry_price = float(record.get("entry_price") or self._field(entry_deal, "price", 0.0) or 0.0)
                    exit_price = float(self._field(exit_deal, "price", 0.0) or 0.0)
                    gross_pnl = sum(float(self._field(d, "profit", 0.0) or 0.0) for d in history)
                    commission_total = sum(float(self._field(d, "commission", 0.0) or 0.0) for d in history)
                    swap_total = sum(float(self._field(d, "swap", 0.0) or 0.0) for d in history)
                    fee_total = sum(float(self._field(d, "fee", 0.0) or 0.0) for d in history)
                    pnl = gross_pnl + commission_total + swap_total + fee_total
                    reasons = {int(self._field(d, "reason", -1) or -1) for d in exits}
                    exit_reason = "STOP_LOSS" if reason_sl in reasons else ("TAKE_PROFIT" if reason_tp in reasons else "STRATEGY_OR_MANUAL_EXIT")
                    submitted = record.get("setup_snapshot") or state["last_submitted_setup_by_symbol"].get(symbol.upper(), {})
                    signature = record.get("setup_signature") or submitted.get("signature", "")
                    decision_id = f"autonomous-demo-position-{position_id}"
                    try:
                        from src.Research.Brain.learning_bridge import BrainLearningBridge
                        learning_result = BrainLearningBridge().record_demo_outcome(
                            decision_id=decision_id, symbol=symbol.upper(), timeframe="M1", direction=direction,
                            entry_price=entry_price, exit_price=exit_price, pnl=pnl,
                            mfe=float(record.get("max_favorable_excursion", 0.0) or 0.0),
                            mae=float(record.get("max_adverse_excursion", 0.0) or 0.0),
                            context={
                                "position_id": int(position_id), "ticket": record.get("ticket"),
                                "exit_reason": exit_reason, "stop_loss": record.get("initial_stop_loss", submitted.get("stop_loss", 0.0)),
                                "take_profit": record.get("initial_take_profit", submitted.get("take_profit", 0.0)),
                                "strategy": record.get("strategy", submitted.get("strategy", "BASE_HIERARCHY")),
                                "setup_signature": signature, "setup_snapshot": submitted,
                                "analysis_reviews": record.get("analysis_reviews", []),
                                "opened_at_utc": record.get("opened_at_utc"),
                                "closed_at_utc": datetime.fromtimestamp(int(self._field(exit_deal, "time", now.timestamp()) or now.timestamp()), timezone.utc).isoformat(),
                                "broker_exit_deal_tickets": [int(self._field(d, "ticket", 0) or 0) for d in exits],
                                "gross_and_cost_adjusted_pnl": pnl,
                            },
                        )
                        if not isinstance(learning_result, dict) or learning_result.get("source") != "DEMO":
                            raise RuntimeError("Brain Learning Bridge did not confirm durable DEMO outcome processing.")
                        self._log_event({
                            "event": "trade_outcome_learned", "symbol": symbol.upper(),
                            "position_id": int(position_id), "direction": direction, "exit_reason": exit_reason,
                            "entry_price": entry_price, "exit_price": exit_price,
                            "pnl_gross": gross_pnl, "pnl_net_including_costs": pnl,
                            "costs": {
                                "commission": commission_total, "swap": swap_total, "fees": fee_total,
                                "cost_total": commission_total + swap_total + fee_total,
                                "source": "MT5_DEAL_HISTORY",
                            },
                            "result": "WIN" if pnl > 0.5 else ("LOSS" if pnl < -0.5 else "BREAKEVEN"),
                            "post_trade_conclusion": (
                                f"Broker-confirmed close: {exit_reason}; net PnL including recorded costs={pnl:.2f}; "
                                f"MFE={float(record.get('max_favorable_excursion', 0.0) or 0.0):.5f}; "
                                f"MAE={float(record.get('max_adverse_excursion', 0.0) or 0.0):.5f}. "
                                "This is an outcome summary, not proof the strategy has positive expectancy."
                            ),
                            "post_trade_review_status": "PENDING_RESEARCH_REVIEW",
                            "alternative_entry_analysis": {
                                "status": "PENDING_REPLAY",
                                "hypothesis": (
                                    "If selected-base boundaries are present, replay entry at 20% into the base "
                                    "and a stop beyond the far base boundary plus a volatility buffer."
                                ),
                                "required_checks": [
                                    "compare fill probability and missed-entry rate",
                                    "recalculate stop distance, position size, and net R multiple",
                                    "include spread, commission, slippage, and broker stop constraints",
                                    "validate on chronological out-of-sample data before changing execution",
                                ],
                            },
                            "initial_stop_loss": record.get("initial_stop_loss"),
                            "initial_take_profit": record.get("initial_take_profit"),
                            "opened_at_utc": record.get("opened_at_utc") or datetime.fromtimestamp(
                                int(self._field(entry_deal, "time", now.timestamp()) or now.timestamp()), timezone.utc
                            ).isoformat(),
                            "closed_at_utc": datetime.fromtimestamp(
                                int(self._field(exit_deal, "time", now.timestamp()) or now.timestamp()), timezone.utc
                            ).isoformat(),
                            "strategy_style": record.get("strategy") or submitted.get("strategy") or "BASE_HIERARCHY",
                            "decision_timeframe": "MULTI_TIMEFRAME",
                            "setup_timeframe": (submitted.get("structure") or {}).get("child_timeframe") or "UNKNOWN",
                            "entry_timeframe": submitted.get("entry_timeframe") or "M1",
                            "execution_timeframe": "M1",
                            "context_timeframes": (submitted.get("structure") or {}).get("hierarchy_timeframes_considered") or submitted.get("context_timeframes") or ["H4", "H1", "M15", "M5", "M1"],
                            "setup_description": submitted.get("analysis_reason") or "",
                            "setup_snapshot": submitted,
                            "mfe": record.get("max_favorable_excursion", 0.0),
                            "mae": record.get("max_adverse_excursion", 0.0),
                            "learning_result": learning_result,
                            "data_source": "MT5_DEAL_HISTORY",
                        })
                    except Exception as learning_exc:
                        # Keep the broker-confirmed close eligible for retry on the next
                        # reconciliation cycle. Never mark a failed learning write processed.
                        self._log_event({
                            "event": "trade_outcome_learning_failed", "symbol": symbol.upper(),
                            "position_id": int(position_id), "decision_id": decision_id,
                            "error": str(learning_exc)[:1000], "retryable": True,
                        })
                        logger.exception("Broker-confirmed outcome learning failed for position %s; will retry", position_id)
                        continue
                    closed_at_epoch = int(self._field(exit_deal, "time", now.timestamp()) or now.timestamp())
                    closed_at_utc = datetime.fromtimestamp(closed_at_epoch, timezone.utc).isoformat()
                    followup_key = str(position_id)
                    state.setdefault("post_close_followups", {}).setdefault(followup_key, {
                        "position_id": int(position_id),
                        "symbol": symbol.upper(),
                        "direction": direction,
                        "exit_reason": exit_reason,
                        "exit_price": exit_price,
                        "entry_price": entry_price,
                        "pnl_net_including_costs": pnl,
                        "closed_at_epoch": closed_at_epoch,
                        "closed_at_utc": closed_at_utc,
                        "decision_id": decision_id,
                        "status": "WAITING_FOR_FIVE_CLOSED_M1_BARS",
                    })
                    state["processed_position_ids"][position_id] = {
                        "symbol": symbol.upper(), "exit_reason": exit_reason, "pnl": pnl,
                        "exit_price": exit_price, "closed_at_utc": closed_at_utc,
                        "learning_status": "CONFIRMED", "decision_id": decision_id,
                        "post_close_followup_status": "PENDING_FIVE_M1_BARS",
                    }
                    if signature:
                        state["last_closed_setup_by_symbol"][symbol.upper()] = {
                            "signature": signature, "position_id": int(position_id),
                            "exit_reason": exit_reason, "pnl": pnl, "closed_at_utc": now.isoformat(),
                        }
                    tracked.pop(position_id, None)
            # Keep the state bounded while retaining enough idempotency history.
            if len(state["processed_position_ids"]) > 5000:
                state["processed_position_ids"] = dict(list(state["processed_position_ids"].items())[-4000:])
            self._save_trade_review_state(state)
        except Exception:
            # Reviews and learning must never disable broker-side protection or close a trade.
            logger.exception("Continuous trade review/learning failed for %s", symbol)

    def _sync_strategy_learning(self, symbol: str, positions: List[Any], now_epoch: int) -> None:
        """Persist broker-authoritative positions continuously and deal history idempotently."""
        try:
            from datetime import timedelta
            from src.Learning.Services.autonomous_strategy_discovery import AutonomousStrategyDiscovery
            now = datetime.now(timezone.utc)
            store = AutonomousStrategyDiscovery(_PROJECT_ROOT / "storage" / "strategy_discovery" / symbol.upper())
            # Snapshots run every cycle; full-history recovery runs once per worker start,
            # then recent history is polled at most once per minute to limit MT5 load.
            if now_epoch - self._last_learning_sync_epoch >= 60:
                initial_recovery = self._last_learning_sync_epoch == 0
                window_days = 365 if initial_recovery else 7
                deals = self.adapter.get_history_deals(date_from=now - timedelta(days=window_days), date_to=now)
                if deals is None:
                    self._log_event({"event": "strategy_learning_sync_unavailable", "symbol": symbol,
                                     "reason": "Broker deal history unavailable; no synthetic history written."})
                else:
                    history_result = store.sync_history(deals, self.adapter._mt5, symbol=symbol)
                    self._last_learning_sync_epoch = now_epoch
                    # Rebuild from opening-deal ownership on every history sync.
                    # Older reports may have mixed manual account trades into bot learning;
                    # keeping a stale report when no new deal arrives would preserve that bug.
                    report = store.build_discovery_report()
                    self._log_event({"event": "strategy_learning_sync", "symbol": symbol,
                                     "new_deals_recorded": history_result.get("new_deals_recorded", 0),
                                     "history_deals_seen": history_result.get("total_seen", 0),
                                     "open_positions": len(positions),
                                     "closed_position_count": report.get("closed_position_count", 0),
                                     "discovery_cohorts": len(report.get("cohorts", [])),
                                     "auto_promotion_enabled": report.get("auto_promotion_enabled", False)})
            store.snapshot_positions(positions, now_utc=now.isoformat())
        except Exception:
            # Learning/audit failure must not interrupt protective position management.
            logger.exception("Unable to synchronize autonomous strategy-learning evidence")

    def _track_post_exit_market_path(self, symbol: str, tick: Dict[str, Any]) -> None:
        """Observe price for 60 minutes after DEMO SL/TP exits and persist excursion feedback."""
        try:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=7)
            deals = self.adapter.get_history_deals(date_from=start, date_to=now)
            if deals is None:
                return
            path = _PROJECT_ROOT / "runtime_logs" / "post_exit_price_tracking.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            except (OSError, ValueError, TypeError):
                state = {}
            if not isinstance(state, dict):
                state = {}
            # Migrate legacy records that were marked complete without the current
            # sample-count, coverage, and gap checks. They must be reclassified rather
            # than silently trusted as valid post-exit evidence.
            for legacy in state.values():
                if not isinstance(legacy, dict):
                    continue
                observations = legacy.get("observations", [])
                sample_count = int(legacy.get("observation_count_total", len(observations) if isinstance(observations, list) else 0) or 0)
                status = str(legacy.get("tracking_status", "")).upper()
                if legacy.get("tracking_complete") and (not status or (status == "COMPLETE" and sample_count < 6)):
                    legacy["tracking_complete"] = False
                    legacy["tracking_status"] = "LEGACY_UNVERIFIED"
                    legacy["legacy_completion_reclassified_at_utc"] = now.isoformat()
                    self._log_event({
                        "event": "post_exit_price_tracking_legacy_reclassified",
                        "symbol": str(legacy.get("symbol", symbol)).upper(),
                        "deal_ticket": legacy.get("deal_ticket"),
                        "previous_observation_count": sample_count,
                        "reason": "Legacy completion did not prove sufficient one-hour sample coverage.",
                    })
            mt5 = self.adapter._mt5
            entry_in = int(getattr(mt5, "DEAL_ENTRY_IN", 0))
            entry_out = int(getattr(mt5, "DEAL_ENTRY_OUT", 1))
            entry_out_by = int(getattr(mt5, "DEAL_ENTRY_OUT_BY", 3))
            reason_sl = int(getattr(mt5, "DEAL_REASON_SL", 4))
            reason_tp = int(getattr(mt5, "DEAL_REASON_TP", 5))
            deal_buy = int(getattr(mt5, "DEAL_TYPE_BUY", 0))
            deal_sell = int(getattr(mt5, "DEAL_TYPE_SELL", 1))
            relevant = [
                d for d in deals
                if str(self._field(d, "symbol", "")).upper() == symbol.upper()
                and int(self._field(d, "magic", 0) or 0) == 100001
            ]
            entries = {
                int(self._field(d, "position_id", 0) or 0): d
                for d in relevant
                if int(self._field(d, "entry", -1) or 0) == entry_in
                and int(self._field(d, "position_id", 0) or 0) > 0
            }
            for deal in relevant:
                reason = int(self._field(deal, "reason", -1) or 0)
                entry_kind = int(self._field(deal, "entry", -1) or 0)
                if reason not in (reason_sl, reason_tp) or entry_kind not in (entry_out, entry_out_by):
                    continue
                ticket = int(self._field(deal, "ticket", 0) or 0)
                if ticket <= 0 or str(ticket) in state:
                    continue
                position_id = int(self._field(deal, "position_id", 0) or 0)
                entry_deal = entries.get(position_id)
                entry_type = int(self._field(entry_deal, "type", -1) or 0) if entry_deal else -1
                exit_type = int(self._field(deal, "type", -1) or 0)
                if entry_type == deal_buy:
                    direction = "BUY"
                elif entry_type == deal_sell:
                    direction = "SELL"
                elif exit_type == deal_sell:
                    direction = "BUY"
                elif exit_type == deal_buy:
                    direction = "SELL"
                else:
                    continue
                state[str(ticket)] = {
                    "deal_ticket": ticket, "position_id": position_id, "symbol": symbol.upper(),
                    "direction": direction,
                    "exit_reason": "STOP_LOSS" if reason == reason_sl else "TAKE_PROFIT",
                    "exit_time": int(self._field(deal, "time", 0) or 0),
                    "exit_price": float(self._field(deal, "price", 0.0) or 0.0),
                    "profit": float(self._field(deal, "profit", 0.0) or 0.0),
                    "observations": [], "max_favorable_move": 0.0, "max_adverse_move": 0.0,
                    "tracking_complete": False,
                }
                self._log_event({
                    "event": "post_exit_price_tracking_started", "symbol": symbol.upper(),
                    "deal_ticket": ticket, "exit_reason": state[str(ticket)]["exit_reason"],
                    "direction": direction, "exit_price": state[str(ticket)]["exit_price"],
                    "tracking_minutes": 60,
                })
            mid = (float(tick.get("bid", 0.0)) + float(tick.get("ask", 0.0))) / 2.0
            if mid <= 0:
                return
            changed = False
            for record in state.values():
                if record.get("symbol") != symbol.upper() or record.get("tracking_complete"):
                    continue
                exit_epoch = int(record.get("exit_time", 0) or 0)
                exit_price = float(record.get("exit_price", 0.0) or 0.0)
                if exit_epoch <= 0 or exit_price <= 0:
                    continue
                elapsed = max(0, int(now.timestamp()) - exit_epoch)
                observations = record.setdefault("observations", [])
                # A closed deal discovered long after its exit has no observable
                # one-hour path. Never compare its exit price to today's quote and
                # call that a post-stop continuation signal.
                if not observations and elapsed > 300:
                    record["tracking_complete"] = True
                    record["tracking_status"] = "SKIPPED_LATE_DISCOVERY"
                    record["elapsed_seconds"] = elapsed
                    self._log_event({
                        "event": "post_exit_price_tracking_incomplete", "symbol": symbol.upper(),
                        "deal_ticket": record["deal_ticket"], "exit_reason": record["exit_reason"],
                        "direction": record.get("direction"), "observations": 0,
                        "elapsed_seconds": elapsed, "max_favorable_move": None, "max_adverse_move": None,
                        "reason": "First sample arrived more than five minutes after exit; historical price path is unavailable.",
                        "learning_note": "Insufficient samples; no post-exit continuation inference recorded.",
                    })
                    changed = True
                    continue
                prev_epoch = record.get("last_observation_epoch")
                if prev_epoch is None and observations:
                    try:
                        prev_epoch = datetime.fromisoformat(str(observations[-1]["time_utc"]).replace("Z", "+00:00")).timestamp()
                    except (KeyError, TypeError, ValueError):
                        prev_epoch = None
                if prev_epoch is not None:
                    gap = max(0, int(now.timestamp()) - int(float(prev_epoch)))
                    record["max_observation_gap_seconds"] = max(int(record.get("max_observation_gap_seconds", 0)), gap)
                now_epoch = int(now.timestamp())
                if not record.get("first_observation_epoch"):
                    record["first_observation_epoch"] = now_epoch
                record["last_observation_epoch"] = now_epoch
                record["observation_count_total"] = int(record.get("observation_count_total", len(observations))) + 1
                move = (mid - exit_price) if record.get("direction") == "BUY" else (exit_price - mid)
                record["max_favorable_move"] = max(float(record.get("max_favorable_move", 0.0)), move, 0.0)
                record["max_adverse_move"] = min(float(record.get("max_adverse_move", 0.0)), move, 0.0)
                observations.append({
                    "time_utc": now.isoformat(), "bid": float(tick.get("bid", 0.0)),
                    "ask": float(tick.get("ask", 0.0)), "mid": mid,
                    "move_in_trade_direction": move,
                })
                # Keep the persistent journal bounded; cumulative counts/gaps remain separate.
                record["observations"] = observations[-130:]
                record["elapsed_seconds"] = elapsed
                changed = True
                if elapsed >= 3600:
                    first_epoch = int(record.get("first_observation_epoch", 0) or 0)
                    last_epoch = int(record.get("last_observation_epoch", 0) or 0)
                    sample_count = int(record.get("observation_count_total", 0) or 0)
                    max_gap = int(record.get("max_observation_gap_seconds", 0) or 0)
                    coverage_ok = (first_epoch > 0 and first_epoch <= exit_epoch + 300
                                   and last_epoch >= exit_epoch + 3600 and sample_count >= 6
                                   and max_gap <= 600)
                    record["tracking_complete"] = True
                    if not coverage_ok:
                        record["tracking_status"] = "INSUFFICIENT_SAMPLES"
                        self._log_event({
                            "event": "post_exit_price_tracking_incomplete", "symbol": symbol.upper(),
                            "deal_ticket": record["deal_ticket"], "exit_reason": record["exit_reason"],
                            "direction": record.get("direction"), "observations": sample_count,
                            "elapsed_seconds": elapsed, "max_observation_gap_seconds": max_gap,
                            "max_favorable_move": None, "max_adverse_move": None,
                            "reason": "One-hour coverage failed the minimum sample/gap checks.",
                            "learning_note": "Insufficient samples; no post-exit continuation inference recorded.",
                        })
                    else:
                        record["tracking_status"] = "COMPLETE"
                        self._log_event({
                            "event": "post_exit_price_tracking_completed", "symbol": symbol.upper(),
                            "deal_ticket": record["deal_ticket"], "exit_reason": record["exit_reason"],
                            "direction": record.get("direction"), "observations": sample_count,
                            "elapsed_seconds": elapsed, "max_observation_gap_seconds": max_gap,
                            "max_favorable_move": record["max_favorable_move"],
                            "max_adverse_move": record["max_adverse_move"],
                            "learning_note": (
                                "Post-exit price continued favorably after a fully sampled one-hour window; review entry/exit timing."
                                if record["max_favorable_move"] > 0 else
                                "No favorable continuation observed during a fully sampled one-hour window."
                            ),
                        })
            if changed or state:
                temp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
                temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                temp.replace(path)
        except Exception:
            # Market observation is non-blocking: it must never halt safe DEMO execution.
            logger.exception("Post-exit market-path tracking failed for %s", symbol)

    def _confirm_position_flat(self, symbol: str, ticket: int) -> Dict[str, Any]:
        """Require an authoritative broker snapshot to confirm the old position is flat."""
        try:
            positions = self.adapter.get_positions(symbol=symbol)
        except Exception as exc:
            return {"confirmed": False, "reason": f"Broker position re-query failed after close: {exc}"}
        if positions is None:
            return {"confirmed": False, "reason": "Broker position state is unknown after close; opposite entry remains blocked."}
        for position in positions:
            try:
                current_ticket = int(self._field(position, "ticket", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                return {"confirmed": False, "reason": "Broker returned an invalid position ticket after close; opposite entry remains blocked."}
            if current_ticket == int(ticket):
                return {"confirmed": False, "reason": f"Position {ticket} is still open after close request; opposite entry remains blocked."}
        return {"confirmed": True, "reason": "Broker confirms the previous position is flat; a fresh next-cycle assessment may consider the opposite direction."}

    def _evaluate_daily_risk(self, account: Dict[str, Any], broker_tick_time: int) -> Dict[str, Any]:
        from src.Risk.Services.daily_loss_kill_switch import (
            DailyLossKillSwitch, calculate_yartrader_daily_pnl,
        )
        risk_now = datetime.now(timezone.utc)
        equity = float(account.get("equity") or 0.0)
        if not math.isfinite(equity) or equity <= 0:
            return {"allowed": False, "reason": "KILL_SWITCH_ERROR", "meta": {}}
        pnl = calculate_yartrader_daily_pnl(self.adapter, now_utc=risk_now)
        risk_switch = DailyLossKillSwitch.get_instance()
        session_key, _, _ = risk_switch.get_session_key_and_window(risk_now)
        # A fresh process or a new session must establish a baseline before the
        # fail-closed evaluator can approve entries. When dynamic bot PnL is used,
        # the persisted baseline is intentionally omitted; safely rehydrate it on
        # restart only if the kill switch is not already active. Never clear an
        # active daily-loss lock to make a trade possible.
        if risk_switch.current_session_key != session_key:
            risk_switch.update_session_state(equity, dt=risk_now)
        elif (risk_switch.baseline_equity is None
              or not math.isfinite(float(risk_switch.baseline_equity or 0.0))
              or float(risk_switch.baseline_equity or 0.0) <= 0.0):
            if not risk_switch.kill_switch_active:
                risk_switch.set_session_baseline(equity, session_key)
        allowed, reason, meta = risk_switch.evaluate_daily_loss(
            equity, now_utc=risk_now, bot_daily_pnl=pnl["total_pnl"]
        )
        meta.update({
            "yartrader_daily_realized_pnl": pnl["realized_pnl"],
            "yartrader_daily_floating_pnl": pnl["floating_pnl"],
            "yartrader_daily_total_pnl": pnl["total_pnl"],
            "yartrader_owned_deals": pnl["owned_deal_count"],
            "yartrader_open_positions": pnl["owned_open_positions"],
        })
        # The 10% daily loss kill switch is never bypassed, including DEMO exploration.
        # Exploration can broaden strategy discovery, not disable portfolio loss protection.
        return {"allowed": allowed, "reason": reason, "meta": meta, "pnl": pnl}

    def _advance_setup_zone_watch(
        self, symbol: str, strategy_name: str, plan: Dict[str, Any],
        tick: Dict[str, Any], symbol_info: Dict[str, Any],
        per_tf: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Persist zone proximity and closed-candle rejection evidence across worker cycles."""
        from pathlib import Path
        import os
        import threading

        direction = str(plan.get("direction") or "").upper()
        entry_raw = plan.get("entry") or plan.get("planned_entry")
        try:
            entry = float(entry_raw)
            bid, ask = float(tick.get("bid") or 0.0), float(tick.get("ask") or 0.0)
            point = float(symbol_info.get("point") or (0.01 if symbol.upper().startswith("XAU") else 0.0001))
        except (TypeError, ValueError):
            return {"state": "WAITING_FOR_ZONE", "reaction_confirmed": False, "reason": "Missing/invalid entry or quote."}
        if direction not in {"BUY", "SELL"} or entry <= 0 or bid <= 0 or ask < bid:
            return {"state": "WAITING_FOR_ZONE", "reaction_confirmed": False, "reason": "Invalid setup direction/quote."}

        bars = []
        if isinstance(per_tf, dict):
            for tf in ("M1", "M5", "M15"):
                candidate = per_tf.get(tf)
                if isinstance(candidate, list) and len(candidate) >= 2:
                    bars = candidate
                    break
        # _fetch_candles starts at MT5 shift=1, so every supplied bar is closed.
        # Use the newest completed candle; dropping bars[-1] added an avoidable
        # one-candle lag to live zone-reaction decisions.
        closed = bars[-1] if bars else None
        candle_ts = None
        if isinstance(closed, dict):
            candle_ts = closed.get("timestamp") or closed.get("time")

        ranges = []
        for bar in (bars[-21:-1] if len(bars) >= 3 else []):
            try:
                hi, lo = float(bar["high"]), float(bar["low"])
                if hi > lo > 0:
                    ranges.append(hi - lo)
            except (KeyError, TypeError, ValueError):
                pass
        ranges.sort()
        median_range = ranges[len(ranges)//2] if ranges else point * 20
        # Volatility-scaled tolerance, with a symbol-point floor and a cap to avoid
        # calling a distant price "near" during a volatility spike.
        tolerance = max(point * 8, min(median_range * 0.20, max(point * 8, entry * 0.0015)))
        mid = (bid + ask) / 2.0
        near = abs(mid - entry) <= tolerance

        signature = f"{symbol.upper()}|{strategy_name}|{direction}|{entry:.10f}|{plan.get('stop_loss')}|{plan.get('take_profit')}"
        safe_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum() or ch in "_-")
        safe_strategy = "".join(ch for ch in strategy_name.upper() if ch.isalnum() or ch in "_-")
        # One file per symbol/strategy avoids cross-symbol read-modify-write races
        # when multiple authorized worker processes scan concurrently.
        state_path = Path(_PROJECT_ROOT) / "runtime_logs" / f"setup_zone_watch_state_{safe_symbol}_{safe_strategy}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            all_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            if not isinstance(all_state, dict):
                all_state = {}
        except (OSError, ValueError, TypeError):
            all_state = {}
        key = f"{symbol.upper()}|{strategy_name}"
        state = all_state.get(key, {})
        if not isinstance(state, dict) or state.get("signature") != signature:
            state = {
                "signature": signature, "symbol": symbol.upper(), "strategy": strategy_name,
                "direction": direction, "entry": entry, "state": "WAITING_FOR_ZONE",
                "first_seen_utc": datetime.now(timezone.utc).isoformat(),
                "last_candle_timestamp": None, "reaction_confirmed": False,
            }
        previous = str(state.get("state") or "WAITING_FOR_ZONE")
        current = previous
        evidence = None

        if state.get("reaction_confirmed") and near:
            current = "REACTION_CONFIRMED"
        elif state.get("reaction_confirmed") and not near:
            current = "WAITING_FOR_ZONE"
            state["reaction_confirmed"] = False
            state.pop("reaction_evidence", None)
        elif near:
            if previous == "WAITING_FOR_ZONE":
                current = "NEAR_ZONE"
            if previous == "NEAR_ZONE" and current == "NEAR_ZONE" and isinstance(closed, dict) and candle_ts is not None and candle_ts != state.get("last_candle_timestamp"):
                try:
                    o, h, l, c = (float(closed[k]) for k in ("open", "high", "low", "close"))
                    candle_range = max(h - l, point)
                    upper_wick = h - max(o, c)
                    lower_wick = min(o, c) - l
                    if direction == "SELL":
                        rejected = c < o and c < entry and upper_wick >= candle_range * 0.20
                        evidence = {"candle_timestamp": candle_ts, "open": o, "high": h, "low": l, "close": c,
                                    "upper_wick": upper_wick, "rejection": rejected}
                    else:
                        rejected = c > o and c > entry and lower_wick >= candle_range * 0.20
                        evidence = {"candle_timestamp": candle_ts, "open": o, "high": h, "low": l, "close": c,
                                    "lower_wick": lower_wick, "rejection": rejected}
                    state["last_candle_timestamp"] = candle_ts
                    if rejected:
                        current = "REACTION_CONFIRMED"
                        state["reaction_confirmed"] = True
                        state["reaction_evidence"] = evidence
                except (KeyError, TypeError, ValueError):
                    evidence = {"candle_timestamp": candle_ts, "rejection": False, "reason": "Malformed closed candle"}
        else:
            current = "WAITING_FOR_ZONE"
            state["reaction_confirmed"] = False
            state.pop("reaction_evidence", None)

        state.update({
            "state": current, "last_observed_utc": datetime.now(timezone.utc).isoformat(),
            "last_mid": mid, "distance_to_entry": abs(mid - entry),
            "proximity_tolerance": tolerance, "last_candle_timestamp": candle_ts if candle_ts is not None else state.get("last_candle_timestamp"),
        })
        all_state[key] = state
        tmp = state_path.with_name(f"{state_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            tmp.write_text(json.dumps(all_state, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(state_path))
        except OSError as exc:
            logger.warning("Could not persist setup zone watch state for %s: %s", symbol, exc)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

        if current != previous or evidence is not None:
            self._log_event({
                "event": "setup_zone_watch_state_transition", "symbol": symbol.upper(),
                "strategy": strategy_name, "direction": direction, "state": current,
                "previous_state": previous, "planned_entry": entry, "bid": bid, "ask": ask,
                "distance_to_entry": abs(mid-entry), "proximity_tolerance": tolerance,
                "reaction_confirmed": bool(state.get("reaction_confirmed")),
                "reaction_evidence": state.get("reaction_evidence") if current == "REACTION_CONFIRMED" else evidence,
                "reason": "State changes only on zone proximity or a distinct completed-candle rejection; observation mode never authorizes an order."
            })
        return {
            "state": current, "reaction_confirmed": bool(state.get("reaction_confirmed")),
            "distance_to_entry": abs(mid-entry), "proximity_tolerance": tolerance,
            "reaction_evidence": state.get("reaction_evidence"),
        }

    @staticmethod
    def _has_confirmed_tp_extension_momentum(
        direction: str, per_tf: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> bool:
        """Require three completed M5 candles to confirm directional momentum and structure."""
        bars = (per_tf or {}).get("M5") or []
        # The final bar may still be forming; use only the three completed bars before it.
        if len(bars) < 4:
            return False
        try:
            closed = bars[-4:-1]
            candles = [{
                "open": float(bar["open"]), "high": float(bar["high"]),
                "low": float(bar["low"]), "close": float(bar["close"]),
            } for bar in closed]
        except (KeyError, TypeError, ValueError):
            return False
        a, b, c = candles
        side = str(direction or "").upper()
        if side == "BUY":
            return (
                a["close"] > a["open"] and b["close"] > b["open"] and c["close"] > c["open"]
                and a["close"] < b["close"] < c["close"]
                and b["high"] >= a["high"] and c["high"] >= b["high"]
                and b["low"] >= a["low"] and c["low"] >= b["low"]
            )
        if side == "SELL":
            return (
                a["close"] < a["open"] and b["close"] < b["open"] and c["close"] < c["open"]
                and a["close"] > b["close"] > c["close"]
                and b["low"] <= a["low"] and c["low"] <= b["low"]
                and b["high"] <= a["high"] and c["high"] <= b["high"]
            )
        return False

    def _reconcile_base_pending_order(
        self, symbol: str, base_plan: Dict[str, Any], tick: Dict[str, Any],
        account: Dict[str, Any], symbol_info: Dict[str, Any],
        per_tf: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Run entry reconciliation and journal the final decision for every path."""
        plan = base_plan.get("order_plan") or {}
        lock_fd, lock_path = _acquire_symbol_execution_lock(symbol)
        if lock_fd is None:
            reason = "Another DEMO worker is reconciling/submitting an order for this symbol; this concurrent cycle is suppressed."
            self._log_event({
                "event": "entry_execution_outcome", "symbol": symbol,
                "strategy": base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY",
                "status": "EXECUTION_LOCKED", "reason": reason,
                "direction": plan.get("direction"), "order_type": plan.get("order_type"),
                "planned_entry": plan.get("entry"), "broker_confirmed": False,
                "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                "historical_structure_analysis": base_plan.get("historical_structure_analysis") or (base_plan.get("hierarchy") or {}).get("historical_structure_analysis") or {},
            })
            return {"status": "EXECUTION_LOCKED", "reason": reason}
        try:
            try:
                outcome = self._reconcile_base_pending_order_impl(
                    symbol, base_plan, tick, account, symbol_info, per_tf=per_tf
                )
            except BaseException as exc:
                self._log_event({
                    "event": "entry_execution_outcome", "symbol": symbol,
                    "strategy": base_plan.get("selected_strategy") or base_plan.get("decision_authority"),
                    "status": "ERROR", "reason": f"Unhandled reconciliation exception: {type(exc).__name__}: {exc}",
                    "direction": plan.get("direction"), "order_type": plan.get("order_type"),
                    "planned_entry": plan.get("entry"), "stop_loss": plan.get("stop_loss"),
                    "take_profit": plan.get("take_profit"), "broker_confirmed": False,
                    "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                    "historical_structure_analysis": base_plan.get("historical_structure_analysis") or (base_plan.get("hierarchy") or {}).get("historical_structure_analysis") or {},
                    "entry_level_context": base_plan.get("entry_level_context") or {},
                })
                raise
        finally:
            try:
                os.close(lock_fd)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove DEMO execution lock for %s", symbol)
        status = str(outcome.get("status", "UNKNOWN")).upper()
        broker_status = outcome.get("broker_status")
        broker_ticket = outcome.get("ticket")
        submission_confirmed = broker_status == "Placed" and status in {
            "PENDING_ORDER_SUBMITTED", "MARKET_OPENED", "MARKET_SUBMITTED"
        }
        # PENDING_ORDER_ACTIVE is returned only after this cycle finds and
        # validates the order in the broker's current pending-order snapshot.
        # It is not a new submission, but it is a broker-confirmed live order.
        existing_order_confirmed = status == "PENDING_ORDER_ACTIVE" and bool(broker_ticket)
        broker_confirmed = submission_confirmed or existing_order_confirmed
        if existing_order_confirmed and not broker_status:
            broker_status = "Active"
        self._log_event({
            "event": "entry_execution_outcome", "symbol": symbol,
            "strategy": base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY",
            "status": status, "reason": outcome.get("reason"),
            "direction": plan.get("direction"), "order_type": outcome.get("order_type") or plan.get("order_type"),
            "planned_entry": plan.get("entry"),
            "execution_entry": outcome.get("entry", plan.get("entry")),
            "stop_loss": outcome.get("stop_loss", plan.get("stop_loss")),
            "take_profit": outcome.get("take_profit", plan.get("take_profit")),
            "broker_status": broker_status, "broker_ticket": outcome.get("ticket"),
            "broker_confirmed": broker_confirmed,
            "execution_enabled": broker_confirmed,
            "execution_details": {key: outcome.get(key) for key in (
                "risk", "risk_budget_usd", "minimum_lot_risk_usd", "risk_basis_usd",
                "volume", "entry", "expires_at", "ticket", "deal_ticket", "broker_retcode"
            ) if key in outcome},
            "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
            "historical_structure_analysis": base_plan.get("historical_structure_analysis") or (base_plan.get("hierarchy") or {}).get("historical_structure_analysis") or {},
            "entry_level_context": base_plan.get("entry_level_context") or {},
        })
        return outcome

    def _reconcile_base_pending_order_impl(
        self, symbol: str, base_plan: Dict[str, Any], tick: Dict[str, Any],
        account: Dict[str, Any], symbol_info: Dict[str, Any],
        per_tf: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Execute qualified DEMO entries as direct market deals, never pending orders.

        Legacy YarTrader-owned pending orders are cancelled under the DEMO safety
        gate so they cannot later create an unintended second entry.
        """
        orders = self.adapter.get_active_orders(symbol=symbol)
        if orders is None:
            return {"status": "BLOCKED", "reason": "Broker order state is unknown; refusing duplicate or new entry."}
        mt5 = self.adapter._mt5
        strategy_name = str(base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY").upper()
        strategy_comment = _strategy_broker_comment(strategy_name)
        owned = [
            order for order in orders
            if int(self._field(order, "magic", 0) or 0) == 100001
            and str(self._field(order, "comment", "") or "").startswith("YarBase")
        ]
        plan = base_plan.get("order_plan") or {}
        # Safe observation mode: scan and journal candidate zones without submitting orders.
        order_submission_enabled = _demo_config_value("YARTRADER_DEMO_ORDER_SUBMISSION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        if not order_submission_enabled:
            cancelled = []
            for order in owned:
                ticket = int(self._field(order, "ticket", 0) or 0)
                if ticket <= 0:
                    continue
                response = self.adapter.cancel_pending_order(ticket)
                if getattr(response, "Status", "") == "Cancelled":
                    cancelled.append(ticket)
                    self._log_event({"event": "watch_only_existing_pending_order_cancelled", "symbol": symbol, "ticket": ticket, "broker_status": getattr(response, "Status", ""), "reason": "Submission disabled; canceling an already-existing YarTrader pending entry so reaction can be observed before any future entry."})
                else:
                    self._log_event({"event": "watch_only_existing_pending_order_cancel_failed", "symbol": symbol, "ticket": ticket, "broker_status": getattr(response, "Status", ""), "broker_comment": getattr(response, "Comment", "")})
            watch_entry = plan.get("entry") or plan.get("planned_entry")
            watch_stop = plan.get("stop_loss")
            watch_target = plan.get("take_profit")
            bid = float(tick.get("bid") or 0.0)
            ask = float(tick.get("ask") or 0.0)
            watch = self._advance_setup_zone_watch(symbol, strategy_name, plan, tick, symbol_info, per_tf)
            proximity = watch.get("distance_to_entry")
            self._log_event({
                "event": "setup_zone_watch_only", "symbol": symbol, "strategy": strategy_name,
                "setup_status": base_plan.get("status"), "direction": plan.get("direction") or base_plan.get("direction"),
                "order_type": plan.get("order_type"), "planned_entry": watch_entry,
                "stop_loss_candidate": watch_stop, "take_profit_candidate": watch_target,
                "bid": bid, "ask": ask, "spread": max(0.0, ask - bid),
                "distance_to_entry": proximity, "proximity_tolerance": watch.get("proximity_tolerance"),
                "watch_state": watch.get("state"), "reaction_confirmed": watch.get("reaction_confirmed", False),
                "reaction_evidence": watch.get("reaction_evidence"),
                "cancelled_existing_pending_orders": cancelled,
                "reason": "Observation-only mode: persisted state tracks waiting, zone proximity, and completed-candle rejection. Even confirmed reaction cannot send orders while submission remains disabled."
            })
            return {"status": "WATCH_ONLY", "symbol": symbol,
                    "reason": "Setup zone journaled; state machine is observing price proximity and closed-candle reaction. Broker order submission is disabled.",
                    "planned_entry": watch_entry, "distance_to_entry": proximity,
                    "watch_state": watch.get("state"), "reaction_confirmed": watch.get("reaction_confirmed", False),
                    "cancelled_existing_pending_orders": cancelled, "execution_enabled": False}
        valid = base_plan.get("status") == "ORDER_PROPOSAL" and plan.get("status") == "PROPOSED"
        if not valid:
            # Review every existing order even when the strategy has no fresh
            # proposal. Finite-expiry orders are retained only until their broker
            # expiry; unbounded legacy orders are removed and cancellation is
            # verified before the next cycle can consider a replacement.
            cancelled = []
            for order in owned:
                expiration = int(self._field(order, "time_expiration", 0) or self._field(order, "expiration", 0) or 0)
                ticket = int(self._field(order, "ticket", 0) or 0)
                if ticket <= 0:
                    self._log_event({"event": "pending_order_review", "symbol": symbol,
                                     "review_decision": "BLOCK_UNKNOWN_TICKET",
                                     "reason": "Owned pending order has no valid ticket; no order mutation attempted."})
                    return {"status": "BLOCKED", "reason": "YarTrader-owned pending order has no valid ticket."}
                review_reason = str(base_plan.get("reason") or "No qualified entry proposal.")
                reason_lower = review_reason.lower()
                invalidation_terms = (
                    "opposes", "opposite structure", "structural invalidation", "zone invalidated",
                    "setup invalidated", "no longer valid", "scenario expired", "setup expired",
                    "direction conflict", "contradicts the current structure",
                )
                explicitly_invalidated = any(term in reason_lower for term in invalidation_terms)
                if expiration > 0 and not explicitly_invalidated:
                    self._log_event({
                        "event": "pending_order_review", "symbol": symbol, "ticket": ticket,
                        "review_decision": "KEEP_UNTIL_EXPIRY_NO_QUALIFIED_REPLACEMENT",
                        "expiration_epoch": expiration, "broker_entry": self._field(order, "price_open", None),
                        "broker_stop_loss": self._field(order, "sl", None),
                        "broker_take_profit": self._field(order, "tp", None),
                        "reason": review_reason,
                    })
                    continue
                cancel_decision = "CANCEL_INVALIDATED_PENDING_ORDER" if explicitly_invalidated else "CANCEL_UNBOUNDED_LEGACY_ORDER"
                self._log_event({"event": "pending_order_review", "symbol": symbol, "ticket": ticket,
                                 "review_decision": cancel_decision,
                                 "reason": review_reason if explicitly_invalidated else
                                           "Order has no broker-side expiry and current strategy has no qualified proposal."})
                response = self.adapter.cancel_pending_order(ticket)
                if getattr(response, "Status", "") != "Cancelled":
                    self._log_event({"event": "pending_order_cancel_result", "symbol": symbol,
                                     "ticket": ticket, "broker_status": getattr(response, "Status", "UNKNOWN"),
                                     "broker_confirmed": False, "replacement_submitted": False,
                                     "reason": "Legacy order cancellation was not confirmed."})
                    return {"status": "BLOCKED", "reason": f"Could not cancel legacy YarTrader pending order {ticket}: {getattr(response, 'Comment', '')}"}
                refreshed = self.adapter.get_active_orders(symbol)
                if refreshed is None or any(int(self._field(o, "ticket", 0) or 0) == ticket for o in refreshed):
                    self._log_event({"event": "pending_order_cancel_result", "symbol": symbol,
                                     "ticket": ticket, "broker_status": getattr(response, "Status", "Cancelled"),
                                     "broker_confirmed": False, "replacement_submitted": False,
                                     "reason": "Cancel response received but active broker state did not verify removal."})
                    return {"status": "BLOCKED", "reason": f"Legacy pending order {ticket} cancellation could not be verified."}
                self._log_event({"event": "pending_order_cancel_result", "symbol": symbol,
                                 "ticket": ticket, "broker_status": getattr(response, "Status", "Cancelled"),
                                 "broker_confirmed": True, "replacement_submitted": False,
                                 "reason": "Legacy order cancellation verified by refreshed broker state."})
                cancelled.append(ticket)
            return {"status": "WAIT", "reason": base_plan.get("reason", "No qualified entry proposal."),
                    "cancelled_legacy_pending_orders": cancelled}

        plan = dict(plan)
        try:
            review_state = self._load_trade_review_state()
            prior_exit = review_state["last_closed_setup_by_symbol"].get(symbol.upper(), {})
            candidate_signature = self._setup_signature(symbol, base_plan)
            if prior_exit.get("signature") and prior_exit.get("signature") == candidate_signature:
                self._log_event({"event": "reentry_blocked_identical_closed_setup", "symbol": symbol.upper(),
                                 "previous_position_id": prior_exit.get("position_id"),
                                 "previous_exit_reason": prior_exit.get("exit_reason"),
                                 "previous_pnl": prior_exit.get("pnl"), "setup_signature": candidate_signature,
                                 "reason": "A broker-confirmed closed trade cannot be re-entered using the identical strategy/structure/entry/SL/TP plan; a materially revised setup is required."})
                return {"status": "REVIEW_REQUIRED", "reason": "Identical previous setup blocked after a completed trade. The next entry requires a changed, freshly evaluated setup.",
                        "previous_exit_reason": prior_exit.get("exit_reason"), "previous_pnl": prior_exit.get("pnl")}
            direction = str(plan["direction"]).upper()
            planned_order_type = str(plan["order_type"]).upper()
            bid = float(tick.get("bid") or 0.0)
            ask = float(tick.get("ask") or 0.0)
            if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0.0 or ask < bid:
                raise ValueError("Current broker quote is invalid; market entry blocked.")
            planned_entry = float(plan.get("entry") or 0.0)
            stop = float(plan["stop_loss"])
            if not math.isfinite(planned_entry) or planned_entry <= 0.0:
                raise ValueError("Strategy proposal has no valid planned entry price.")
            # The strategy emits LIMIT/STOP setups frequently. Keep these as real
            # broker-side pending orders with server-side SL/TP and finite expiry;
            # never silently turn an untriggered setup into a market entry.
            conditional_types = {"BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"}
            pending_order = planned_order_type in conditional_types
            order_type = planned_order_type if pending_order else direction
            tick_time = int(tick.get("time") or 0)
            if tick_time <= 0:
                raise ValueError("Broker tick timestamp is missing; entry expiry cannot be enforced.")
            if pending_order:
                crossed_trigger = (
                    (planned_order_type == "BUY_LIMIT" and planned_entry >= ask)
                    or (planned_order_type == "SELL_LIMIT" and planned_entry <= bid)
                    or (planned_order_type == "BUY_STOP" and planned_entry <= ask)
                    or (planned_order_type == "SELL_STOP" and planned_entry >= bid)
                )
                planned_risk = abs(planned_entry - stop)
                current_entry = ask if direction == "BUY" else bid
                drift_r = abs(current_entry - planned_entry) / planned_risk if planned_risk > 0 else float("inf")
                if crossed_trigger:
                    if not math.isfinite(drift_r) or drift_r > self.MAX_ENTRY_DRIFT_R:
                        self._log_event({
                            "event": "entry_rejected_crossed_trigger", "symbol": symbol,
                            "strategy": strategy_name, "planned_order_type": planned_order_type,
                            "planned_entry": planned_entry, "bid": bid, "ask": ask,
                            "entry_drift_r": round(drift_r, 4) if math.isfinite(drift_r) else None,
                            "maximum_entry_drift_r": self.MAX_ENTRY_DRIFT_R,
                            "reason": "Conditional trigger crossed outside the allowed entry-drift envelope; a fresh setup is required.",
                        })
                        return {"status": "WAIT", "reason": "Conditional trigger crossed too far from its planned level; no chase entry sent."}
                    # The trigger is already crossed, but price is still within the
                    # strategy's strict drift envelope. Revalidate as a market deal.
                    pending_order = False
                    order_type = direction
                    entry = current_entry
                    self._log_event({
                        "event": "conditional_trigger_crossed_market_entry_approved", "symbol": symbol,
                        "strategy": strategy_name, "planned_order_type": planned_order_type,
                        "planned_entry": planned_entry, "current_entry": current_entry,
                        "entry_drift_r": round(drift_r, 4), "maximum_entry_drift_r": self.MAX_ENTRY_DRIFT_R,
                        "reason": "Trigger crossed within the configured drift limit; full market-entry risk/target checks still apply.",
                    })
                else:
                    entry = planned_entry
                    requested_expiration = int(float(plan.get("expires_at") or 0))
                    # Do not leave autonomous pending orders live indefinitely.
                    expires = min(requested_expiration, tick_time + 3600) if requested_expiration > tick_time else tick_time + 3600
                    self._log_event({
                        "event": "conditional_entry_pending_order_eligible", "symbol": symbol,
                        "strategy": strategy_name, "order_type": planned_order_type,
                        "planned_entry": planned_entry, "bid": bid, "ask": ask,
                        "expires_at": expires,
                        "reason": "Uncrossed qualified setup will be submitted as a broker-side pending order with protective SL/TP and a one-hour maximum lifetime.",
                    })
            else:
                if planned_order_type not in {"BUY", "SELL"}:
                    return {"status": "WAIT", "reason": f"Unsupported entry order type: {planned_order_type}; no order was sent."}
                entry = ask if direction == "BUY" else bid

            # Dual-mode execution: maintain a future broker-side level order while
            # price is away from the zone, but allow a live market entry when the
            # current quote is near the structural level and the newest completed
            # candle confirms a directional rejection. Never chase beyond MAX_ENTRY_DRIFT_R.
            entry_decision_mode = "MARKET_NOW" if not pending_order else "PENDING_FUTURE_LEVEL"
            entry_decision_reason = (
                "The strategy explicitly proposed a market direction; current quote and drift checks still apply."
                if not pending_order else
                "Price has not reached the structural entry; retain a broker-side pending order at the planned level."
            )
            live_watch = None
            if pending_order:
                live_watch = self._advance_setup_zone_watch(
                    symbol, strategy_name, plan, tick, symbol_info, per_tf
                )
                if live_watch.get("state") == "REACTION_CONFIRMED" and live_watch.get("reaction_confirmed"):
                    current_entry = ask if direction == "BUY" else bid
                    planned_risk = abs(planned_entry - stop)
                    reaction_drift_r = abs(current_entry - planned_entry) / planned_risk if planned_risk > 0 else float("inf")
                    if math.isfinite(reaction_drift_r) and reaction_drift_r <= self.MAX_ENTRY_DRIFT_R:
                        pending_order = False
                        order_type = direction
                        entry = current_entry
                        entry_decision_mode = "MARKET_AFTER_CONFIRMED_ZONE_REACTION"
                        entry_decision_reason = "Newest completed M1/M5/M15 candle confirmed rejection at the nearby structural entry; market entry remains within the strict drift envelope."
                    else:
                        entry_decision_mode = "PENDING_LEVEL_REACTION_TOO_FAR_TO_CHASE"
                        entry_decision_reason = "A zone reaction was observed, but current price is outside the permitted entry-drift envelope; keep the level order and do not chase."
                elif live_watch.get("state") == "NEAR_ZONE":
                    entry_decision_mode = "PENDING_AT_LEVEL_AWAITING_REACTION"
                    entry_decision_reason = "Price is near the structural entry but no completed-candle rejection is confirmed yet; leave the broker-side order at the planned level and do not force a market entry."

            structure_for_decision = base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {}
            self._log_event({
                "event": "live_entry_context_decision", "symbol": symbol,
                "strategy": strategy_name, "direction": direction,
                "decision_mode": entry_decision_mode, "decision_reason": entry_decision_reason,
                "planned_order_type": planned_order_type, "execution_order_type": order_type,
                "planned_entry": planned_entry, "execution_entry": entry,
                "bid": bid, "ask": ask, "mid": (bid + ask) / 2.0,
                "distance_to_entry": abs(((bid + ask) / 2.0) - planned_entry),
                "watch_state": (live_watch or {}).get("state"),
                "reaction_confirmed": bool((live_watch or {}).get("reaction_confirmed", False)),
                "reaction_evidence": (live_watch or {}).get("reaction_evidence"),
                "entry_drift_r": round(abs(entry - planned_entry) / abs(planned_entry - stop), 4) if abs(planned_entry - stop) > 0 else None,
                "parent_base_id": structure_for_decision.get("parent_base_id"),
                "child_base_id": structure_for_decision.get("child_base_id"),
                "execution_candidate_qualified": True,
                "broker_confirmed": False,
                "broker_order_submission_enabled": True,
                "live_trading_enabled": False,
            })
            planned_risk_distance = abs(planned_entry - stop)
            if not math.isfinite(planned_risk_distance) or planned_risk_distance <= 0.0:
                raise ValueError("Strategy proposal has no valid planned entry-to-stop distance.")
            expires_at = plan.get("expires_at")
            if expires_at is not None and tick_time > 0 and tick_time >= int(expires_at):
                return {"status": "WAIT", "reason": "Entry proposal expired before execution; no stale order was sent."}
            if not pending_order:
                # Market entries are allowed only while still near the planned level.
                entry_drift_r = abs(entry - planned_entry) / planned_risk_distance
                if entry_drift_r > self.MAX_ENTRY_DRIFT_R:
                    self._log_event({
                        "event": "entry_rejected_excessive_drift", "symbol": symbol,
                        "strategy": strategy_name, "direction": direction,
                        "planned_entry": planned_entry, "current_entry": entry,
                        "planned_stop_loss": stop, "entry_drift_r": round(entry_drift_r, 4),
                        "maximum_entry_drift_r": self.MAX_ENTRY_DRIFT_R,
                        "reason": "Price moved too far from the planned structural entry; wait for a fresh setup instead of chasing.",
                    })
                    return {"status": "WAIT", "reason": (
                        f"Price moved {entry_drift_r:.2f}R from the planned entry; "
                        f"maximum allowed drift is {self.MAX_ENTRY_DRIFT_R:.2f}R. Wait for a fresh setup; no chase entry sent."
                    ), "entry_drift_r": round(entry_drift_r, 4)}
            original_stop = stop
            target = float(plan.get("take_profit") or 0.0)
            spread_now = max(0.0, float(tick.get("ask", 0.0)) - float(tick.get("bid", 0.0)))
            if per_tf is not None:
                # Do not let a tiny M1/M5 Base define the entire stop distance.
                # Use only completed bars and widen beyond both structure invalidation
                # and a volatility floor derived from M5/M15 ATR.
                atr_values = []
                quote_time = float(tick.get("time") or time.time())
                for atr_tf in ("M5", "M15"):
                    rows = [
                        row for row in per_tf.get(atr_tf, [])
                        if float(row.get("timestamp", row.get("time", 0)) or 0) <= quote_time
                    ]
                    if len(rows) < 15:
                        continue
                    true_ranges = []
                    for index in range(max(1, len(rows) - 14), len(rows)):
                        row, previous = rows[index], rows[index - 1]
                        try:
                            high = float(row["high"]); low = float(row["low"])
                            previous_close = float(previous["close"])
                            true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
                        except (KeyError, TypeError, ValueError):
                            continue
                    if true_ranges and all(math.isfinite(value) and value > 0 for value in true_ranges):
                        atr_values.append((atr_tf, sum(true_ranges) / len(true_ranges)))
                if not atr_values:
                    return {"status": "BLOCKED", "reason": "Cannot validate a volatility-aware protective stop without closed M5/M15 ATR data."}
                volatility_floor = max(
                    [1.5 * value if tf == "M5" else 0.75 * value for tf, value in atr_values]
                    + [2.0 * spread_now]
                )
                structural_risk = entry - stop if direction == "BUY" else stop - entry
                if structural_risk < volatility_floor:
                    # The child Base's own edge can be too close for current volatility.
                    # In that case, select the nearest confirmed parent/intermediate Base
                    # boundary that genuinely invalidates the setup and clears the floor.
                    # Never manufacture a wider stop by multiplying ATR or adding fixed pips.
                    structure = base_plan.get("structure") or {}
                    chain = structure.get("hierarchy_chain") or []
                    if not chain:
                        reaction = base_plan.get("reaction_analysis") or {}
                        scenario = reaction.get("scenario") or {}
                        chain = scenario.get("hierarchy_chain") or []
                    spread_buffer = max(2.0 * spread_now, 1e-8)
                    max_stop_distance = self.MAX_STOP_ATR_MULTIPLE * max(value for _, value in atr_values)
                    candidates = []
                    for node in chain:
                        if str(node.get("role", "")).upper() not in ("MOTHER", "INTERMEDIATE_BASE"):
                            continue
                        try:
                            boundary = float(node["base_low"] if direction == "BUY" else node["base_high"])
                            candidate_stop = boundary - spread_buffer if direction == "BUY" else boundary + spread_buffer
                            candidate_risk = entry - candidate_stop if direction == "BUY" else candidate_stop - entry
                        except (KeyError, TypeError, ValueError, OverflowError):
                            continue
                        if (math.isfinite(candidate_stop) and candidate_risk >= volatility_floor
                                and candidate_risk > 0 and candidate_risk <= max_stop_distance):
                            candidates.append((candidate_risk, candidate_stop, str(node.get("timeframe", "")),
                                               str(node.get("event_id", ""))))
                    if candidates:
                        _, stop, stop_timeframe, stop_event_id = min(candidates, key=lambda item: item[0])
                        structural_risk = entry - stop if direction == "BUY" else stop - entry
                        plan["stop_loss"] = stop
                        self._log_event({
                            "event": "structural_stop_promoted_to_parent_boundary",
                            "symbol": symbol, "direction": direction, "entry": entry,
                            "old_stop_loss": original_stop,
                            "new_stop_loss": stop, "stop_timeframe": stop_timeframe,
                            "stop_event_id": stop_event_id, "volatility_floor": volatility_floor,
                            "risk_distance": structural_risk,
                        })
                    else:
                        # If no confirmed parent boundary is available, preserve the
                        # child-Base invalidation but place the protective stop farther
                        # beyond it to clear the measured volatility floor. Position
                        # sizing is then recalculated from this wider stop; never keep
                        # an unrealistically tight stop just to manufacture a trade.
                        stop = entry - volatility_floor if direction == "BUY" else entry + volatility_floor
                        structural_risk = entry - stop if direction == "BUY" else stop - entry
                        plan["stop_loss"] = stop
                        self._log_event({
                            "event": "structural_stop_extended_to_volatility_floor",
                            "symbol": symbol, "strategy": strategy_name, "direction": direction,
                            "entry": entry, "old_stop_loss": original_stop,
                            "new_stop_loss": stop, "volatility_floor": volatility_floor,
                            "risk_distance": structural_risk,
                            "reason": "No parent boundary cleared the volatility floor; stop was extended beyond the original structural invalidation and lot size will be reduced to remain within the DEMO risk budget.",
                        })
                # Structural stops must be valid in both directions: not so tight
                # that normal volatility hits them, and not so wide that a distant
                # parent Base creates an oversized risk distance. If no confirmed
                # structure fits the volatility envelope, reject instead of widening.
                max_stop_distance = self.MAX_STOP_ATR_MULTIPLE * max(value for _, value in atr_values)
                final_stop_distance = entry - stop if direction == "BUY" else stop - entry
                if (not math.isfinite(final_stop_distance) or final_stop_distance <= 0
                        or final_stop_distance > max_stop_distance):
                    return {"status": "BLOCKED", "reason": (
                        f"Structural stop is too wide for current volatility ({final_stop_distance:.5f} > "
                        f"{max_stop_distance:.5f}, {self.MAX_STOP_ATR_MULTIPLE:.1f}x ATR); "
                        "YarTrader refuses oversized-stop entries instead of moving the stop farther away."
                    )}
                # The stop remains the selected structural invalidation; ATR only
                # bounds acceptable distance and never fabricates a stop price.
                plan["stop_loss"] = stop
            if not pending_order:
                expires = None
            digits = int(symbol_info["digits"])
            if direction not in ("BUY", "SELL") or planned_order_type not in ("BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP", "BUY", "SELL"):
                raise ValueError("Unsupported strategy direction or entry plan.")
            if not all(math.isfinite(x) and x > 0 for x in (entry, stop)):
                raise ValueError("Base plan contains invalid entry or protective stop.")
            if (direction == "BUY" and not stop < entry) or (direction == "SELL" and not entry < stop):
                raise ValueError("Market entry has invalid protective-stop geometry.")
            risk_distance = abs(entry - stop)
            analytical_scenario = (base_plan.get("reaction_analysis") or {}).get("scenario") or {}
            if not analytical_scenario:
                analytical_scenario = (base_plan.get("hierarchy") or {}).get("scenario") or {}
            try:
                target_value = analytical_scenario.get("target")
                if target_value is None:
                    # Some independent strategies publish a validated research target
                    # in strategy_results rather than reaction_analysis.scenario.
                    # Use it only as an analytical candidate; the execution core still
                    # checks direction, costs, net R:R, and position risk below.
                    target_value = self._planned_target(base_plan)
                analytical_target = float(target_value)
                if not math.isfinite(analytical_target) or analytical_target <= 0:
                    raise ValueError("A valid structural or strategy-analysis target is required for YarTrader's own net R:R check.")
                reward_distance = (analytical_target - entry if direction == "BUY" else entry - analytical_target)
                if reward_distance <= 0 or risk_distance <= 0:
                    raise ValueError("Target must be on the profitable side of entry and stop distance must be positive.")
                contract_size = float(symbol_info.get("trade_contract_size") or symbol_info.get("contract_size")
                                      or ProfessionalRiskEngine().get_contract_size(symbol, entry))
                if not math.isfinite(contract_size) or contract_size <= 0:
                    raise ValueError("Broker contract size is unavailable for transaction-cost calculation.")
                # YarTrader execution core owns this calculation. Use live spread,
                # a conservative slippage allowance, and round-trip commission converted
                # into price distance; never trust an upstream plan's precomputed R:R.
                slippage_allowance = spread_now * 0.5
                commission_allowance = (2.0 * self.ESTIMATED_COMMISSION_PER_LOT_USD) / contract_size
                cost_allowance = spread_now + slippage_allowance + commission_allowance
                gross_rr = reward_distance / risk_distance
                net_rr = max(0.0, reward_distance - cost_allowance) / (risk_distance + cost_allowance)
                plan["gross_reward_risk"] = round(gross_rr, 4)
                plan["net_reward_risk"] = round(net_rr, 4)
                plan["transaction_cost_allowance"] = round(cost_allowance, 8)
                plan["rr_calculated_by"] = "YarTrader.execution_core"
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"YarTrader cannot independently validate net R:R: {exc}") from exc
            min_net_rr = self._minimum_net_rr_for_plan(base_plan)
            # If the structural SL was widened for volatility and the nearest TP no
            # longer pays for that risk, promote TP to the nearest farther, confirmed
            # structural Base that still clears net R:R after estimated costs. Never
            # invent a farther price just to force an entry.
            if net_rr <= min_net_rr:
                reaction_targets = (base_plan.get("reaction_analysis") or {}).get("structural_target_candidates") or []
                if not reaction_targets:
                    reaction_targets = ((base_plan.get("hierarchy") or {}).get("reaction_analysis") or {}).get("structural_target_candidates") or []
                selected_target = self._best_structural_target_for_net_rr(
                    reaction_targets, direction, entry, risk_distance, cost_allowance,
                    min_net_rr, float(tick.get("time") or time.time()),
                )
                if selected_target:
                    old_target = analytical_target
                    analytical_target, target_evidence, net_rr = selected_target
                    reward_distance = analytical_target - entry if direction == "BUY" else entry - analytical_target
                    gross_rr = reward_distance / risk_distance
                    plan["gross_reward_risk"] = round(gross_rr, 4)
                    plan["net_reward_risk"] = round(net_rr, 4)
                    plan["take_profit"] = analytical_target
                    base_plan["take_profit_target_evidence"] = target_evidence
                    self._log_event({
                        "event": "structural_take_profit_promoted_to_next_base", "symbol": symbol,
                        "strategy": strategy_name, "direction": direction, "entry": entry,
                        "old_take_profit": old_target, "new_take_profit": analytical_target,
                        "target_timeframe": target_evidence.get("timeframe"),
                        "target_event_id": target_evidence.get("event_id"),
                        "gross_reward_risk": round(gross_rr, 4), "net_reward_risk": round(net_rr, 4),
                        "stop_loss": stop, "reason": "Nearest TP no longer cleared the net-R:R floor after final structural stop validation; selected the nearest farther confirmed Base.",
                        "base_plan": base_plan,
                    })
            if min_net_rr < self.MIN_RR:
                self._log_event({
                    "event": "demo_exploration_rr_floor_applied", "symbol": symbol,
                    "strategy": strategy_name, "net_reward_risk": round(net_rr, 4),
                    "standard_minimum_net_rr": float(self.MIN_RR),
                    "exploration_minimum_net_rr": min_net_rr,
                    "reason": "Lower R:R floor applies only to DEMO_STYLE_DISCOVERY while autonomous DEMO is enabled and LIVE trading is disabled; normal risk sizing and broker-side SL/TP remain required.",
                })
            if (risk_distance <= 0 or not math.isfinite(net_rr) or net_rr <= min_net_rr):
                raise ValueError(
                    f"YarTrader blocks this order: net R:R {net_rr:.4f} must be strictly greater than "
                    f"{min_net_rr:.2f} after spread, slippage, and commission."
                )
            # Every new DEMO entry must carry a broker-side protective TP as well
            # as the structural SL. The analytical target is accepted only after
            # direction, costs, and net reward/risk have been validated above.
            target = analytical_target
            plan["take_profit"] = target
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            return {"status": "BLOCKED", "reason": f"Invalid Base pending order plan: {exc}"}

        # An ambiguous/partial broker response is a durable stop for new entries
        # on this symbol until a human reconciles the broker state. Existing position
        # management runs earlier and remains available; do not auto-clear this lock.
        if type(self.adapter) is RealMT5BrokerAdapter:
            symbol_key = symbol.upper()
            if symbol_key in getattr(self, "_unresolved_execution_symbols", set()):
                return {"status": "BLOCKED_UNRESOLVED_EXECUTION",
                        "reason": "A previous broker submission has unresolved status; reconcile it manually before another entry."}
            review_state = self._load_trade_review_state()
            unresolved_orders = review_state.get("unresolved_order_by_symbol", {})
            if symbol_key in unresolved_orders:
                self._unresolved_execution_symbols = set(getattr(self, "_unresolved_execution_symbols", set())) | {symbol_key}
                return {"status": "BLOCKED_UNRESOLVED_EXECUTION",
                        "reason": "A persisted unresolved broker submission exists for this symbol; reconcile it manually before another entry."}

        # Reconcile only this strategy's own pending order. Keep other strategy
        # slots independent; never cancel a different strategy's valid setup.
        strategy_owned = [
            order for order in owned
            if str(self._field(order, "comment", "") or "").strip() == strategy_comment
            or _legacy_strategy_comment_matches(
                str(self._field(order, "comment", "") or ""), strategy_name
            )
        ]
        if pending_order:
            expected_type = getattr(mt5, f"ORDER_TYPE_{planned_order_type}", None)
            point = float(symbol_info.get("point") or 0.0)
            if point <= 0 or expected_type is None:
                return {"status": "BLOCKED", "reason": "Broker point size or pending order type is unavailable for duplicate-safe order reconciliation."}
            bid = float((tick or {}).get("bid") or 0.0)
            ask = float((tick or {}).get("ask") or 0.0)
            spread = max(0.0, ask - bid) if bid > 0 and ask > 0 else 0.0
            for order in strategy_owned:
                same, entry_tolerance, protection_tolerance, target_tolerance = _pending_order_matches_current_plan(
                    order, int(expected_type), entry, stop, target, point, spread, direction=direction
                )
                order_entry = float(self._field(order, "price_open", 0.0) or 0.0)
                order_sl = float(self._field(order, "sl", 0.0) or 0.0)
                order_tp = float(self._field(order, "tp", 0.0) or 0.0)
                if same:
                    ticket = int(self._field(order, "ticket", 0) or 0)
                    self._log_event({
                        "event": "pending_order_review", "symbol": symbol,
                        "strategy": strategy_name, "ticket": ticket,
                        "review_decision": "KEEP_EXISTING",
                        "broker_entry": order_entry, "proposed_entry": entry,
                        "broker_stop_loss": order_sl, "proposed_stop_loss": stop,
                        "broker_take_profit": order_tp, "proposed_take_profit": target,
                        "entry_tolerance": entry_tolerance,
                        "stop_tolerance": protection_tolerance,
                        "target_tolerance": target_tolerance,
                        "reason": "Existing broker order still matches the current setup within risk-aware price tolerance; no cancel/re-submit churn.",
                        "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                        "entry_level_context": base_plan.get("entry_level_context") or {},
                    })
                    redundant_cancelled = []
                    for duplicate in strategy_owned:
                        duplicate_ticket = int(self._field(duplicate, "ticket", 0) or 0)
                        if duplicate_ticket <= 0 or duplicate_ticket == ticket:
                            continue
                        self._log_event({
                            "event": "pending_order_review", "symbol": symbol,
                            "strategy": strategy_name, "ticket": duplicate_ticket,
                            "kept_ticket": ticket, "review_decision": "CANCEL_REDUNDANT_SAME_STRATEGY_ORDER",
                            "reason": "One strategy may reserve only one broker-side pending-order slot; keeping the order that matches the current setup.",
                        })
                        cancel_result = self.adapter.cancel_pending_order(duplicate_ticket)
                        if getattr(cancel_result, "Status", "") != "Cancelled":
                            self._log_event({
                                "event": "pending_order_cancel_result", "symbol": symbol,
                                "strategy": strategy_name, "ticket": duplicate_ticket,
                                "broker_status": getattr(cancel_result, "Status", "UNKNOWN"),
                                "broker_confirmed": False, "replacement_submitted": False,
                                "reason": "Redundant same-strategy order could not be cancelled; no additional order submitted.",
                            })
                            return {"status": "BLOCKED", "reason": f"Could not cancel redundant same-strategy pending order {duplicate_ticket}."}
                        refreshed = self.adapter.get_active_orders(symbol)
                        if refreshed is None or any(int(self._field(o, "ticket", 0) or 0) == duplicate_ticket for o in refreshed):
                            self._log_event({
                                "event": "pending_order_cancel_result", "symbol": symbol,
                                "strategy": strategy_name, "ticket": duplicate_ticket,
                                "broker_status": getattr(cancel_result, "Status", "Cancelled"),
                                "broker_confirmed": False, "replacement_submitted": False,
                                "reason": "Cancel response received but broker state did not verify duplicate removal.",
                            })
                            return {"status": "BLOCKED", "reason": f"Redundant pending order {duplicate_ticket} cancellation could not be verified."}
                        self._log_event({
                            "event": "pending_order_cancel_result", "symbol": symbol,
                            "strategy": strategy_name, "ticket": duplicate_ticket,
                            "broker_status": getattr(cancel_result, "Status", "Cancelled"),
                            "broker_confirmed": True, "replacement_submitted": False,
                            "reason": f"Redundant same-strategy order removed; matching order {ticket} retained.",
                        })
                        redundant_cancelled.append(duplicate_ticket)
                    return {"status": "PENDING_ORDER_ACTIVE", "symbol": symbol,
                            "ticket": ticket, "order_type": planned_order_type,
                            "entry": order_entry, "stop_loss": order_sl, "take_profit": order_tp,
                            "cancelled_redundant_tickets": redundant_cancelled,
                            "reason": "Existing broker-side pending order remains valid within the current structural price tolerance; duplicate submission suppressed."}
        # Do not cancel a current order yet. First validate the replacement's
        # volume/risk budget; otherwise a rejected replacement would erase a
        # still-valid broker-side order and the next cycle could churn again.

        # No exploration or strategy mode may bypass wallet-based risk sizing.
        # Use the fresh account snapshot and broker-native PnL calculation for
        # every new autonomous entry; reject when broker minimum exceeds budget.
        # Budget against actual/configured concurrent DEMO slots, not every
        # strategy that merely proposed a setup. Unselected candidates must not
        # dilute the selected entry's risk budget into an untradeable minimum lot.
        risk_slot_count = max(1, int(base_plan.get("max_demo_slots") or 1))
        occupied_strategy_names = base_plan.get("occupied_strategy_slots") or []
        from src.Execution.Services.strategy_risk_allocator import allocate_demo_slot_risk_pct
        allocation = allocate_demo_slot_risk_pct(
            occupied_strategy_names, strategy_name, risk_slot_count,
            float(ProductionRiskPolicy.TARGET_RISK_PCT),
        )
        allocated_risk_pct = float(allocation["risk_pct"])
        try:
            sizing = calculate_demo_volume_by_risk(
                mt5, symbol, direction, entry, stop, symbol_info,
                float(account.get("balance") or 0), float(account.get("equity") or 0),
                allocated_risk_pct, allow_portfolio_allocation=True,
            )
        except (ValidationException, ValueError, TypeError, KeyError) as exc:
            self._log_event({
                "event": "entry_blocked_invalid_risk_sizing_facts", "symbol": symbol,
                "strategy": strategy_name, "direction": direction,
                "planned_entry": planned_entry, "current_entry": entry, "stop_loss": stop,
                "reason": str(exc),
            })
            return {"status": "RISK_BLOCKED", "reason": f"Risk sizing could not be verified: {exc}"}
        sizing["strategy_allocation"] = allocation
        if not sizing.get("allowed"):
            self._log_event({
                "event": "pending_order_review", "symbol": symbol,
                "strategy": strategy_name,
                "review_decision": "KEEP_EXISTING_RISK_BLOCKED_REPLACEMENT",
                "existing_tickets": [int(self._field(o, "ticket", 0) or 0) for o in strategy_owned],
                "reason": sizing.get("reason") or "Replacement sizing failed; existing order was not cancelled.",
                "risk": sizing,
                "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                "entry_level_context": base_plan.get("entry_level_context") or {},
            })
            return {"status": "RISK_BLOCKED", "reason": sizing.get("reason"), "risk": sizing}

        # If an existing order differs only by a small stop/target recalculation,
        # keep it when its actual broker-calculated loss remains within this cycle's
        # allocated dollar-risk budget. This prevents harmless candle-to-candle
        # rounding drift from repeatedly cancelling and re-creating a valid order.
        if pending_order and strategy_owned:
            point_for_review = float(symbol_info.get("point") or 0.0)
            bid_for_review = float((tick or {}).get("bid") or 0.0)
            ask_for_review = float((tick or {}).get("ask") or 0.0)
            spread_for_review = max(0.0, ask_for_review - bid_for_review)
            entry_tol_for_review = max(point_for_review * 10.0, spread_for_review * 3.0, abs(entry) * 0.0001)
            planned_risk_distance = abs(entry - stop)
            stop_tol_for_review = max(point_for_review * 20.0, planned_risk_distance * 0.10, abs(stop) * 0.0001)
            expected_pending_type = getattr(mt5, f"ORDER_TYPE_{planned_order_type}", None)
            risk_order_type = getattr(mt5, f"ORDER_TYPE_{direction}", None)
            risk_budget = float(sizing.get("risk_budget_usd") or 0.0)
            for existing_order in strategy_owned:
                try:
                    existing_ticket = int(self._field(existing_order, "ticket", 0) or 0)
                    existing_type = int(self._field(existing_order, "type", -1))
                    existing_entry = float(self._field(existing_order, "price_open", 0.0) or 0.0)
                    existing_sl = float(self._field(existing_order, "sl", 0.0) or 0.0)
                    existing_tp = float(self._field(existing_order, "tp", 0.0) or 0.0)
                    existing_volume = float(self._field(
                        existing_order, "volume_current", self._field(existing_order, "volume_initial", 0.0)
                    ) or 0.0)
                    target_is_valid = (
                        direction == "BUY" and existing_tp > existing_entry
                    ) or (direction == "SELL" and 0.0 < existing_tp < existing_entry)
                    target_within_review = abs(existing_tp - target) <= max(
                        point_for_review * 10.0, spread_for_review * 3.0,
                        abs(target) * 0.0001, planned_risk_distance,
                    )
                    stop_within_review = abs(existing_sl - stop) <= stop_tol_for_review
                    entry_within_review = abs(existing_entry - entry) <= entry_tol_for_review
                    if not (existing_ticket > 0 and existing_type == int(expected_pending_type)
                            and existing_volume > 0 and existing_entry > 0 and existing_sl > 0 and existing_tp > 0
                            and target_is_valid and target_within_review
                            and stop_within_review and entry_within_review
                            and risk_budget > 0 and risk_order_type is not None):
                        continue
                    current_loss = mt5.order_calc_profit(
                        int(risk_order_type), symbol, existing_volume, existing_entry, existing_sl
                    )
                    if current_loss is None or not math.isfinite(float(current_loss)):
                        continue
                    current_risk_usd = abs(float(current_loss))
                    if current_risk_usd > risk_budget + 1e-6:
                        continue
                    self._log_event({
                        "event": "pending_order_review", "symbol": symbol,
                        "strategy": strategy_name, "ticket": existing_ticket,
                        "review_decision": "KEEP_EXISTING_WITHIN_RISK_BUDGET",
                        "broker_entry": existing_entry, "proposed_entry": entry,
                        "broker_stop_loss": existing_sl, "proposed_stop_loss": stop,
                        "broker_take_profit": existing_tp, "proposed_take_profit": target,
                        "actual_broker_risk_usd": current_risk_usd,
                        "allocated_risk_budget_usd": risk_budget,
                        "stop_review_tolerance": stop_tol_for_review,
                        "target_review_tolerance": max(point_for_review * 10.0, spread_for_review * 3.0,
                                                        abs(target) * 0.0001, planned_risk_distance),
                        "reason": "Existing order's actual broker-calculated loss remains within the allocated risk budget; retaining it avoids cancel/re-submit churn.",
                        "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                        "entry_level_context": base_plan.get("entry_level_context") or {},
                    })
                    return {"status": "PENDING_ORDER_ACTIVE", "symbol": symbol,
                            "ticket": existing_ticket, "order_type": planned_order_type,
                            "entry": existing_entry, "stop_loss": existing_sl, "take_profit": existing_tp,
                            "actual_broker_risk_usd": current_risk_usd, "risk_budget_usd": risk_budget,
                            "reason": "Existing pending order remains within the current structural review tolerances and allocated dollar-risk budget."}
                except (TypeError, ValueError, OverflowError, AttributeError):
                    continue

        # Replace only after the candidate has passed structural, RR and risk
        # sizing gates. Confirm each cancellation and refresh broker state before
        # sending the replacement; never submit into an unknown order state.
        replaced_tickets: List[int] = []
        for order in strategy_owned:
            ticket = int(self._field(order, "ticket", 0) or 0)
            if ticket <= 0:
                return {"status": "BLOCKED", "reason": "YarTrader-owned pending order has no valid ticket; replacement was not sent."}
            self._log_event({
                "event": "pending_order_review", "symbol": symbol,
                "strategy": strategy_name, "ticket": ticket,
                "review_decision": "REPLACE_AFTER_VALIDATED_CANDIDATE",
                "broker_entry": float(self._field(order, "price_open", 0.0) or 0.0),
                "proposed_entry": entry, "broker_stop_loss": float(self._field(order, "sl", 0.0) or 0.0),
                "proposed_stop_loss": stop, "broker_take_profit": float(self._field(order, "tp", 0.0) or 0.0),
                "proposed_take_profit": target, "risk": sizing,
                "reason": "Current candidate passed risk sizing and materially differs from the existing pending order.",
                "base_plan": base_plan,
            })
            response = self.adapter.cancel_pending_order(ticket)
            if getattr(response, "Status", "") != "Cancelled":
                self._log_event({
                    "event": "pending_order_cancel_result", "symbol": symbol,
                    "strategy": strategy_name, "ticket": ticket,
                    "broker_status": getattr(response, "Status", "UNKNOWN"),
                    "broker_comment": getattr(response, "Comment", ""),
                    "broker_confirmed": False, "replacement_submitted": False,
                    "reason": "Broker did not confirm cancellation; replacement blocked.",
                })
                return {"status": "BLOCKED", "reason": f"Could not replace prior strategy pending order {ticket}: {getattr(response, 'Comment', '')}"}
            refreshed = self.adapter.get_active_orders(symbol)
            if refreshed is None or any(int(self._field(o, "ticket", 0) or 0) == ticket for o in refreshed):
                self._log_event({
                    "event": "pending_order_cancel_result", "symbol": symbol,
                    "strategy": strategy_name, "ticket": ticket,
                    "broker_status": getattr(response, "Status", "Cancelled"),
                    "broker_confirmed": False, "replacement_submitted": False,
                    "reason": "Cancellation response was received but refreshed broker state is unknown or still contains the order.",
                })
                return {"status": "BLOCKED", "reason": f"Pending order {ticket} cancellation could not be verified; replacement blocked."}
            self._log_event({
                "event": "pending_order_cancel_result", "symbol": symbol,
                "strategy": strategy_name, "ticket": ticket,
                "broker_status": getattr(response, "Status", "Cancelled"),
                "broker_comment": getattr(response, "Comment", ""),
                "broker_confirmed": True, "replacement_submitted": False,
                "reason": "Order cancellation verified by refreshed broker state; replacement may now be submitted.",
            })
            replaced_tickets.append(ticket)

        request = OrderRequest(
            Symbol=symbol, OrderType=order_type, Volume=float(sizing["volume"]),
            Price=round(entry, digits), StopLoss=round(stop, digits), TakeProfit=round(target, digits),
            Comment=strategy_comment, Magic=100001, Expiration=expires, RiskPct=allocated_risk_pct,
        )
        response = self.adapter.send_order_to_broker(request)
        if getattr(response, "Status", "") in {"Partial", "Uncertain"}:
            symbol_key = symbol.upper()
            self._unresolved_execution_symbols = set(getattr(self, "_unresolved_execution_symbols", set())) | {symbol_key}
            if type(self.adapter) is RealMT5BrokerAdapter:
                try:
                    review_state = self._load_trade_review_state()
                    review_state.setdefault("unresolved_order_by_symbol", {})[symbol_key] = {
                        "order_id": str(getattr(response, "OrderId", "") or ""),
                        "deal_ticket": str(getattr(response, "DealTicket", "") or ""),
                        "retcode": getattr(response, "Retcode", None),
                        "status": str(getattr(response, "Status", "Uncertain")),
                        "comment": str(getattr(response, "Comment", ""))[:300],
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "resolution": "MANUAL_BROKER_RECONCILIATION_REQUIRED",
                    }
                    self._save_trade_review_state(review_state)
                except Exception:
                    # Keep the in-process fail-closed lock even if durable persistence fails.
                    logger.exception("Could not persist unresolved execution lock for %s", symbol_key)
            self._log_event({
                "event": "execution_reconciliation_required", "symbol": symbol_key,
                "status": getattr(response, "Status", "Uncertain"),
                "order_id": str(getattr(response, "OrderId", "") or ""),
                "deal_ticket": str(getattr(response, "DealTicket", "") or ""),
                "retcode": getattr(response, "Retcode", None),
                "new_entries_blocked": True,
            })
        deal_ticket = getattr(response, "DealTicket", None)
        structure = base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {}
        event_name = "strategy_pending_order_submission" if pending_order else "strategy_market_deal_submission"
        self._log_event({
            "event": event_name, "trade_type": "DEMO", "symbol": symbol,
            "strategy": strategy_name, "strategy_style": strategy_name, "direction": direction,
            "order_type": order_type, "planned_entry": planned_entry, "entry": round(entry, digits),
            "stop_loss": round(stop, digits), "take_profit": round(target, digits),
            "take_profit_source": "CONFIRMED_STRUCTURAL_BASE" if base_plan.get("take_profit_target_evidence")
                else (base_plan.get("reaction_analysis") or {}).get("target_source") or "STRATEGY_ANALYTICAL_TARGET",
            "take_profit_timeframe": (base_plan.get("take_profit_target_evidence") or {}).get("timeframe")
                or (base_plan.get("reaction_analysis") or {}).get("target_timeframe"),
            "take_profit_event_id": (base_plan.get("take_profit_target_evidence") or {}).get("event_id")
                or (base_plan.get("reaction_analysis") or {}).get("target_event_id"),
            "gross_reward_risk": plan.get("gross_reward_risk"), "net_reward_risk": plan.get("net_reward_risk"),
            "volume": float(sizing["volume"]), "confidence": base_plan.get("confidence"),
            "entry_qualification_net_rr": net_rr,
            "decision_timeframe": "MULTI_TIMEFRAME",
            "setup_timeframe": structure.get("child_timeframe") or structure.get("selected_child_timeframe") or "UNKNOWN",
            "entry_timeframe": structure.get("micro_timeframe") or "M1",
            "execution_timeframe": "M1", "context_timeframes": structure.get("hierarchy_timeframes_considered") or [],
            "exit_policy": "broker_protective_initial_TP_with_strategy_managed_target_extension",
            "expiration": expires, "risk": sizing, "base_plan": base_plan,
            "broker_status": response.Status, "broker_comment": getattr(response, "Comment", ""),
            "broker_order_id": response.OrderId, "broker_deal_ticket": deal_ticket,
            "broker_retcode": response.Retcode,
            "replaces_broker_tickets": replaced_tickets,
        })
        if replaced_tickets:
            self._log_event({
                "event": "pending_order_replacement_completed", "symbol": symbol,
                "strategy": strategy_name, "replaced_tickets": replaced_tickets,
                "new_broker_order_id": response.OrderId,
                "broker_status": response.Status, "broker_retcode": response.Retcode,
                "broker_confirmed": response.Status == "Placed",
                "replacement_status": "REPLACED" if response.Status == "Placed" else "REPLACEMENT_FAILED",
                "reason": getattr(response, "Comment", ""),
                "base_plan": base_plan,
            })
        if response.Status == "Placed" and not pending_order:
            self._remember_submitted_setup(symbol, base_plan, plan, response)
        if response.Status in {"Partial", "Uncertain"}:
            result_status = "EXECUTION_UNCERTAIN"
        elif response.Status != "Placed":
            result_status = "ORDER_FAILED"
        elif pending_order:
            result_status = "PENDING_ORDER_SUBMITTED"
        else:
            result_status = "MARKET_OPENED" if deal_ticket else "MARKET_SUBMITTED"
        return {"status": result_status, "ticket": response.OrderId, "deal_ticket": deal_ticket,
                "broker_status": response.Status, "reason": response.Comment,
                "risk": sizing, "order_type": order_type, "entry": entry,
                "stop_loss": round(stop, digits), "take_profit": round(target, digits),
                "volume": float(sizing["volume"]), "broker_retcode": response.Retcode,
                "expires_at": expires if pending_order else None}

    def run_once(self, symbol_override: Optional[str] = None) -> Dict[str, Any]:
        """Run one read/decide/execute cycle for a selected enabled symbol."""
        if not _read_flag():
            return {"status": "DISABLED", "reason": "Explicit DEMO auto-trading opt-in is disabled."}

        symbol = str(symbol_override or os.environ.get("YARTRADER_MT5_SYMBOL", "XAUUSD")).strip().upper()
        market_gate = MarketSessionEngine.live_activity_status(symbol)
        if not market_gate.get("allowed"):
            # Do not initialize MT5, fetch ticks/candles, run learning/research, or write
            # runtime journals while the instrument's market is closed. Historical
            # backtests use their own data timeline and are deliberately unaffected.
            return {
                "status": "MARKET_CLOSED" if market_gate.get("state") != "UNKNOWN" else "BLOCKED",
                "symbol": symbol,
                "reason": market_gate.get("reason", "MARKET_NOT_OPEN"),
                "market_calendar": market_gate,
                "execution_enabled": False,
                "data_collection_enabled": False,
                "backtest_allowed": True,
            }

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

            symbol_info = self.adapter.get_symbol_info(symbol)
            tick = self.adapter.get_symbol_tick(symbol)
            if not symbol_info or not tick or float(tick.get("bid") or 0) <= 0 or float(tick.get("ask") or 0) <= 0:
                raise ValidationException(f"Valid live quote and symbol contract are unavailable for {symbol}.")

            # Keep observing the market after broker-side SL/TP exits so post-exit
            # continuation becomes durable evidence for entry/exit review.
            self._track_post_exit_market_path(symbol, tick)

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
            # Multiple positions are normally unsafe. The only supported two-position
            # state is a confirmed YarTrader-owned hedge during an actual reversal.
            # Validate ownership/directions after the fresh Base plan is evaluated below.
            allow_multiple_positions = _demo_config_value(
                "YARTRADER_DEMO_ALLOW_MULTIPLE_POSITIONS", "false"
            ).strip().lower() in {"1", "true", "yes", "on"}
            if allow_multiple_positions:
                try:
                    configured_max_positions = int(_demo_config_value(
                        "YARTRADER_DEMO_MAX_POSITIONS_PER_SYMBOL", "3"
                    ))
                except (TypeError, ValueError):
                    raise ValidationException("Invalid DEMO multi-position limit configuration.")
                if configured_max_positions < 1 or configured_max_positions > 10:
                    raise ValidationException("DEMO multi-position limit must be between 1 and 10.")
                if len(positions) > configured_max_positions:
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": f"More open positions than the configured per-symbol limit ({configured_max_positions}); manual reconciliation required."}
            elif len(positions) > 2:
                return {"status": "BLOCKED", "symbol": symbol, "reason": "More than two positions exist while multi-position mode is disabled; manual reconciliation required."}
            open_positions = positions
            self._sync_strategy_learning(symbol, open_positions, tick_time)

            # MT5 position 0 is the still-forming candle. Use it only for quote
            # freshness checks; strategy decisions must use fully closed candles.
            # _fetch_candles starts at MT5 shift=1, so every returned row is
            # already a fully closed candle. Do not drop the newest closed bar.
            per_tf: Dict[str, List[Dict[str, Any]]] = {"M1": m1}
            # Fetch the full configured Base hierarchy, including weekly and monthly
            # parents. Omitting these silently downgraded the supposed MTF model.
            for timeframe in ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5"):
                per_tf[timeframe] = self._fetch_candles(symbol, timeframe, 201)

            # The only enabled decision path is hierarchical Base behavior.
            # A proposal is not an order: pending-order execution and Base-driven
            # position exits/re-entry management must use a dedicated broker manager.
            base_plan = self._evaluate_hierarchical_base_plan(per_tf, tick, symbol=symbol)
            self._sync_trade_review(symbol, open_positions, tick, base_plan)
            if _demo_exploration_enabled() and not open_positions:
                strategy_results = base_plan.get("strategy_results") or {}
                qualified = {
                    name: result for name, result in strategy_results.items()
                    if result.get("status") == "ENTRY_PROPOSAL"
                    and isinstance(result.get("order_plan"), dict)
                    and str((result.get("order_plan") or {}).get("status", "")).upper() == "PROPOSED"
                    and str(result.get("direction", "")).upper() in ("BUY", "SELL")
                }
                if qualified:
                    try:
                        from src.Learning.Services.strategy_exploration_selector import choose_demo_strategy
                        discovery = choose_demo_strategy(
                            qualified.keys(), symbol, _PROJECT_ROOT / "storage" / "strategy_discovery"
                        )
                        chosen_name = discovery["selected_strategy"]
                        chosen = qualified[chosen_name]
                        base_plan.update({
                            "status": "ORDER_PROPOSAL", "selected_strategy": chosen_name,
                            "decision_authority": chosen_name, "order_plan": chosen["order_plan"],
                            "reason": chosen.get("reason", "DEMO exploration selected an under-sampled strategy."),
                            "strategy_selection": discovery, "execution_mode": "DEMO_STYLE_DISCOVERY",
                        })
                        self._log_event({"event": "demo_strategy_exploration_selected", "symbol": symbol,
                                         **discovery, "candidate_names": sorted(qualified.keys()),
                                         "live_activation_allowed": False})
                    except Exception:
                        # Strategy research is optional; retain the existing qualified plan if selection fails.
                        logger.exception("DEMO strategy exploration selection failed closed to existing plan")
            if allow_multiple_positions:
                active_orders_for_slots = self.adapter.get_active_orders(symbol=symbol)
                if active_orders_for_slots is None:
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Cannot verify pending-order state before assigning strategy slots.",
                            "execution_enabled": False}
                dedupe = self._dedupe_owned_pending_orders(symbol, active_orders_for_slots, symbol_info)
                if not dedupe.get("ok"):
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": dedupe.get("reason", "Pending-order duplicate reconciliation failed."),
                            "execution_enabled": False}
                active_orders_for_slots = dedupe["orders"]
                def _slot_name(comment: str) -> str:
                    normalized = str(comment or "").strip().upper()
                    # Match broker-safe canonical comments against this cycle's
                    # actual strategy names before attempting legacy comment parsing.
                    for candidate_name in (base_plan.get("strategy_results") or {}):
                        if _strategy_broker_comment(candidate_name).upper() == normalized:
                            return candidate_name
                    # Recover the long names written by older versions whose MT5
                    # comment was truncated to 15 characters by the broker adapter.
                    if normalized.startswith("YARBASEBASE_ENG") or normalized == "YARBASEENGULF":
                        return "BASE_ENGULF_REVERSAL"
                    if normalized.startswith("YARBASEPRICE"):
                        return "PRICE_ACTION"
                    if ":" in normalized:
                        return normalized.split(":", 1)[1].strip() or "BASE_HIERARCHY"
                    if normalized == "YARBASE":
                        return "BASE_HIERARCHY"
                    if normalized.startswith("YARBASE"):
                        return normalized[len("YARBASE"):].lstrip("_-") or "BASE_HIERARCHY"
                    return "BASE_HIERARCHY"
                occupied_slots = {_slot_name(str(self._field(pos, "comment", "") or ""))
                                  for pos in open_positions
                                  if int(self._field(pos, "magic", 0) or 0) == 100001
                                  and str(self._field(pos, "comment", "") or "").startswith("YarBase")}
                bot_pending_orders = [order for order in active_orders_for_slots
                                      if int(self._field(order, "magic", 0) or 0) == 100001
                                      and str(self._field(order, "comment", "") or "").startswith("YarBase")]
                occupied_slots.update(_slot_name(str(self._field(order, "comment", "") or ""))
                                      for order in bot_pending_orders)
                bot_positions = [position for position in open_positions
                                 if int(self._field(position, "magic", 0) or 0) == 100001
                                 and str(self._field(position, "comment", "") or "").startswith("YarBase")]
                total_reserved_slots = len(bot_positions) + len(bot_pending_orders)
                candidates = []
                for name, result in (base_plan.get("strategy_results") or {}).items():
                    plan = result.get("order_plan")
                    if (result.get("status") == "ENTRY_PROPOSAL" and isinstance(plan, dict)
                            and str(plan.get("status", "")).upper() == "PROPOSED"
                            and str(result.get("direction", "")).upper() in ("BUY", "SELL")):
                        candidates.append((name, result, plan))
                selected = next((item for item in candidates if item[0] not in occupied_slots), None)

                # Review every existing bot-owned pending order against its own
                # strategy's freshly computed result before deciding whether the
                # portfolio has room for a new slot. Capacity-full must not freeze
                # pending orders in an unreviewed state.
                reviewed_strategy_slots = set()
                for existing_order in bot_pending_orders:
                    existing_slot = _slot_name(str(self._field(existing_order, "comment", "") or ""))
                    if existing_slot in reviewed_strategy_slots:
                        continue
                    reviewed_strategy_slots.add(existing_slot)
                    existing_ticket = int(self._field(existing_order, "ticket", 0) or 0)
                    existing_result = (base_plan.get("strategy_results") or {}).get(existing_slot, {})
                    existing_plan = existing_result.get("order_plan")
                    review_plan = dict(base_plan)
                    if (existing_result.get("status") == "ENTRY_PROPOSAL"
                            and isinstance(existing_plan, dict)
                            and str(existing_plan.get("status", "")).upper() == "PROPOSED"
                            and str(existing_result.get("direction", "")).upper() in ("BUY", "SELL")):
                        review_plan.update({
                            "status": "ORDER_PROPOSAL", "selected_strategy": existing_slot,
                            "decision_authority": existing_slot, "order_plan": existing_plan,
                            "reason": existing_result.get("reason", "Revalidating existing pending order."),
                        })
                    else:
                        review_plan.update({
                            "status": "WAIT", "selected_strategy": existing_slot,
                            "decision_authority": existing_slot,
                            "order_plan": {"status": "WAIT"},
                            "reason": existing_result.get("reason") or
                                      "Current strategy has no fresh qualified replacement; keep finite-expiry order under review.",
                        })
                    review_plan["max_demo_slots"] = configured_max_positions
                    review_plan["reserved_demo_slots"] = total_reserved_slots
                    review_plan["occupied_strategy_slots"] = sorted(occupied_slots)
                    self._log_event({
                        "event": "pending_order_review_cycle", "symbol": symbol,
                        "ticket": existing_ticket, "strategy": existing_slot,
                        "strategy_signal_status": existing_result.get("status", "WAIT"),
                        "strategy_signal_direction": existing_result.get("direction", "WAIT"),
                        "capacity_full": total_reserved_slots >= configured_max_positions,
                        "reason": "Rechecking existing pending order against fresh closed-candle strategy evidence before allocating any new slot.",
                        "structure": review_plan.get("structure") or (review_plan.get("hierarchy") or {}).get("structure") or {},
                        "entry_level_context": review_plan.get("entry_level_context") or {},
                    })
                    self._reconcile_base_pending_order(
                        symbol, review_plan, tick, account, symbol_info, per_tf=per_tf
                    )

                if total_reserved_slots >= configured_max_positions:
                    base_plan.update({"status": "WAIT",
                                      "reason": f"DEMO capacity reached: {total_reserved_slots} open/pending YarTrader slots reserve the configured limit of {configured_max_positions}.",
                                      "selected_strategy": "NONE", "decision_authority": "NONE",
                                      "order_plan": {"status": "WAIT", "reason": "Open positions plus broker-side pending orders already reserve every configured slot."},
                                      "execution_enabled": False})
                elif selected is None:
                    base_plan.update({"status": "WAIT", "reason": "No qualified strategy proposal has a free independent slot.",
                                      "selected_strategy": "NONE", "decision_authority": "NONE",
                                      "order_plan": {"status": "WAIT", "reason": "All current proposals are waiting or already have a slot."},
                                      "execution_enabled": False})
                else:
                    selected_name, selected_result, selected_plan = selected
                    base_plan.update({"status": "ORDER_PROPOSAL", "reason": selected_result.get("reason", "Qualified strategy proposal."),
                                      "selected_strategy": selected_name, "decision_authority": selected_name,
                                      "order_plan": selected_plan, "execution_enabled": False})
                base_plan["reserved_demo_slots"] = total_reserved_slots
                base_plan["max_demo_slots"] = configured_max_positions
                base_plan["occupied_strategy_slots"] = sorted(occupied_slots)
                base_plan["available_strategy_proposals"] = [name for name, _, _ in candidates if name not in occupied_slots]
            self._log_event({
                "event": "strategy_candidate_audit",
                "symbol": symbol,
                "strategies": {name: {
                    "status": result.get("status", "WAIT"),
                    "direction": result.get("direction", "WAIT"),
                    "confidence": result.get("confidence", 0.0),
                    "reason": result.get("reason", ""),
                    "execution_enabled": bool(result.get("execution_enabled", False)),
                    "order_plan_status": (result.get("order_plan") or {}).get("status"),
                } for name, result in (base_plan.get("strategy_results") or {}).items()},
                "selected_strategy": base_plan.get("selected_strategy", "NONE"),
                "strategy_proposals_count": base_plan.get("strategy_proposals_count", 0),
            })
            self._log_event({
                "event": "hierarchical_base_primary_decision",
                "symbol": symbol,
                "base_plan_summary": {
                    "status": base_plan.get("status"),
                    "reason": base_plan.get("reason"),
                    "selected_strategy": base_plan.get("selected_strategy"),
                    "decision_authority": base_plan.get("decision_authority"),
                    "confidence": base_plan.get("confidence"),
                    "order_plan": base_plan.get("order_plan") or {},
                    "strategy_results": {
                        name: {
                            "status": result.get("status"),
                            "direction": result.get("direction"),
                            "reason": result.get("reason"),
                            "order_plan": result.get("order_plan") or {},
                        }
                        for name, result in (base_plan.get("strategy_results") or {}).items()
                        if isinstance(result, dict)
                    },
                },
                "structure": base_plan.get("structure") or (base_plan.get("hierarchy") or {}).get("structure") or {},
                "historical_structure_analysis": base_plan.get("historical_structure_analysis") or (base_plan.get("hierarchy") or {}).get("historical_structure_analysis") or {},
                "entry_level_context": base_plan.get("entry_level_context") or {},
                "open_positions": len(open_positions),
                "execution_enabled": False,
            })

            # Explicit multi-position DEMO mode: keep all bot-owned positions
            # (including same-direction adds and opposite-direction hedges) under
            # their broker-side protective SLs. Never manage unrelated/manual trades.
            if allow_multiple_positions and open_positions:
                try:
                    max_positions = int(_demo_config_value(
                        "YARTRADER_DEMO_MAX_POSITIONS_PER_SYMBOL", "3"
                    ))
                except (TypeError, ValueError):
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Invalid multi-position limit configuration.",
                            "execution_enabled": False}
                if max_positions < 1 or max_positions > 10 or len(open_positions) > max_positions:
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": f"Open position count/configuration exceeds the configured per-symbol limit ({max_positions}).",
                            "execution_enabled": False}
                for existing in open_positions:
                    existing_magic = int(self._field(existing, "magic", 0) or 0)
                    existing_comment = str(self._field(existing, "comment", "") or "")
                    existing_ticket = int(self._field(existing, "ticket", 0) or 0)
                    existing_sl = float(self._field(existing, "sl", 0.0) or 0.0)
                    if existing_magic != 100001 or not existing_comment.startswith("YarBase"):
                        return {"status": "MANUAL_POSITION_UNMANAGED", "symbol": symbol,
                                "reason": "Multi-position mode refuses to modify or add exposure alongside a non-YarTrader position.",
                                "execution_enabled": False}
                    if existing_ticket <= 0 or existing_sl <= 0:
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Every managed position must have a valid ticket and protective stop loss in multi-position mode.",
                                "execution_enabled": False}

                    # Each strategy owns its own exit signal, protective stop, and audit trail.
                    slot = existing_comment.split(":", 1)[1].upper() if ":" in existing_comment else "BASE_HIERARCHY"
                    strategy_result = (base_plan.get("strategy_results") or {}).get(slot, {})
                    position_type = int(self._field(existing, "type", -1))
                    mt5_types = self.adapter._mt5
                    buy_type = int(getattr(mt5_types, "POSITION_TYPE_BUY", 0))
                    sell_type = int(getattr(mt5_types, "POSITION_TYPE_SELL", 1))
                    held_direction = "BUY" if position_type == buy_type else ("SELL" if position_type == sell_type else "UNKNOWN")
                    signal_direction = str(strategy_result.get("direction", "WAIT")).upper()
                    if (strategy_result.get("status") == "ENTRY_PROPOSAL"
                            and signal_direction in ("BUY", "SELL") and held_direction in ("BUY", "SELL")
                            and signal_direction != held_direction):
                        close_response = self.adapter.send_order_to_broker(OrderRequest(
                            Symbol=symbol, OrderType="CLOSE",
                            Volume=float(self._field(existing, "volume", 0.0) or 0.0),
                            PositionTicket=existing_ticket, Comment=f"YarExit:{slot}", Magic=100001,
                        ))
                        success_codes = {0, 10009, int(getattr(mt5_types, "TRADE_RETCODE_DONE", 10009))}
                        if close_response.Status not in ("Placed", "Executed") or int(close_response.Retcode) not in success_codes:
                            return {"status": "EXIT_FAILED", "symbol": symbol, "strategy": slot,
                                    "ticket": existing_ticket, "reason": close_response.Comment,
                                    "execution_enabled": False}
                        flat_check = self._confirm_position_flat(symbol, existing_ticket)
                        self._log_event({"event": "strategy_position_exit", "symbol": symbol,
                                         "strategy": slot, "ticket": existing_ticket,
                                         "exit_reason": "OWN_STRATEGY_OPPOSITE_SETUP",
                                         "held_direction": held_direction, "signal_direction": signal_direction,
                                         "flat_confirmation": flat_check})
                        if not flat_check.get("confirmed"):
                            return {"status": "EXIT_NOT_CONFIRMED", "symbol": symbol,
                                    "strategy": slot, "ticket": existing_ticket,
                                    "reason": flat_check.get("reason"), "execution_enabled": False}
                        return {"status": "STRATEGY_POSITION_CLOSED", "symbol": symbol,
                                "strategy": slot, "ticket": existing_ticket,
                                "reason": "The position was closed only after its own strategy confirmed an opposite setup.",
                                "execution_enabled": True}

                    # Broker-side TP is a fail-safe, not a competing exit policy.
                    # Keep any existing target in place; only validated target-extension
                    # logic may move it farther into profit, never clear it here.

                    trailing_candidate = self._candidate_structural_trailing_stop(
                        existing, per_tf.get("M5", []), tick, symbol_info
                    )
                    if trailing_candidate is not None:
                        update_sl = getattr(self.adapter, "update_position_stop_loss", None)
                        if not callable(update_sl):
                            return {"status": "BLOCKED", "symbol": symbol, "strategy": slot,
                                    "reason": "Structural trailing stop is indicated but broker SL modification is unavailable.",
                                    "execution_enabled": False}
                        update_response = update_sl(existing_ticket, trailing_candidate)
                        if update_response.Status not in ("Modified", "NoChange") or int(update_response.Retcode) not in (0, 10009):
                            return {"status": "BLOCKED", "symbol": symbol, "strategy": slot,
                                    "reason": f"Could not update structural trailing SL for {existing_ticket}: {update_response.Comment}",
                                    "execution_enabled": False}
                        if update_response.Status == "Modified":
                            self._log_event({"event": "strategy_structural_trailing_stop", "symbol": symbol,
                                             "strategy": slot, "ticket": existing_ticket,
                                             "old_sl": existing_sl, "new_sl": trailing_candidate,
                                             "basis": "CONFIRMED_M5_SWING"})
                if len(open_positions) >= max_positions:
                    return {"status": "MULTI_POSITION_LIMIT_REACHED", "symbol": symbol,
                            "reason": f"Configured limit of {max_positions} active positions per symbol reached; no additional entry submitted.",
                            "open_positions": len(open_positions), "execution_enabled": False}
                if (base_plan.get("status") == "ORDER_PROPOSAL"
                        and str((base_plan.get("order_plan") or {}).get("direction", "")).upper() in ("BUY", "SELL")):
                    order_state = self._reconcile_base_pending_order(
                        symbol, base_plan, tick, account, symbol_info, per_tf=per_tf
                    )
                    return {
                        "status": order_state.get("status", "WAIT"),
                        "symbol": symbol,
                        "reason": order_state.get("reason") or "Multi-position DEMO proposal evaluated.",
                        "pending_order_state": order_state,
                        "open_positions": len(open_positions),
                        "max_positions_per_symbol": max_positions,
                        "position_mode": "SAME_OR_OPPOSITE_DIRECTION_DEMO",
                        "execution_enabled": order_state.get("status") in ("MARKET_OPENED", "MARKET_SUBMITTED"),
                    }
                return {"status": "MULTI_POSITION_HOLD", "symbol": symbol,
                        "reason": "No qualified Base entry; existing same/opposite-direction DEMO positions are retained with protective stop losses.",
                        "open_positions": len(open_positions),
                        "max_positions_per_symbol": max_positions,
                        "execution_enabled": False}

            if len(open_positions) > 1:
                mt5 = self.adapter._mt5
                buy_type_check = int(getattr(mt5, "POSITION_TYPE_BUY", 0))
                sell_type_check = int(getattr(mt5, "POSITION_TYPE_SELL", 1))
                directions = []
                for existing in open_positions:
                    existing_magic = int(self._field(existing, "magic", 0) or 0)
                    existing_comment = str(self._field(existing, "comment", "") or "")
                    existing_type = int(self._field(existing, "type", -1))
                    if existing_magic != 100001 or not existing_comment.startswith("YarBase"):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Multiple positions include a non-YarTrader position; manual reconciliation required."}
                    directions.append("BUY" if existing_type == buy_type_check else
                                      ("SELL" if existing_type == sell_type_check else "UNKNOWN"))
                if set(directions) != {"BUY", "SELL"}:
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Multiple positions are not a clean opposite-direction YarTrader hedge."}

            if open_positions:
                # Keep a qualified reverse pending order intact across polling cycles.
                # Orphan orders are reconciled only after the fresh setup is classified.
                proposal_direction = str((base_plan.get("order_plan") or {}).get("direction", "")).upper()
                buy_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_BUY", 0))
                sell_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_SELL", 1))
                # When a reverse leg has filled on a hedging account, select the old
                # position first; never accidentally close the newly opened reverse leg.
                position = open_positions[0]
                if len(open_positions) > 1:
                    # With two broker-confirmed opposite legs, close the older leg
                    # after validating that both are bot-owned; retain the newer reverse leg.
                    def _position_opened_at(candidate: Any) -> int:
                        return int(self._field(candidate, "time_msc", 0) or
                                   (int(self._field(candidate, "time", 0) or 0) * 1000))
                    position_times = [_position_opened_at(candidate) for candidate in open_positions]
                    if any(opened_at <= 0 for opened_at in position_times):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Cannot establish the order of two opposite positions from broker timestamps; manual reconciliation required.",
                                "base_plan": base_plan, "execution_enabled": False}
                    position = open_positions[position_times.index(min(position_times))]
                position_magic = int(self._field(position, "magic", 0) or 0)
                position_comment = str(self._field(position, "comment", "") or "")
                owned = position_magic == 100001 and position_comment.startswith("YarBase")
                if not owned:
                    return {"status": "MANUAL_POSITION_UNMANAGED", "symbol": symbol,
                            "reason": "Open position is not identified as a YarTrader Base position; it will not be modified or closed.",
                            "base_plan": base_plan, "execution_enabled": False}

                # Keep the initial broker-side TP as protection. Extend it only when
                # the freshly analyzed target is farther in the profitable direction;
                # never initialize/change TP on a pre-existing position with no TP here.
                target_plan_direction = str((base_plan.get("order_plan") or {}).get("direction", "")).upper()
                candidate_target = (
                    self._planned_target(base_plan)
                    if base_plan.get("status") == "ORDER_PROPOSAL" and target_plan_direction in ("BUY", "SELL")
                    else 0.0
                )
                for candidate in open_positions:
                    candidate_ticket = int(self._field(candidate, "ticket", 0) or 0)
                    candidate_magic = int(self._field(candidate, "magic", 0) or 0)
                    candidate_comment = str(self._field(candidate, "comment", "") or "")
                    candidate_tp = float(self._field(candidate, "tp", 0.0) or 0.0)
                    candidate_type = int(self._field(candidate, "type", -1))
                    candidate_entry = float(self._field(candidate, "price_open", 0.0) or 0.0)
                    buy_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_BUY", 0))
                    sell_type = int(getattr(self.adapter._mt5, "POSITION_TYPE_SELL", 1))
                    if (candidate_magic != 100001 or not candidate_comment.startswith("YarBase")
                            or candidate_ticket <= 0 or candidate_tp <= 0 or candidate_target <= 0):
                        continue
                    momentum_confirmed = self._has_confirmed_tp_extension_momentum(target_plan_direction, per_tf)
                    extends_target = momentum_confirmed and ((
                        target_plan_direction == "BUY" and candidate_type == buy_type
                        and candidate_target > candidate_tp and candidate_target > candidate_entry
                        and candidate_target > ask
                    ) or (
                        target_plan_direction == "SELL" and candidate_type == sell_type
                        and candidate_target < candidate_tp and 0 < candidate_target < candidate_entry
                        and candidate_target < bid
                    ))
                    if not extends_target:
                        continue
                    update_tp = getattr(self.adapter, "update_position_take_profit", None)
                    if not callable(update_tp):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "A farther structural target is indicated but broker TP modification is unavailable.",
                                "base_plan": base_plan, "execution_enabled": False}
                    update_response = update_tp(candidate_ticket, candidate_target)
                    if update_response.Status not in ("Modified", "NoChange") or int(update_response.Retcode) not in (0, 10009):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": f"Could not extend broker TP for position {candidate_ticket}: {update_response.Comment}",
                                "base_plan": base_plan, "execution_enabled": False}
                    if update_response.Status == "Modified":
                        self._log_event({"event": "strategy_take_profit_extended", "symbol": symbol,
                                         "ticket": candidate_ticket, "old_tp": candidate_tp,
                                         "new_tp": candidate_target,
                                         "basis": "FRESH_VALIDATED_STRATEGY_TARGET_AND_CONFIRMED_M5_MOMENTUM_STRUCTURE",
                                         "protective_sl_preserved": float(self._field(candidate, "sl", 0.0) or 0.0)})
                # Strategy-managed profit protection: tighten the broker SL only
                # behind a confirmed M5 swing that has formed after entry. Keep the
                # broker TP as a fail-safe; target extension is handled separately.
                trailing_candidate = self._candidate_structural_trailing_stop(
                    position, per_tf.get("M5", []), tick, symbol_info,
                )
                if trailing_candidate is not None:
                    position_ticket = int(self._field(position, "ticket", 0) or 0)
                    update_sl = getattr(self.adapter, "update_position_stop_loss", None)
                    if position_ticket <= 0 or not callable(update_sl):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "A structural profit-protection update is indicated but broker SL modification is unavailable.",
                                "base_plan": base_plan, "execution_enabled": False}
                    update_response = update_sl(position_ticket, trailing_candidate)
                    if (update_response.Status not in ("Modified", "NoChange")
                            or int(update_response.Retcode) not in (0, 10009)):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": f"Could not apply structural profit-protection stop: {update_response.Comment}",
                                "base_plan": base_plan, "execution_enabled": False}
                    if update_response.Status == "Modified":
                        self._log_event({"event": "base_structural_profit_protection", "symbol": symbol,
                                         "ticket": position_ticket,
                                         "old_sl": float(self._field(position, "sl", 0.0) or 0.0),
                                         "new_sl": trailing_candidate, "basis": "CONFIRMED_M5_SWING"})
                        refreshed = self.adapter.get_positions(symbol=symbol)
                        if refreshed is None:
                            return {"status": "BLOCKED", "symbol": symbol,
                                    "reason": "Broker position state unavailable after structural SL update.",
                                    "base_plan": base_plan, "execution_enabled": False}
                        position = next((candidate for candidate in refreshed
                                         if int(self._field(candidate, "ticket", 0) or 0) == position_ticket), position)
                        open_positions = refreshed

                pos_type = int(self._field(position, "type", -1))
                held_direction = "BUY" if pos_type == buy_type else ("SELL" if pos_type == sell_type else "UNKNOWN")
                proposal_direction = str((base_plan.get("order_plan") or {}).get("direction", "")).upper()
                opposite_positions = []
                for candidate in open_positions:
                    candidate_magic = int(self._field(candidate, "magic", 0) or 0)
                    candidate_comment = str(self._field(candidate, "comment", "") or "")
                    candidate_type = int(self._field(candidate, "type", -1))
                    candidate_direction = (
                        "BUY" if candidate_type == buy_type
                        else ("SELL" if candidate_type == sell_type else "UNKNOWN")
                    )
                    if (candidate_magic == 100001 and candidate_comment.startswith("YarBase")
                            and candidate_direction in ("BUY", "SELL")
                            and candidate_direction != held_direction):
                        opposite_positions.append(candidate)

                qualified_opposite = bool(opposite_positions) or (
                    base_plan.get("status") == "ORDER_PROPOSAL"
                    and proposal_direction in ("BUY", "SELL") and proposal_direction != held_direction
                )
                if qualified_opposite:
                    # A confirmed opposite strategy setup is itself an exit signal.
                    # Do not wait for a reverse pending order to fill before protecting
                    # already-earned profit; exit the old position first.
                    if not opposite_positions and not (
                        base_plan.get("status") == "ORDER_PROPOSAL"
                        and proposal_direction in ("BUY", "SELL")
                        and proposal_direction != held_direction
                    ):
                        reverse_order_state = self._reconcile_base_pending_order(
                            symbol, base_plan, tick, account, symbol_info, per_tf=per_tf,
                        )
                        if reverse_order_state.get("status") not in ("MARKET_OPENED", "MARKET_SUBMITTED"):
                            return {
                                "status": "POSITION_HELD_REVERSE_NOT_FILLED",
                                "symbol": symbol,
                                "reason": "Opposite setup is not an executed broker position; keep the current position and wait. A pending order alone never triggers an exit.",
                                "reverse_order_state": reverse_order_state,
                                "base_plan": base_plan,
                                "execution_enabled": False,
                            }
                        return {
                            "status": "POSITION_HELD_WAITING_REVERSE_FILL",
                            "symbol": symbol,
                            "reason": "Opposite pending order is working but has not filled; retain the current position's broker-side protection.",
                            "reverse_order_state": reverse_order_state,
                            "base_plan": base_plan,
                            "execution_enabled": True,
                        }

                    # The reverse position is already live. Cancel any remaining
                    # YarTrader Base pending entries first, so they cannot create a
                    # duplicate position after this transition.
                    active_orders = self.adapter.get_active_orders(symbol=symbol)
                    if active_orders is None:
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Cannot verify pending-order state before closing the old position.",
                                "base_plan": base_plan, "execution_enabled": False}
                    for pending in active_orders:
                        if (int(self._field(pending, "magic", 0) or 0) == 100001
                                and str(self._field(pending, "comment", "") or "").startswith("YarBase")):
                            pending_ticket = int(self._field(pending, "ticket", 0) or 0)
                            if pending_ticket <= 0:
                                return {"status": "BLOCKED", "symbol": symbol,
                                        "reason": "Owned pending order has no valid ticket during reversal cleanup.",
                                        "base_plan": base_plan, "execution_enabled": False}
                            cancel_response = self.adapter.cancel_pending_order(pending_ticket)
                            if cancel_response.Status != "Cancelled":
                                return {"status": "BLOCKED", "symbol": symbol,
                                        "reason": f"Could not cancel residual pending order {pending_ticket} before reversal cleanup: {cancel_response.Comment}",
                                        "base_plan": base_plan, "execution_enabled": False}

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
                                     "exit_reason": "OPPOSITE_BASE_SETUP_CONFIRMED",
                                     "reverse_position_confirmed": bool(opposite_positions),
                                     "broker_status": close_response.Status, "retcode": close_response.Retcode})
                    success_codes = {0, 10009, int(getattr(self.adapter._mt5, "TRADE_RETCODE_DONE", 10009))}
                    if close_response.Status not in ("Placed", "Executed") or int(close_response.Retcode) not in success_codes:
                        return {"status": "EXIT_FAILED", "symbol": symbol, "reason": close_response.Comment,
                                "base_plan": base_plan, "execution_enabled": False}
                    flat_check = self._confirm_position_flat(symbol, ticket)
                    self._log_event({"event": "base_position_exit_reconciliation", "symbol": symbol,
                                     "ticket": ticket, **flat_check})
                    if not flat_check.get("confirmed"):
                        return {"status": "EXIT_NOT_CONFIRMED", "symbol": symbol,
                                "reason": flat_check.get("reason"), "base_plan": base_plan,
                                "close_response": close_response.__dict__, "execution_enabled": False}
                    return {"status": "POSITION_CLOSED_BASE_EXIT", "symbol": symbol,
                            "reason": "Strategy-confirmed opposite structural setup closed the old position; no preset TP is used.",
                            "base_plan": base_plan, "close_response": close_response.__dict__,
                            "flat_confirmation": flat_check, "execution_enabled": True}
                order_state = self._reconcile_base_pending_order(
                    symbol, {"status": "WAIT", "reason": "Position held; no qualified opposite entry setup."},
                    tick, account, symbol_info, per_tf=per_tf,
                )
                if order_state.get("status") == "BLOCKED":
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Could not reconcile stale pending orders while holding the position.",
                            "pending_order_state": order_state, "base_plan": base_plan, "execution_enabled": False}
                return {
                    "status": "POSITION_HELD_BASE_STRUCTURE", "symbol": symbol,
                    "reason": "No qualified opposite entry is available; hold the position with its broker-side SL/TP protection.",
                    "pending_order_state": order_state, "base_plan": base_plan, "execution_enabled": False,
                }
            order_state = self._reconcile_base_pending_order(symbol, base_plan, tick, account, symbol_info, per_tf=per_tf)
            return {
                "status": order_state.get("status", "WAIT"), "symbol": symbol,
                "reason": order_state.get("reason") or base_plan.get("reason") or "No validated hierarchical Base setup.",
                "base_plan": base_plan, "pending_order_state": order_state,
                "execution_enabled": order_state.get("status") in ("MARKET_OPENED", "MARKET_SUBMITTED"),
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
            try:
                symbols = _enabled_demo_symbols()
            except Exception as exc:
                logger.error("Cannot resolve canonical DEMO symbol universe; failing closed: %s", exc)
                symbols = []
            # If every enabled market is closed, avoid even initializing the broker
            # adapter or entering the research/learning loop. Backtests run separately.
            open_symbols = [symbol for symbol in symbols if MarketSessionEngine.live_activity_status(symbol).get("allowed")]
            if not open_symbols:
                time.sleep(60)
                continue
            if trader is None:
                trader = AutonomousDemoTrader()
            results = []
            for symbol in open_symbols:
                result = trader.run_once(symbol_override=symbol)
                results.append(result)
                # A managed position on one symbol must not starve the rest of the
                # enabled universe. Stop only after a NEW market entry is submitted;
                # held positions and WAIT cycles still allow
                # later symbols (such as EURUSD) to be evaluated this cycle.
                if result.get("status") in ("MARKET_OPENED", "MARKET_SUBMITTED"):
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
        from src.Execution.Services.demo_worker_singleton import acquire_demo_worker_singleton
        if not acquire_demo_worker_singleton():
            logger.warning("DEMO worker not started because another process owns the cross-process singleton.")
            return
        _WORKER = threading.Thread(
            target=run_autonomous_demo_trading_loop,
            name="AutonomousDemoTrader",
            daemon=True,
        )
        _WORKER.start()
