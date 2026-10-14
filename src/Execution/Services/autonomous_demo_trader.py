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
from src.Execution.Safety.demo_exploration_policy import demo_exploration_autonomy_enabled
from src.Infrastructure.exceptions import ValidationException
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, ProductionRiskPolicy

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
        "W1": "TIMEFRAME_W1",
        "MN1": "TIMEFRAME_MN1",
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
                exploration_mode=(
                    os.environ.get("YARTRADER_DEMO_EXPLORATION_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
                    and os.environ.get("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
                    and os.environ.get("YARTRADER_TRADING_MODE", "").strip().upper() == "DEMO"
                ),
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
                    or (
                        os.environ.get("YARTRADER_DEMO_EXPLORATION_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
                        and os.environ.get("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
                        and os.environ.get("YARTRADER_TRADING_MODE", "").strip().upper() == "DEMO"
                    )
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
        event["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            folder = _PROJECT_ROOT / "runtime_logs"
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "autonomous_demo_trader.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except OSError:
            logger.exception("Unable to persist autonomous DEMO trader event")
        logger.info("Autonomous DEMO trader: %s", event)

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
                    if history_result.get("new_deals_recorded", 0) or not store.report_path.exists():
                        report = store.build_discovery_report()
                    else:
                        try:
                            report = json.loads(store.report_path.read_text(encoding="utf-8"))
                        except (OSError, ValueError):
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
                move = (mid - exit_price) if record.get("direction") == "BUY" else (exit_price - mid)
                record["max_favorable_move"] = max(float(record.get("max_favorable_move", 0.0)), move, 0.0)
                record["max_adverse_move"] = min(float(record.get("max_adverse_move", 0.0)), move, 0.0)
                record.setdefault("observations", []).append({
                    "time_utc": now.isoformat(), "bid": float(tick.get("bid", 0.0)),
                    "ask": float(tick.get("ask", 0.0)), "mid": mid,
                    "move_in_trade_direction": move,
                })
                # Keep the persistent journal bounded while retaining the full one-hour sample.
                record["observations"] = record["observations"][-130:]
                record["elapsed_seconds"] = elapsed
                changed = True
                if elapsed >= 3600:
                    record["tracking_complete"] = True
                    self._log_event({
                        "event": "post_exit_price_tracking_completed", "symbol": symbol.upper(),
                        "deal_ticket": record["deal_ticket"], "exit_reason": record["exit_reason"],
                        "observations": len(record["observations"]),
                        "max_favorable_move": record["max_favorable_move"],
                        "max_adverse_move": record["max_adverse_move"],
                        "learning_note": (
                            "Post-exit price continued favorably after exit; review entry/exit timing."
                            if record["max_favorable_move"] > 0 else
                            "No favorable continuation observed during the tracking window."
                        ),
                    })
            if changed or state:
                temp = path.with_suffix(".json.tmp")
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
        exploration = demo_exploration_autonomy_enabled()
        if exploration and not allowed and reason == "DAILY_LOSS_LIMIT_REACHED":
            logger.warning("DEMO_EXPLORATION_OVERRIDE: daily-loss threshold is telemetry-only; hard account/data validation remains enforced.")
            return {"allowed": True, "reason": "DEMO_EXPLORATION_DAILY_LOSS_OVERRIDE", "meta": meta, "pnl": pnl,
                    "exploration_override": True}
        return {"allowed": allowed, "reason": reason, "meta": meta, "pnl": pnl}

    def _reconcile_base_pending_order(
        self, symbol: str, base_plan: Dict[str, Any], tick: Dict[str, Any],
        account: Dict[str, Any], symbol_info: Dict[str, Any],
        per_tf: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Idempotently reconcile one YarTrader-owned Base pending order for a symbol."""
        orders = self.adapter.get_active_orders(symbol=symbol)
        if orders is None:
            return {"status": "BLOCKED", "reason": "Broker pending-order state is unknown; refusing duplicate or new entry."}
        mt5 = self.adapter._mt5
        strategy_name = str(base_plan.get("selected_strategy") or base_plan.get("decision_authority") or "BASE_HIERARCHY").upper()
        strategy_comment = "YarBase" if strategy_name in ("BASE_HIERARCHY", "NONE", "") else f"YarBase:{strategy_name}"
        owned = [
            order for order in orders
            if int(self._field(order, "magic", 0) or 0) == 100001
            and str(self._field(order, "comment", "") or "") == strategy_comment
        ]
        plan = base_plan.get("order_plan") or {}
        valid = base_plan.get("status") == "ORDER_PROPOSAL" and plan.get("status") == "PROPOSED"
        if not valid:
            # A missing proposal in this polling cycle is not proof that a working
            # broker-side pending order is invalid. Keep accepted orders working
            # until broker expiry or a new qualified proposal explicitly replaces
            # them; otherwise a transient WAIT/no-parent/model-not-ready decision
            # would cancel orders seconds after successful placement.
            retained = [
                int(self._field(order, "ticket", 0) or 0)
                for order in owned
                if int(self._field(order, "ticket", 0) or 0) > 0
            ]
            if len(retained) != len(owned):
                return {"status": "BLOCKED", "reason": "Owned pending order has no valid broker ticket; refusing to assume its state."}
            return {
                "status": "WAIT" if not retained else "ALREADY_PENDING",
                "reason": base_plan.get("reason", "No new qualified Base reaction proposal; existing broker orders are retained."),
                "retained_pending_orders": retained,
                "cancelled_pending_orders": [],
            }

        plan = dict(plan)
        try:
            direction = str(plan["direction"]).upper()
            order_type = str(plan["order_type"]).upper()
            entry, stop = float(plan["entry"]), float(plan["stop_loss"])
            original_stop = stop
            target = float(plan.get("take_profit") or 0.0)
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
                spread_now = max(0.0, float(tick.get("ask", 0.0)) - float(tick.get("bid", 0.0)))
                volatility_floor = max(
                    [1.5 * value if tf == "M5" else 0.75 * value for tf, value in atr_values]
                    + [2.0 * spread_now]
                )
                structural_risk = entry - stop if direction == "BUY" else stop - entry
                if structural_risk < volatility_floor and strategy_name != "BASE_HIERARCHY":
                    return {"status": "BLOCKED", "reason": (
                        f"{strategy_name} structural stop is below the closed-bar volatility floor "
                        f"({structural_risk:.5f} < {volatility_floor:.5f}); no other strategy's boundary may replace it."
                    )}
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
                                and candidate_risk > 0):
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
                        return {
                            "status": "BLOCKED",
                            "reason": (
                                f"Child structural stop is too close (risk distance {structural_risk:.5f}, "
                                f"required floor {volatility_floor:.5f}) and no confirmed parent/intermediate "
                                "Base boundary clears the volatility floor; no artificial stop was forced."
                            ),
                        }
                # A confirmed structural boundary is used; volatility is a minimum
                # validity check, never an arbitrary distance used to invent an SL.
                plan["stop_loss"] = stop
                plan["take_profit"] = None
            expires = int(float(plan["expires_at"])) if plan.get("expires_at") is not None else None
            # DEMO exploration orders are GTC where the broker supports it; short
            # strategy-sample expiries were causing accepted orders to disappear
            # before the learning cycle could observe fills.
            if demo_exploration_autonomy_enabled() and strategy_name == "BASE_HIERARCHY":
                expires = None
            digits = int(symbol_info["digits"])
            if direction not in ("BUY", "SELL") or order_type not in ("BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"):
                raise ValueError("Unsupported Base pending order type or direction.")
            if not all(math.isfinite(x) and x > 0 for x in (entry, stop)):
                raise ValueError("Base plan contains invalid entry or protective stop.")
            if (direction == "BUY" and not stop < entry) or (direction == "SELL" and not entry < stop):
                raise ValueError("Pending order has invalid protective-stop geometry.")
            risk_distance = abs(entry - stop)
            net_rr = float(plan.get("net_reward_risk") or 0.0)
            analytical_scenario = (base_plan.get("reaction_analysis") or {}).get("scenario") or {}
            if not analytical_scenario:
                analytical_scenario = (base_plan.get("hierarchy") or {}).get("scenario") or {}
            try:
                analytical_target = float(analytical_scenario.get("target"))
                if math.isfinite(analytical_target) and analytical_target > 0:
                    reward_distance = (analytical_target - entry if direction == "BUY" else entry - analytical_target)
                    if reward_distance > 0 and risk_distance > 0:
                        cost_allowance = spread_now
                        gross_rr = reward_distance / risk_distance
                        net_rr = max(0.0, reward_distance - cost_allowance) / (risk_distance + cost_allowance)
                        plan["gross_reward_risk"] = round(gross_rr, 4)
                        plan["net_reward_risk"] = round(net_rr, 4)
            except (TypeError, ValueError, OverflowError):
                pass
            if (risk_distance <= 0 or not math.isfinite(net_rr)
                    or (net_rr <= 1.0 and not demo_exploration_autonomy_enabled())):
                raise ValueError("Candidate entry fails the net reward/risk > 1 qualification after costs.")
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
        if demo_exploration_autonomy_enabled() and owned:
            # In exploration, a new candle/model proposal must not erase an accepted
            # broker order. A protective SL is mandatory; TP is intentionally strategy-managed.
            tickets = []
            for order in owned:
                ticket = int(self._field(order, "ticket", 0) or 0)
                stop_value = float(self._field(order, "sl", 0.0) or 0.0)
                target_value = float(self._field(order, "tp", 0.0) or 0.0)
                if ticket <= 0 or stop_value <= 0:
                    return {"status": "BLOCKED", "reason": "Existing DEMO exploration order lacks a ticket or protective SL; refusing unsafe silent replacement."}
                tickets.append(ticket)
            return {
                "status": "ALREADY_PENDING",
                "reason": "DEMO exploration retains broker-accepted pending orders until fill or broker expiry; new polling proposals do not cancel them.",
                "retained_pending_orders": tickets,
                "cancelled_pending_orders": [],
            }
        for order in owned:
            # Reuse only an order whose entry, protective SL, and broker-side TP
            # all match the qualified plan.
            try:
                old_type = int(self._field(order, "type", -1))
                old_entry = float(self._field(order, "price_open", 0.0))
                old_stop = float(self._field(order, "sl", 0.0))
                old_target = float(self._field(order, "tp", 0.0) or 0.0)
                old_expiry = int(self._field(order, "time_expiration", 0) or 0)
                current_time = int(tick.get("time") or time.time())
                same = (
                    old_type == int(desired_type)
                    and abs(old_entry - entry) <= 10 ** (-digits)
                    and abs(old_stop - stop) <= 10 ** (-digits)
                    and abs(old_target) <= 10 ** (-digits)
                    and (old_expiry == 0 or old_expiry > current_time)
                )
            except (TypeError, ValueError, OverflowError):
                same = False
            if same:
                return {"status": "ALREADY_PENDING", "ticket": int(self._field(order, "ticket", 0)),
                        "order_type": order_type, "entry": old_entry,
                        "take_profit": None, "entry_qualification_net_rr": round(net_rr, 4),
                        "expires_at": old_expiry}
        # Remove obsolete orders before replacing them; never stack duplicate Base orders.
        for order in owned:
            ticket = int(self._field(order, "ticket", 0) or 0)
            if ticket <= 0:
                return {"status": "BLOCKED", "reason": "Owned pending order has no valid broker ticket."}
            response = self.adapter.cancel_pending_order(ticket)
            if response.Status != "Cancelled":
                return {"status": "BLOCKED", "reason": f"Could not replace stale Base order {ticket}: {response.Comment}"}

        if demo_exploration_autonomy_enabled():
            # Research-only mode samples with broker minimum volume. Strategy-level
            # percent-risk sizing is bypassed; broker volume bounds remain mandatory.
            min_volume = float(symbol_info.get("volume_min") or 0.0)
            volume_step = float(symbol_info.get("volume_step") or 0.0)
            volume_max = float(symbol_info.get("volume_max") or 0.0)
            if (not all(math.isfinite(v) for v in (min_volume, volume_step, volume_max))
                    or min_volume <= 0 or volume_step <= 0 or volume_max < min_volume):
                return {"status": "RISK_BLOCKED", "reason": "Broker minimum-volume metadata is invalid in DEMO exploration."}
            sizing = {"allowed": True, "volume": min_volume, "risk_model": "DEMO_EXPLORATION_BROKER_MINIMUM_LOT",
                      "risk_per_trade_pct": None, "note": "Percentage risk cap bypassed for DEMO exploration; minimum broker volume retained."}
        else:
            sizing = calculate_demo_volume_by_risk(
                mt5, symbol, direction, entry, stop, symbol_info,
                float(account.get("balance") or 0), float(account.get("equity") or 0),
                float(ProductionRiskPolicy.TARGET_RISK_PCT),
            )
            if not sizing.get("allowed"):
                return {"status": "RISK_BLOCKED", "reason": sizing.get("reason"), "risk": sizing}
        request = OrderRequest(
            Symbol=symbol, OrderType=order_type, Volume=float(sizing["volume"]),
            Price=round(entry, digits), StopLoss=round(stop, digits), TakeProfit=0.0,
            Comment=strategy_comment, Magic=100001, Expiration=expires,
        )
        response = self.adapter.send_order_to_broker(request)
        self._log_event({
            "event": "strategy_pending_order_submission", "symbol": symbol, "strategy": strategy_name,
            "order_type": order_type, "entry": entry, "stop_loss": stop, "take_profit": None,
            "entry_qualification_net_rr": net_rr,
            "exit_policy": "strategy_managed_structural_exit; protective_SL_only; no_preset_TP",
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
            if allow_multiple_positions:
                active_orders_for_slots = self.adapter.get_active_orders(symbol=symbol)
                if active_orders_for_slots is None:
                    return {"status": "BLOCKED", "symbol": symbol,
                            "reason": "Cannot verify pending-order state before assigning strategy slots.",
                            "execution_enabled": False}
                def _slot_name(comment: str) -> str:
                    return comment.split(":", 1)[1].upper() if ":" in comment else "BASE_HIERARCHY"
                occupied_slots = {_slot_name(str(self._field(pos, "comment", "") or ""))
                                  for pos in open_positions
                                  if int(self._field(pos, "magic", 0) or 0) == 100001
                                  and str(self._field(pos, "comment", "") or "").startswith("YarBase")}
                occupied_slots.update(_slot_name(str(self._field(order, "comment", "") or ""))
                                      for order in active_orders_for_slots
                                      if int(self._field(order, "magic", 0) or 0) == 100001
                                      and str(self._field(order, "comment", "") or "").startswith("YarBase"))
                candidates = []
                for name, result in (base_plan.get("strategy_results") or {}).items():
                    plan = result.get("order_plan")
                    if (result.get("status") == "ENTRY_PROPOSAL" and isinstance(plan, dict)
                            and str(plan.get("status", "")).upper() == "PROPOSED"
                            and str(result.get("direction", "")).upper() in ("BUY", "SELL")):
                        candidates.append((name, result, plan))
                selected = next((item for item in candidates if item[0] not in occupied_slots), None)
                if selected is None:
                    base_plan.update({"status": "WAIT", "reason": "No qualified strategy proposal has a free independent slot.",
                                      "selected_strategy": "NONE", "decision_authority": "NONE",
                                      "order_plan": {"status": "WAIT", "reason": "All current proposals are waiting or already have a slot."},
                                      "execution_enabled": False})
                else:
                    selected_name, selected_result, selected_plan = selected
                    base_plan.update({"status": "ORDER_PROPOSAL", "reason": selected_result.get("reason", "Qualified strategy proposal."),
                                      "selected_strategy": selected_name, "decision_authority": selected_name,
                                      "order_plan": selected_plan, "execution_enabled": False})
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
                "base_plan": base_plan,
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

                    # Strategy-managed exits do not use a fixed broker TP. Remove legacy TP
                    # only from verified bot-owned positions and preserve broker SL protection.
                    current_tp = float(self._field(existing, "tp", 0.0) or 0.0)
                    if current_tp > 0:
                        clear_tp = getattr(self.adapter, "clear_position_take_profit", None)
                        if not callable(clear_tp):
                            return {"status": "BLOCKED", "symbol": symbol, "strategy": slot,
                                    "reason": "Cannot safely remove legacy TP for strategy-managed exits.",
                                    "execution_enabled": False}
                        clear_response = clear_tp(existing_ticket)
                        if clear_response.Status not in ("Modified", "NoChange") or int(clear_response.Retcode) not in (0, 10009):
                            return {"status": "BLOCKED", "symbol": symbol, "strategy": slot,
                                    "reason": f"Could not clear legacy TP on position {existing_ticket}: {clear_response.Comment}",
                                    "execution_enabled": False}
                        self._log_event({"event": "strategy_managed_tp_cleared", "symbol": symbol,
                                         "strategy": slot, "ticket": existing_ticket, "old_tp": current_tp})

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
                        "execution_enabled": order_state.get("status") in ("PENDING_PLACED", "ALREADY_PENDING"),
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

                # Strategy-managed exits must not be pre-empted by legacy broker TPs.
                # Clear only TP on bot-owned positions; preserve their structural SL.
                cleared_any_tp = False
                for candidate in open_positions:
                    candidate_ticket = int(self._field(candidate, "ticket", 0) or 0)
                    candidate_magic = int(self._field(candidate, "magic", 0) or 0)
                    candidate_comment = str(self._field(candidate, "comment", "") or "")
                    candidate_tp = float(self._field(candidate, "tp", 0.0) or 0.0)
                    if candidate_magic != 100001 or not candidate_comment.startswith("YarBase") or candidate_tp <= 0:
                        continue
                    clear_tp = getattr(self.adapter, "clear_position_take_profit", None)
                    if not callable(clear_tp) or candidate_ticket <= 0:
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Cannot safely remove a legacy preset TP from a bot-owned position.",
                                "base_plan": base_plan, "execution_enabled": False}
                    clear_response = clear_tp(candidate_ticket)
                    if clear_response.Status not in ("Modified", "NoChange") or int(clear_response.Retcode) not in (0, 10009):
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": f"Could not clear legacy TP for position {candidate_ticket}: {clear_response.Comment}",
                                "base_plan": base_plan, "execution_enabled": False}
                    self._log_event({"event": "strategy_managed_exit_tp_cleared", "symbol": symbol,
                                     "ticket": candidate_ticket, "old_tp": candidate_tp})
                    cleared_any_tp = True
                if cleared_any_tp:
                    refreshed_positions = self.adapter.get_positions(symbol=symbol)
                    if refreshed_positions is None:
                        return {"status": "BLOCKED", "symbol": symbol,
                                "reason": "Broker position state unavailable after legacy TP removal.",
                                "base_plan": base_plan, "execution_enabled": False}
                    for candidate in refreshed_positions:
                        if (int(self._field(candidate, "magic", 0) or 0) == 100001
                                and str(self._field(candidate, "comment", "") or "").startswith("YarBase")
                                and float(self._field(candidate, "tp", 0.0) or 0.0) > 0.0):
                            return {"status": "BLOCKED", "symbol": symbol,
                                    "reason": "Broker still reports a preset TP after the removal request.",
                                    "base_plan": base_plan, "execution_enabled": False}
                # Strategy-managed profit protection: tighten the broker SL only
                # behind a confirmed M5 swing that has formed after entry. No preset
                # TP or fixed-pip trailing distance is introduced.
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
                        if reverse_order_state.get("status") not in ("PENDING_PLACED", "ALREADY_PENDING"):
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
                # A managed position on one symbol must not starve the rest of the
                # enabled universe. Stop only after a NEW pending entry is actually
                # submitted; held positions and already-pending orders still allow
                # later symbols (such as EURUSD) to be evaluated this cycle.
                if result.get("status") == "PENDING_PLACED":
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
