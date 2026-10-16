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
import os

from src.Decision.Intelligence.hierarchical_base_behavior_engine import HierarchicalBaseBehaviorEngine
from src.Decision.Intelligence.base_reaction_decision_engine import BaseReactionDecisionEngine
from src.Decision.Intelligence.pending_order_planner import PendingOrderPlanner
from src.Research.Brain.multitimeframe_base_transition_engine import TIMEFRAME_SECONDS
from src.Research.Brain.multitimeframe_base_transition_engine import detect_base_departures
from src.Intelligence.Execution.historical_structure_research import analyze_historical_structure_levels

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

    @staticmethod
    def _plan_in_base_rotation(child: Dict[str, Any], bars: List[Dict[str, Any]],
                               quote: Dict[str, float], now: int,
                               spread_allowance: float,
                               trigger_timeframe: str = "M1") -> Optional[Dict[str, Any]]:
        """DEMO-exploration only: sample directional closed M1 candles inside a Base.

        Candle direction selects BUY/SELL while the quote remains inside a confirmed
        Base. The opposite Base edge is only a reward estimate; the exploratory
        path bypasses minimum R:R but retains quote geometry, expiry, and protective
        SL checks. PendingOrderPlanner never returns a broker TP.
        """
        try:
            low, high = float(child["base_low"]), float(child["base_high"])
            width = high - low
            confirm = int(child["confirmation_time"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(width) or width <= 0 or now <= confirm:
            return None
        bid, ask = float(quote.get("bid", 0)), float(quote.get("ask", 0))
        mid = (bid + ask) / 2.0
        if bid <= 0 or ask < bid:
            return None
        trigger_tf = str(trigger_timeframe or "M1").upper()
        trigger_seconds = TIMEFRAME_SECONDS.get(trigger_tf, 60)
        recent = [bar for bar in bars if confirm < int(bar.get("time", 0)) <= now
                  and now - int(bar.get("time", 0)) <= 24 * trigger_seconds]
        if not recent:
            return None
        bar = recent[-1]
        o, h, l, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
        if not all(math.isfinite(v) for v in (o, h, l, c)) or h < l or not l <= c <= h:
            return None
        direction = None
        entry = target = stop = None
        # Exploration samples directional rotations anywhere inside the confirmed
        # Base, not only edge rejections. This is deliberately not treated as a
        # validated edge or profitability claim; broker geometry still applies.
        # Keep exploration sampling even when price has left the zone: use a
        # broker-side limit retest of the Base rather than requiring price to sit
        # inside it at the exact polling instant.
        if mid > high:
            direction = "BUY"
        elif mid < low:
            direction = "SELL"
        elif mid >= low + 0.65 * width:
            # Price in the upper part leaves room for a lower BUY_LIMIT retest.
            direction = "BUY"
        elif mid <= low + 0.35 * width:
            # Price in the lower part leaves room for an upper SELL_LIMIT retest.
            direction = "SELL"
        elif c > o:
            direction = "BUY"
        elif c < o:
            direction = "SELL"
        else:
            direction = "BUY" if mid <= (low + high) / 2.0 else "SELL"
        if direction == "BUY":
            entry = min(low + 0.15 * width, ask - 0.06 * width)
            target = high
            stop = low - max(0.10 * width, 1.5 * (ask - bid))
        else:
            entry = max(high - 0.15 * width, bid + 0.06 * width)
            target = low
            stop = high + max(0.10 * width, 1.5 * (ask - bid))
        if not low < entry < high:
            return None
        # Exploration is deliberately permissive on confidence, spread/Base ratio,
        # and R:R; broker-side price/volume/stops validation remains authoritative.
        planner = PendingOrderPlanner(
            min_confidence=0.0, min_net_rr=0.0,
            max_spread_base_width_ratio=1e9,
            enforce_min_net_rr=False,
        )
        result = planner.plan({
            "direction": direction, "setup_type": "RETEST",
            "zone_low": low, "zone_high": high, "entry_price": entry,
            "invalidation": stop, "target": target, "base_width": width,
            "confidence": 100.0, "expires_at": None,
            "slippage_allowance": max(0.0, spread_allowance * 0.25),
        }, quote, now=float(now)).to_dict()
        if result.get("status") != "PROPOSED":
            return None
        result["setup_type"] = "IN_BASE_ROTATION"
        result["reason"] = ("DEMO EXPLORATION ONLY: directional closed candle inside a confirmed Base; "
                            "candidate generation may relax the research R:R floor, but the execution-stage "
                            "10% daily-loss gate, 1% per-trade sizing, broker validation, and protective SL/TP "
                            "remain mandatory.")
        return result

    def evaluate_all_strategies(
        self, symbol: str, primary_timeframe: str, candles: List[Dict[str, Any]],
        all_timeframe_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        narrative: Optional[Dict[str, Any]] = None, liquidity: Optional[Dict[str, Any]] = None,
        zones: Optional[Dict[str, Any]] = None, alignment: Optional[Dict[str, Any]] = None,
        similarity: Optional[Dict[str, Any]] = None, fractal: Optional[Dict[str, Any]] = None,
        spread_pip: float = 1.0, account_balance: float = 10000.0,
        exploration_mode: bool = False,
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
        historical_structure = analyze_historical_structure_levels(
            bars_by_tf, now=int(datetime.now().timestamp()),
            current_prices={tf: rows[-1]["close"] for tf, rows in bars_by_tf.items() if rows},
        )
        demo_exploration = bool(exploration_mode) or (
            os.environ.get("YARTRADER_DEMO_EXPLORATION_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
            and os.environ.get("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
            and os.environ.get("YARTRADER_TRADING_MODE", "").strip().upper() == "DEMO"
        )
        engine = HierarchicalBaseBehaviorEngine()
        model_dir = "mt5_gold_history_full" if symbol.upper() in {"XAUUSD", "GOLD"} else f"mt5_{symbol.lower()}_history_full"
        model_path = _PROJECT_ROOT / "runtime_logs" / model_dir / "hierarchical_base_behavior_model_research.json"
        try:
            if model_path.exists():
                model = json.loads(model_path.read_text(encoding="utf-8"))
                if (model.get("detector_version") == "base_geometry_price_only_v2"
                        and model.get("model_schema_version") == "base_only_directional_net_r_v3"
                        and model.get("status") == "ACTIVE_VALIDATED"):
                    engine.load_stats(model)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Invalid/missing evidence fails closed; no alternative strategy is tried.
            pass
        price = float(candles[-1]["close"])
        pip_factor = 0.1 if "XAU" in symbol.upper() else (1.0 if "BTC" in symbol.upper() else 0.0001)
        spread = max(0.0, float(spread_pip)) * pip_factor
        quote = {"bid": price - spread / 2, "ask": price + spread / 2}
        hierarchy = engine.analyze(events_by_tf, quote, now=float(latest_epoch), exploration_mode=demo_exploration)
        # Attach causal swing levels and measured historical reactions to the same
        # context consumed by the Base/reaction decision path and its diagnostics.
        hierarchy["historical_structure_analysis"] = historical_structure
        if demo_exploration:
            # DEMO/backtest-only trigger fallback: derive an explicit exploratory M1
            # trigger from a real closed candle that touches the selected child Base
            # and closes directionally back outside it. No synthetic prices are used.
            structure = hierarchy.get("structure") or {}
            child_id = str(structure.get("child_base_id") or "")
            child = next((event for group in events_by_tf.values() for event in group
                          if str(event.get("event_id")) == child_id), None)
            if child and not structure.get("micro_base_id"):
                child_low, child_high = float(child["base_low"]), float(child["base_high"])
                child_confirm = int(child.get("confirmation_time", 0))
                child_direction = int(child.get("exit_direction", 0))
                for bar in reversed(bars_by_tf.get("M1", [])[-24:]):
                    stamp = int(bar.get("time", 0))
                    if stamp < child_confirm or latest_epoch - stamp > 24 * TIMEFRAME_SECONDS["M1"]:
                        continue
                    touched = float(bar["low"]) <= child_high and float(bar["high"]) >= child_low
                    directional_rejection = (
                        child_direction > 0 and float(bar["close"]) > float(bar["open"]) and float(bar["close"]) > child_high
                    ) or (
                        child_direction < 0 and float(bar["close"]) < float(bar["open"]) and float(bar["close"]) < child_low
                    )
                    quote_confirmed_breakout = (
                        child_direction > 0 and float(bar["close"]) > float(bar["open"])
                        and float(quote.get("ask", 0.0)) > child_high
                    ) or (
                        child_direction < 0 and float(bar["close"]) < float(bar["open"])
                        and float(quote.get("bid", 0.0)) < child_low
                    )
                    directional_candle = (
                        child_direction > 0 and float(bar["close"]) > float(bar["open"])
                    ) or (
                        child_direction < 0 and float(bar["close"]) < float(bar["open"])
                    )
                    quote_mid = (float(quote.get("ask", 0.0)) + float(quote.get("bid", 0.0))) / 2.0
                    quote_inside_zone = child_low <= quote_mid <= child_high
                    trigger_mode = (
                        "RETEST_REJECTION" if touched and directional_rejection
                        else "BREAKOUT_CONTINUATION" if quote_confirmed_breakout
                        else "IN_ZONE_EXPLORATION" if touched and directional_candle and quote_inside_zone
                        else None
                    )
                    if trigger_mode is None:
                        continue
                    trigger = {
                        "event_id": f"EXPLORATION_M1_CANDLE_{stamp}_{child_direction}",
                        "timeframe": "M1", "base_type": "EXPLORATION_CANDLE_TRIGGER",
                        "exploration_trigger_mode": trigger_mode,
                        "base_start_time": stamp, "base_end_time": stamp,
                        "confirmation_time": stamp, "base_low": float(bar["low"]),
                        "base_high": float(bar["high"]),
                        "base_mid": (float(bar["low"]) + float(bar["high"])) / 2.0,
                        "base_width": max(0.0, float(bar["high"]) - float(bar["low"])),
                        "exit_direction": child_direction,
                        "exploration_only": True,
                    }
                    events_by_tf.setdefault("M1", []).append(trigger)
                    hierarchy = engine.analyze(
                        events_by_tf, quote, now=float(latest_epoch), exploration_mode=True
                    )
                    break
        reaction_engine = BaseReactionDecisionEngine(
            planner=PendingOrderPlanner(enforce_min_net_rr=not demo_exploration),
            min_reverse_net_rr=(0.0 if demo_exploration else 1.0),
        )
        reaction_model_path = _PROJECT_ROOT / "runtime_logs" / model_dir / "base_reaction_behavior_model_research.json"
        reaction_model_status = "MISSING_COSTED_REACTION_MODEL"
        try:
            if reaction_model_path.exists():
                reaction_model = json.loads(reaction_model_path.read_text(encoding="utf-8"))
                if (reaction_model.get("detector_version") != "base_geometry_price_only_v2"
                        or reaction_model.get("model_schema_version") != "base_only_directional_net_r_v3"):
                    reaction_model_status = "REACTION_MODEL_SCHEMA_VERSION_MISMATCH"
                elif reaction_model.get("status") != "ACTIVE_VALIDATED":
                    reaction_model_status = "REACTION_MODEL_NOT_ACTIVATED"
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
        if demo_exploration and child is None:
            # Research sampling must not require a complete parent/child hierarchy.
            # Fall back to the most recently confirmed real Base from M15/M5/M1.
            eligible = [
                event for tf in ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
                for event in events_by_tf.get(tf, [])
                if event.get("base_low") is not None and event.get("base_high") is not None
                and int(event.get("confirmation_time", 0) or 0) < int(latest_epoch)
                and float(event.get("base_high", 0) or 0) > float(event.get("base_low", 0) or 0)
            ]
            if eligible:
                child = max(eligible, key=lambda event: int(event.get("confirmation_time", 0) or 0))
                structure = dict(structure)
                structure["child_base_id"] = child.get("event_id")
                structure["child_timeframe"] = child.get("timeframe")
                structure["exploration_child_fallback"] = True
        reaction_result = {"status": "WAIT", "reason": "Confirmed parent/child/M1 structure and costed reaction model are required.",
                           "execution_enabled": False, "model_status": reaction_model_status}
        if parent and child and micro and (reaction_model_status == "COSTED_REACTION_MODEL_LOADED" or demo_exploration):
            tf = str(child.get("timeframe", "M15"))
            low, high = float(child["base_low"]), float(child["base_high"])
            confirm = int(child["confirmation_time"])
            measured_reaction = self._measure_latest_base_reaction(
                bars_by_tf.get("M1", []), child, int(latest_epoch))
            if measured_reaction is None and demo_exploration and micro and micro.get("exploration_only"):
                # This is an explicitly tagged breakout/rejection sample, not a
                # measured historical retest; never publish it as validated evidence.
                zone_low = float(child["base_low"])
                zone_high = float(child["base_high"])
                zone_width = max(zone_high - zone_low, 1e-9)
                if int(child.get("exit_direction", 0)) > 0:
                    exploratory_depth = (zone_high - float(quote.get("ask", zone_high))) / zone_width + 0.1
                else:
                    exploratory_depth = (float(quote.get("bid", zone_low)) - zone_low) / zone_width + 0.1
                exploratory_depth = min(0.9, max(0.1, exploratory_depth))
                measured_reaction = {
                    "reaction_number": 1, "penetration_fraction": exploratory_depth,
                    "entry_side": "ANY", "exploration_only": True,
                }
            direction_sign = int(child.get("exit_direction", 0))
            base_width = float(child.get("base_width", 0.0))
            stop = low - 0.15 * base_width if direction_sign > 0 else high + 0.15 * base_width
            # Destination Bases may form after the source Base, but must be fully
            # confirmed before the current decision candle; never freeze targets
            # at the older source-Base confirmation timestamp.
            decision_time = int(latest_epoch)
            # Search every available timeframe for the nearest confirmed destination
            # Base. Restricting targets to the child timeframe misses valid H1/H4/D1
            # objectives (especially on XAUUSD) and can leave a stale or undersized TP
            # after the execution layer widens a structural stop.
            all_destination_events = []
            seen_destination_ids = set()
            for destination_tf, tf_events in events_by_tf.items():
                for event in tf_events:
                    event_id = str(event.get("event_id") or "")
                    if (not event_id or event_id == str(child.get("event_id") or "")
                            or event_id in seen_destination_ids):
                        continue
                    try:
                        confirmed_at = int(event.get("confirmation_time", 0))
                        base_low = float(event["base_low"])
                        base_high = float(event["base_high"])
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue
                    if confirmed_at <= decision_time and base_low > 0 and base_high >= base_low:
                        candidate = dict(event)
                        candidate["_target_timeframe"] = str(event.get("timeframe") or destination_tf).upper()
                        all_destination_events.append(candidate)
                        seen_destination_ids.add(event_id)
            if direction_sign > 0:
                known_destination_events = sorted(
                    (event for event in all_destination_events if float(event["base_low"]) > high),
                    key=lambda event: float(event["base_low"]),
                )[:64]
            else:
                known_destination_events = sorted(
                    (event for event in all_destination_events if float(event["base_high"]) < low),
                    key=lambda event: float(event["base_high"]), reverse=True,
                )[:64]
            destinations = []
            for event in known_destination_events:
                if direction_sign > 0 and float(event["base_low"]) > max(high, price):
                    destinations.append((float(event["base_low"]) - price, float(event["base_low"]), event))
                elif direction_sign < 0 and float(event["base_high"]) < min(low, price):
                    destinations.append((price - float(event["base_high"]), float(event["base_high"]), event))
            # Prefer the next confirmed structural Base as target. In explicit DEMO
            # exploration only, if no destination Base exists, derive the smallest
            # cost-aware target that still clears strict net reward/risk > 1.0.
            # This is not a fixed-R target and does not relax quote, geometry, or
            # broker-risk checks. Production/validated mode still waits for structure.
            selected_destination = min(destinations, key=lambda item: item[0]) if destinations else None
            target = selected_destination[1] if selected_destination else None
            target_event = selected_destination[2] if selected_destination else None
            target_source = "CONFIRMED_DESTINATION_BASE" if target_event else "DEMO_EXPLORATION_COST_AWARE_FALLBACK"
            target_timeframe = str(target_event.get("_target_timeframe") or target_event.get("timeframe") or "UNKNOWN") if target_event else None
            trigger_mode = str(micro.get("exploration_trigger_mode", "")) if micro else ""
            # A quote-confirmed breakout has already crossed the Base edge. Do not
            # submit a stale stop-chase; in DEMO exploration sample the pullback
            # with a RETEST limit inside the confirmed Base instead.
            setup_type = ("RETEST" if demo_exploration and trigger_mode == "BREAKOUT_CONTINUATION"
                          else "BREAKOUT" if trigger_mode == "BREAKOUT_CONTINUATION" else "RETEST")
            if target is None and demo_exploration:
                # Use the least favorable valid entry edge and current executable
                # quote, so TP is beyond both the planned entry and current market.
                planned_entry = high if direction_sign > 0 else low
                spread_cost = max(0.0, float(quote["ask"]) - float(quote["bid"]))
                extra_cost = max(0.0, 0.1 * spread_cost)
                risk_distance = abs(planned_entry - stop)
                target_distance = risk_distance + 2.0 * (spread_cost + extra_cost) + max(0.01, risk_distance * 0.01)
                target_anchor = max(planned_entry, float(quote["ask"])) if direction_sign > 0 else min(planned_entry, float(quote["bid"]))
                target = target_anchor + (1 if direction_sign > 0 else -1) * target_distance
                target_source = "DEMO_EXPLORATION_COST_AWARE_FALLBACK"
                target_timeframe = None
            reaction_result = reaction_engine.evaluate(
                setup={"timeframe": tf, "base_type": str(child.get("base_type", "UNKNOWN")),
                       "parent_relation": str(structure.get("parent_relation", "NESTED")),
                       "hierarchy_chain": list(structure.get("hierarchy_chain", [])),
                       "hierarchy_complete_to_m1": bool(structure.get("hierarchy_complete_to_m1", False)),
                       "setup_type": setup_type,
                       "entry_price": price, "zone_low": low, "zone_high": high,
                       "invalidation": stop, "target": target, "target_source": target_source,
                       "target_timeframe": target_timeframe,
                       "target_event_id": str(target_event.get("event_id")) if target_event else None,
                       "base_width": base_width,
                       "confidence": 100.0,
                       "expires_at": float(latest_epoch) + 8 * TIMEFRAME_SECONDS.get(tf, 60)},
                quote=quote, now=float(latest_epoch), parent=parent, child=child, micro=micro,
                reaction={"base_id": child.get("event_id"),
                          "reaction_number": int(measured_reaction["reaction_number"]) if measured_reaction else 0,
                          "penetration_fraction": float(measured_reaction["penetration_fraction"]) if measured_reaction else -1.0,
                          "entry_side": str(measured_reaction["entry_side"]) if measured_reaction else "ANY"},
                exploration_mode=demo_exploration,
            )
            reaction_result["model_status"] = reaction_model_status
            reaction_result["target_source"] = target_source
            reaction_result["target_timeframe"] = target_timeframe
            reaction_result["target_event_id"] = str(target_event.get("event_id")) if target_event else None
            reaction_result["structural_target_candidates"] = [
                {"price": float(item[1]), "timeframe": str(item[2].get("_target_timeframe") or item[2].get("timeframe") or "UNKNOWN"),
                 "event_id": str(item[2].get("event_id") or ""), "distance_from_decision_price": float(item[0]),
                 "confirmation_time": int(item[2].get("confirmation_time", 0))}
                for item in sorted(destinations, key=lambda value: value[0])
            ]

        # Separate Base-interior rotation path. It is deliberately available only
        # in explicitly enabled DEMO exploration until costed historical profiles
        # for this setup are validated; it never sets a broker TP.
        if (demo_exploration and reaction_result.get("status") != "ENTRY_PROPOSAL"
                and parent and child and micro
                and bool(structure.get("hierarchy_complete_to_m1"))):
            # Prefer M1 triggers, but historical DEMO/backtest exploration may
            # have sparse or unavailable M1 history for older train windows. Use
            # the finest real, causally available closed timeframe with a recent
            # bar after Base confirmation instead of silently producing zero trades.
            trigger_tf = None
            trigger_bars = []
            for candidate_tf in ("M1", "M5", "M15", "M30", str(primary_timeframe).upper(), "H1", "H4"):
                candidate_bars = bars_by_tf.get(candidate_tf, [])
                seconds = TIMEFRAME_SECONDS.get(candidate_tf, 60)
                if any(
                    int(bar.get("time", 0)) > int(child.get("confirmation_time", 0))
                    and int(bar.get("time", 0)) <= int(latest_epoch)
                    and int(latest_epoch) - int(bar.get("time", 0)) <= 24 * seconds
                    for bar in candidate_bars
                ):
                    trigger_tf, trigger_bars = candidate_tf, candidate_bars
                    break
            in_base_plan = self._plan_in_base_rotation(
                child, trigger_bars, quote, int(latest_epoch), spread,
                trigger_timeframe=trigger_tf or "M1",
            ) if trigger_tf else None
            if in_base_plan:
                reaction_result = {
                    "status": "ENTRY_PROPOSAL",
                    "reason": in_base_plan.get("reason"),
                    "structure": {
                        "strategy_type": "IN_BASE_ROTATION",
                        "parent_id": parent.get("event_id") if parent else None,
                        "child_id": child.get("event_id"),
                        "timeframe": child.get("timeframe"),
                        "base_low": float(child["base_low"]),
                        "base_high": float(child["base_high"]),
                        "trigger": "CLOSED_M1_EDGE_REJECTION",
                        "validated_historical_edge": False,
                    },
                    "scenario": {"setup_type": "IN_BASE_ROTATION"},
                    "order_plan": in_base_plan,
                    "execution_enabled": False,
                    "model_status": reaction_model_status,
                    "exploration_only": True,
                }

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
                "confidence": (100.0 if reaction_result.get("exploration_only") else
                               round(100.0 * float(((reaction_result.get("structure") or {}).get("profile_stats") or {}).get("win_rate", 0.0)), 2)),
                "reasoning": [str(reaction_result.get("reason") or "Validated Base re-entry reaction proposal.")],
                "market_context": {"strategy": str((reaction_result.get("structure") or {}).get("strategy_type") or "BASE_HIERARCHY"),
                                   "order_type": plan.get("order_type"),
                                   "base_structure": reaction_result.get("structure"),
                                   "historical_structure_analysis": historical_structure},
                "invalidation_level": float(plan.get("stop_loss") or 0),
                "holding_period": "Base-reaction / next-Base",
            }
            candidates.append(candidate)
        return {"symbol": symbol.upper(), "primary_timeframe": primary_timeframe,
                "candidates": candidates, "active_candidates_count": len(candidates),
                "best_candidate": candidates[0] if candidates else None,
                "base_plan": plan, "hierarchy": hierarchy, "reaction_analysis": reaction_result,
                "historical_structure_analysis": historical_structure,
                "model_status": reaction_model_status,
                "exploration_mode": demo_exploration,
                "summary": ("DEMO/BACKTEST EXPLORATION: unvalidated profiles are sampled; results are not evidence of profitability."
                            if demo_exploration else
                            "Only the hierarchical Base plus costed re-entry reaction model can emit a signal; no fallback strategy is available.")}
