"""Single-strategy compatibility facade: hierarchical Base behavior only.

Legacy callers keep the evaluate_all_strategies signature, but this facade has
no alternative strategy evaluators and can only return a Base-hierarchy proposal.
It never submits orders.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import math

from src.Decision.Intelligence.hierarchical_base_behavior_engine import HierarchicalBaseBehaviorEngine
from src.Decision.Intelligence.base_reaction_decision_engine import BaseReactionDecisionEngine
from src.Research.Brain.multitimeframe_base_transition_engine import TIMEFRAME_SECONDS
from src.Research.Brain.multitimeframe_base_transition_engine import detect_base_departures

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class StrategyOrchestrator:
    """Compatibility facade that exposes only the canonical Base behavior model."""

    supported_strategies = ["BASE_HIERARCHY"]

    @staticmethod
    def _epoch(value: Any, fallback: int) -> int:
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return int(value)
        try:
            return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
        except (TypeError, ValueError, OverflowError):
            return fallback

    @staticmethod
    def _measure_latest_base_reaction(bars: List[Dict[str, Any]], child: Dict[str, Any],
                                      now: int) -> Optional[Dict[str, Any]]:
        """Measure latest closed-candle visit to the selected Base, with causal approach side."""
        try:
            confirm = int(child["confirmation_time"])
            low, high = float(child["base_low"]), float(child["base_high"])
            width = high-low
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(width) or width <= 0:
            return None
        episodes: List[Dict[str, Any]] = []
        active: Optional[Dict[str, Any]] = None
        in_visit = False
        previous_close: Optional[float] = None
        for bar in bars:
            stamp = int(bar["time"])
            if stamp > now:
                break
            close = float(bar["close"])
            if stamp <= confirm:
                previous_close = close
                continue
            touches = float(bar["low"]) <= high and float(bar["high"]) >= low
            if touches and not in_visit:
                side = ("FROM_ABOVE" if previous_close is not None and previous_close > high
                        else "FROM_BELOW" if previous_close is not None and previous_close < low
                        else "INTERIOR_OR_AMBIGUOUS_OHLC")
                active = {"reaction_number": len(episodes)+1, "entry_side": side,
                          "penetration_fraction": 0.0, "start_time": stamp}
                episodes.append(active)
            if touches and active is not None:
                if active["entry_side"] == "FROM_ABOVE":
                    depth = (high-min(max(float(bar["low"]), low), high))/width
                elif active["entry_side"] == "FROM_BELOW":
                    depth = (max(min(float(bar["high"]), high), low)-low)/width
                else:
                    depth = 0.0
                active["penetration_fraction"] = round(max(float(active["penetration_fraction"]),
                                                            min(1.0, max(0.0, depth))), 4)
            in_visit = touches
            previous_close = close
        return dict(episodes[-1]) if episodes else None

    def evaluate_all_strategies(
        self, symbol: str, primary_timeframe: str, candles: List[Dict[str, Any]],
        all_timeframe_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        narrative: Optional[Dict[str, Any]] = None, liquidity: Optional[Dict[str, Any]] = None,
        zones: Optional[Dict[str, Any]] = None, alignment: Optional[Dict[str, Any]] = None,
        similarity: Optional[Dict[str, Any]] = None, fractal: Optional[Dict[str, Any]] = None,
        spread_pip: float = 1.0, account_balance: float = 10000.0,
    ) -> Dict[str, Any]:
        del narrative, liquidity, zones, alignment, similarity, fractal, account_balance
        if not candles:
            return {"symbol": symbol.upper(), "primary_timeframe": primary_timeframe,
                    "candidates": [], "best_candidate": None, "active_candidates_count": 0,
                    "summary": "No candle data provided."}
        tf_map = dict(all_timeframe_candles or {})
        tf_map.setdefault(primary_timeframe, candles)
        events_by_tf: Dict[str, List[Dict[str, Any]]] = {}
        bars_by_tf: Dict[str, List[Dict[str, Any]]] = {}
        latest_epoch = 0
        for tf, rows in tf_map.items():
            bars = []
            for index, row in enumerate(rows):
                epoch = self._epoch(row.get("timestamp", row.get("time")), index * 60)
                latest_epoch = max(latest_epoch, epoch)
                bars.append({"time": epoch, "open": float(row["open"]), "high": float(row["high"]),
                             "low": float(row["low"]), "close": float(row["close"])})
            bars_by_tf[str(tf).upper()] = bars
            if len(bars) >= 50:
                step = 1 if str(tf).upper() in {"M30", "M15", "M5", "M1"} else 2
                events_by_tf[str(tf).upper()] = detect_base_departures(bars, str(tf).upper(),
                                                                        scan_step=step, horizon=0)
            else:
                events_by_tf[str(tf).upper()] = []
        engine = HierarchicalBaseBehaviorEngine()
        model_dir = "mt5_gold_history_full" if symbol.upper() in {"XAUUSD", "GOLD"} else f"mt5_{symbol.lower()}_history_full"
        model_path = _PROJECT_ROOT / "runtime_logs" / model_dir / "hierarchical_base_behavior_model_research.json"
        try:
            if model_path.exists():
                model = json.loads(model_path.read_text(encoding="utf-8"))
                if model.get("detector_version") == "base_geometry_price_only_v2":
                    engine.load_stats(model)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Invalid/missing evidence fails closed; no alternative strategy is tried.
            pass
        price = float(candles[-1]["close"])
        pip_factor = 0.1 if "XAU" in symbol.upper() else (1.0 if "BTC" in symbol.upper() else 0.0001)
        spread = max(0.0, float(spread_pip)) * pip_factor
        quote = {"bid": price - spread / 2, "ask": price + spread / 2}
        hierarchy = engine.analyze(events_by_tf, quote, now=float(latest_epoch))
        reaction_engine = BaseReactionDecisionEngine()
        reaction_model_path = _PROJECT_ROOT / "runtime_logs" / model_dir / "base_reaction_behavior_model_research.json"
        reaction_model_status = "MISSING_COSTED_REACTION_MODEL"
        try:
            if reaction_model_path.exists():
                reaction_model = json.loads(reaction_model_path.read_text(encoding="utf-8"))
                if reaction_model.get("detector_version") != "base_geometry_price_only_v2":
                    reaction_model_status = "REACTION_MODEL_DETECTOR_VERSION_MISMATCH"
                else:
                    reaction_engine.load_stats(reaction_model)
                    reaction_model_status = "COSTED_REACTION_MODEL_LOADED"
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            reaction_model_status = "REACTION_MODEL_LOAD_FAILED"
        structure = hierarchy.get("structure") or {}
        all_events = {str(e.get("event_id")): e for group in events_by_tf.values() for e in group}
        parent = all_events.get(str(structure.get("parent_base_id")))
        child = all_events.get(str(structure.get("child_base_id")))
        micro = all_events.get(str(structure.get("micro_base_id")))
        reaction_result = {"status": "WAIT", "reason": "Confirmed parent/child/M1 structure and costed reaction model are required.",
                           "execution_enabled": False, "model_status": reaction_model_status}
        if parent and child and micro and reaction_model_status == "COSTED_REACTION_MODEL_LOADED":
            tf = str(child.get("timeframe", "M15"))
            low, high = float(child["base_low"]), float(child["base_high"])
            confirm = int(child["confirmation_time"])
            measured_reaction = self._measure_latest_base_reaction(
                bars_by_tf.get("M1", []), child, int(latest_epoch))
            direction_sign = int(child.get("exit_direction", 0))
            base_width = float(child.get("base_width", child.get("base_atr", 0.0)))
            stop = low - 0.15 * base_width if direction_sign > 0 else high + 0.15 * base_width
            child_confirmation = int(child.get("confirmation_time", 0))
            known_destination_events = sorted(
                [event for event in events_by_tf.get(tf, [])
                 if event.get("event_id") != child.get("event_id")
                 and int(event.get("confirmation_time", 0)) <= child_confirmation],
                key=lambda event: int(event.get("confirmation_time", 0)),
            )[-512:]
            destinations = []
            for event in known_destination_events:
                if direction_sign > 0 and float(event["base_low"]) > max(high, price):
                    destinations.append((float(event["base_low"]) - price, float(event["base_low"])))
                elif direction_sign < 0 and float(event["base_high"]) < min(low, price):
                    destinations.append((price - float(event["base_high"]), float(event["base_high"])))
            target = min(destinations, key=lambda item: item[0])[1] if destinations else (
                price + (1 if direction_sign > 0 else -1) * 3.0 * abs(price-stop))
            reaction_result = reaction_engine.evaluate(
                setup={"timeframe": tf, "base_type": str(child.get("base_type", "UNKNOWN")),
                       "parent_relation": str(structure.get("parent_relation", "NESTED")),
                       "setup_type": "RETEST", "zone_low": low, "zone_high": high,
                       "invalidation": stop, "target": target, "base_width": base_width,
                       "atr": base_width, "confidence": 100.0,
                       "expires_at": float(latest_epoch) + 8 * TIMEFRAME_SECONDS.get(tf, 60)},
                quote=quote, now=float(latest_epoch), parent=parent, child=child, micro=micro,
                reaction={"base_id": child.get("event_id"),
                          "reaction_number": int(measured_reaction["reaction_number"]) if measured_reaction else 0,
                          "penetration_fraction": float(measured_reaction["penetration_fraction"]) if measured_reaction else -1.0,
                          "entry_side": str(measured_reaction["entry_side"]) if measured_reaction else "ANY"},
            )
            reaction_result["model_status"] = reaction_model_status
        plan = reaction_result.get("order_plan") or {"status": "WAIT", "reason": reaction_result.get("reason")}
        candidates = []
        if reaction_result.get("status") == "ENTRY_PROPOSAL" and plan.get("status") == "PROPOSED":
            candidate = {
                "strategy_id": f"BASE-{symbol.upper()}-{primary_timeframe.upper()}-{latest_epoch}",
                "strategy_name": "BASE_HIERARCHY", "symbol": symbol.upper(),
                "timeframe": str(primary_timeframe).upper(), "direction": plan.get("direction", "WAIT"),
                "entry": float(plan.get("entry") or 0), "stop_loss": float(plan.get("stop_loss") or 0),
                "take_profit": float(plan.get("take_profit") or 0),
                "risk_reward": float(plan.get("net_reward_risk") or 0),
                "confidence": round(100.0 * float(((reaction_result.get("structure") or {}).get("profile_stats") or {}).get("win_rate", 0.0)), 2),
                "reasoning": [str(reaction_result.get("reason") or "Validated Base re-entry reaction proposal.")],
                "market_context": {"strategy": "BASE_HIERARCHY", "order_type": plan.get("order_type"),
                                   "base_structure": reaction_result.get("structure")},
                "invalidation_level": float(plan.get("stop_loss") or 0),
                "holding_period": "Base-reaction / next-Base",
            }
            candidates.append(candidate)
        return {"symbol": symbol.upper(), "primary_timeframe": primary_timeframe,
                "candidates": candidates, "active_candidates_count": len(candidates),
                "best_candidate": candidates[0] if candidates else None,
                "base_plan": plan, "hierarchy": hierarchy, "reaction_analysis": reaction_result,
                "model_status": reaction_model_status,
                "summary": "Only the hierarchical Base plus costed re-entry reaction model can emit a signal; no fallback strategy is available."}
