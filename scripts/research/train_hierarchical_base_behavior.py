"""Walk-forward research for hierarchical parent/child Base retest orders.

No broker interaction. The script simulates limit-entry retests, conservative stop/target
ordering, ATR-based round-trip cost sensitivity, and only learns from outcomes completed
before each subsequent signal. Results are an event study; overlapping trades are not
portfolio-constrained and cost is a proxy, not broker execution data.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import csv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Research.Brain.multitimeframe_base_transition_engine import (
    TIMEFRAME_ORDER, detect_base_departures, label_exit_to_next_base,
    _bar_end_time,
)

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
FILES = ("MN1", "W1", "D1", "H4", "H1", "M15", "M5", "M1")
STEPS = {"MN1": 1, "W1": 1, "D1": 1, "H4": 2, "H1": 2, "M15": 5, "M5": 10, "M1": 10}
CHILD_TFS = {"M15": 48, "M5": 96}


def load_bars(tf: str, max_bars: int) -> List[Dict[str, Any]]:
    """Read chronological OHLC rows without pandas or a second full-frame copy."""
    path = DATA / (tf + ".csv")
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        time_col = "time" if "time" in fields else "timestamp" if "timestamp" in fields else None
        if time_col is None or not {"open", "high", "low", "close"}.issubset(fields):
            return []
        limit = max_bars if max_bars > 0 else None
        rows = deque(maxlen=limit)
        last_time = None
        for raw in reader:
            try:
                t = int(float(raw[time_col]))
                row = {"time": t, "open": float(raw["open"]), "high": float(raw["high"]),
                       "low": float(raw["low"]), "close": float(raw["close"])}
            except (TypeError, ValueError, KeyError, OverflowError):
                continue
            if not all(math.isfinite(row[k]) for k in ("open", "high", "low", "close")):
                continue
            # Source history is chronological; fail closed rather than silently
            # mis-handle a non-monotonic file while retaining only the tail.
            if last_time is not None and t < last_time:
                raise ValueError(f"{path} is not sorted by {time_col}: {t} < {last_time}")
            if t == last_time:
                continue
            rows.append(row)
            last_time = t
    return list(rows)


def key_for(event: Mapping[str, Any], label: Mapping[str, Any]) -> str:
    parent_tf = str(label.get("parent_timeframe") or "NONE")
    aligned = bool(label.get("parent_aligned", False))
    relation = str(label.get("parent_relation") or "NESTED")
    reaction_number = int(label.get("reaction_number", 1))
    depth_bin = str(label.get("penetration_bin", "MIDPOINT"))
    return "{}|{}|{}|{}|{}|{}|{}".format(event["timeframe"], event["base_type"], parent_tf,
        relation, "ALIGNED" if aligned else "OPPOSED", reaction_number, depth_bin)


def simulate_pending_retest(event: Mapping[str, Any], label: Mapping[str, Any],
                            target_event: Mapping[str, Any] | None, bars: Sequence[Mapping[str, Any]],
                            bar_times: Sequence[int], activation_time: int, trigger_id: str,
                            round_trip_cost_atr: float, penetration_fraction: float = 0.5,
                            target_reaction_number: int = 1) -> Dict[str, Any] | None:
    tf = str(event["timeframe"])
    if tf not in ("M15", "M5"):
        return None
    direction = int(event["exit_direction"])
    if direction not in (-1, 1) or not bool(label.get("parent_aligned")):
        return None
    low, high = float(event["base_low"]), float(event["base_high"])
    atr = float(event["base_atr"])
    if atr <= 0:
        return None
    if not 0.0 <= float(penetration_fraction) <= 1.0 or int(target_reaction_number) < 1:
        return None
    # Penetration is measured from the near edge toward the far edge in the
    # direction of the Base departure, so 0 is shallow and 1 is deep.
    entry = (high - penetration_fraction * (high-low)) if direction > 0 else (low + penetration_fraction * (high-low))
    stop = low - 0.15 * atr if direction > 0 else high + 0.15 * atr
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    target_source = "PREVIOUSLY_KNOWN_DESTINATION_BASE"
    if target_event is not None:
        target = float(target_event["base_low"] if direction > 0 else target_event["base_high"])
    else:
        target = entry + direction * 3.0 * risk
        target_source = "STRUCTURAL_3R_FALLBACK"
    if (direction > 0 and not stop < entry < target) or (direction < 0 and not target < entry < stop):
        target = entry + direction * 3.0 * risk
        target_source = "STRUCTURAL_3R_FALLBACK"
    if (direction > 0 and not stop < entry < target) or (direction < 0 and not target < entry < stop):
        return None

    # Orders cannot fill on the M1 trigger candle: it is only known at its close.
    # Start strictly after signal time, and include the trigger candle in prior-visit counting.
    activation_index = bisect_right(bar_times, int(activation_time))
    expiry_time = int(activation_time) + 8 * (900 if tf == "M15" else 300)
    expiry_index = min(len(bars) - 1, bisect_right(bar_times, expiry_time) - 1)
    if activation_index >= len(bars) or expiry_index < activation_index:
        return None
    # Count completed Base-zone visits since the child Base confirmation, then
    # number future visits globally rather than restarting the counter at M1.
    # Exclude the confirmation candle itself, matching live visit counting.
    confirm_index = bisect_right(bar_times, int(event["confirmation_time"]))
    prior_visits = 0
    in_zone_visit = False
    for j in range(confirm_index, min(activation_index, len(bars))):
        b = bars[j]
        zone_touch = float(b["low"]) <= high and float(b["high"]) >= low
        if zone_touch and not in_zone_visit:
            prior_visits += 1
        in_zone_visit = zone_touch
    desired_total_reaction = prior_visits + int(target_reaction_number)
    fill_index = None
    reaction_number = prior_visits
    for j in range(activation_index, expiry_index + 1):
        b = bars[j]
        zone_touch = float(b["low"]) <= high and float(b["high"]) >= low
        if zone_touch and not in_zone_visit:
            reaction_number += 1
        in_zone_visit = zone_touch
        if reaction_number != desired_total_reaction:
            continue
        if float(b["low"]) <= entry <= float(b["high"]):
            fill_index = j
            break
    if fill_index is None or fill_index + 1 >= len(bars):
        return None

    active_stop = stop
    favorable = entry
    inside_count = 0
    hold_bars = 720 if tf == "M15" else 480
    max_index = min(len(bars) - 1, fill_index + hold_bars)
    exit_price = float(bars[max_index]["close"])
    exit_index = max_index
    exit_reason = "evaluation_horizon_close"
    for j in range(fill_index + 1, max_index + 1):
        b = bars[j]
        hi, lo, close = float(b["high"]), float(b["low"]), float(b["close"])
        stop_hit = lo <= active_stop if direction > 0 else hi >= active_stop
        target_hit = hi >= target if direction > 0 else lo <= target
        if stop_hit:
            exit_price, exit_index, exit_reason = active_stop, j, "stop_or_trail"
            break
        if target_hit:
            exit_price, exit_index, exit_reason = target, j, "destination_base"
            break
        if direction > 0:
            favorable = max(favorable, hi)
            best_move = favorable - entry
        else:
            favorable = min(favorable, lo)
            best_move = entry - favorable
        if best_move >= risk:
            active_stop = max(active_stop, entry) if direction > 0 else min(active_stop, entry)
        if best_move >= 1.5 * risk:
            trail = favorable - direction * 2.5 * atr
            active_stop = max(active_stop, trail) if direction > 0 else min(active_stop, trail)
        inside = low <= close <= high
        inside_count = inside_count + 1 if inside else 0
        if inside_count >= 2 and direction * (close - entry) > 0:
            exit_price, exit_index, exit_reason = close, j, "profitable_return_inside_origin_base"
            break

    gross_r = direction * (exit_price - entry) / risk
    cost_r = round_trip_cost_atr * atr / risk
    net_r = gross_r - cost_r
    return {
        "event_id": event["event_id"], "timeframe": tf, "base_type": event["base_type"],
        "parent_timeframe": label.get("parent_timeframe") or "NONE",
        "parent_relation": label.get("parent_relation") or "NONE",
        "parent_aligned": bool(label.get("parent_aligned")),
        "reaction_number": int(desired_total_reaction),
        "penetration_fraction": float(penetration_fraction),
        "penetration_bin": ("EDGE" if penetration_fraction < 0.25 else "OUTER" if penetration_fraction < 0.5 else "INNER" if penetration_fraction < 0.75 else "FAR_EDGE"),
        "signal_time": int(activation_time), "child_base_confirmation_time": int(event["confirmation_time"]),
        "m1_trigger_id": trigger_id, "label_end_time": _bar_end_time(bars, exit_index, "M1"),
        "fill_time": int(bars[fill_index]["time"]),
        "entry": entry, "stop": stop, "target": target, "target_source": target_source, "exit": exit_price,
        "exit_reason": exit_reason, "first_transition": exit_reason,
        "label_horizon_bars": max(1, exit_index - fill_index),
        "outcome_source": "historical_execution_simulation",
        "gross_R": gross_r, "cost_R_proxy": cost_r, "net_R": net_r,
        "ambiguous_fill_bar_excluded": True,
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"trades": 0}
    values = [float(x["net_R"]) for x in rows]
    gains = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    return {
        "trades": len(rows),
        "win_rate_pct": round(100 * sum(x > 0 for x in values) / len(values), 2),
        "mean_net_R_proxy": round(sum(values) / len(values), 4),
        "profit_factor_proxy": round(gains / losses, 4) if losses else None,
        "exit_reasons": {reason: sum(x["exit_reason"] == reason for x in rows)
                         for reason in sorted({str(x["exit_reason"]) for x in rows})},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1-max-bars", type=int, default=600000)
    parser.add_argument("--out", default=str(DATA / "base_reaction_grid_walkforward.json"))
    parser.add_argument("--model-out", default=str(DATA / "base_reaction_behavior_model_research.json"))
    parser.add_argument("--min-samples", type=int, default=40)
    parser.add_argument("--min-win-rate", type=float, default=0.52)
    parser.add_argument("--min-mean-net-r", type=float, default=0.05)
    parser.add_argument("--round-trip-cost-atr", type=float, default=0.05)
    parser.add_argument("--depth-fractions", default="0.125,0.375,0.625,0.875",
                        help="Comma-separated penetration fractions from near to far edge")
    parser.add_argument("--reaction-numbers", default="1,2,3",
                        help="Comma-separated revisit ordinal after M1 trigger")
    args = parser.parse_args()
    depth_fractions = sorted(set(float(x.strip()) for x in args.depth_fractions.split(",")))
    reaction_numbers = sorted(set(int(x.strip()) for x in args.reaction_numbers.split(",")))
    if not depth_fractions or any(not 0 <= x <= 1 for x in depth_fractions):
        raise ValueError("Depth fractions must be a non-empty list within [0,1].")
    if not reaction_numbers or any(x < 1 or x > 10 for x in reaction_numbers):
        raise ValueError("Reaction numbers must be a non-empty list in [1,10].")

    bars_by_tf, events_by_tf = {}, {}
    for tf in FILES:
        bars = load_bars(tf, args.m1_max_bars if tf == "M1" else 0)
        bars_by_tf[tf] = bars
        events_by_tf[tf] = detect_base_departures(bars, tf, scan_step=STEPS[tf]) if len(bars) >= 50 else []
        print("DATA", tf, "bars", len(bars), "base_events", len(events_by_tf[tf]), flush=True)

    labels = label_exit_to_next_base(events_by_tf, bars_by_tf, horizon_bars=24)
    event_map = {e["event_id"]: e for vals in events_by_tf.values() for e in vals}
    label_map = {x["event_id"]: x for x in labels}
    m1_bars = bars_by_tf.get("M1", [])
    m1_times = [int(b["time"]) for b in m1_bars]
    m1_events = sorted(events_by_tf.get("M1", []), key=lambda x: int(x["confirmation_time"]))
    m1_confirm_times = [int(x["confirmation_time"]) for x in m1_events]
    potential = []
    diagnostics = defaultdict(int)
    for tf in CHILD_TFS:
        tf_seconds = 900 if tf == "M15" else 300
        for event in events_by_tf.get(tf, []):
            diagnostics[tf + "_base_events"] += 1
            label = label_map.get(event["event_id"])
            if not label:
                diagnostics[tf + "_missing_label"] += 1
                continue
            if not label.get("parent_aligned"):
                diagnostics[tf + "_parent_not_aligned"] += 1
                continue
            diagnostics[tf + "_parent_aligned"] += 1
            direction = int(event["exit_direction"])
            start = int(event["confirmation_time"])
            end = start + 8 * tf_seconds
            lo = bisect_left(m1_confirm_times, start)
            hi = bisect_right(m1_confirm_times, end)
            trigger = None
            for micro in m1_events[lo:hi]:
                if int(micro.get("exit_direction", 0)) != direction:
                    continue
                micro_idx = int(micro.get("confirmation_index", -1))
                if micro_idx < 0 or micro_idx >= len(m1_bars):
                    continue
                micro_close = float(m1_bars[micro_idx]["close"])
                if direction > 0 and micro_close <= float(event["base_high"]):
                    continue
                if direction < 0 and micro_close >= float(event["base_low"]):
                    continue
                trigger = micro
                break
            if trigger is None:
                diagnostics[tf + "_no_m1_trigger"] += 1
                continue
            diagnostics[tf + "_m1_triggered"] += 1
            # No look-ahead: target must already be confirmed at the M1 trigger time.
            known_targets = []
            for candidate in events_by_tf.get(tf, []):
                if candidate.get("event_id") == event.get("event_id") or int(candidate.get("confirmation_time", 0)) > int(trigger["confirmation_time"]):
                    continue
                c_low, c_high = float(candidate["base_low"]), float(candidate["base_high"])
                if direction > 0 and c_low > float(event["base_high"]):
                    known_targets.append((c_low, candidate))
                elif direction < 0 and c_high < float(event["base_low"]):
                    known_targets.append((-c_high, candidate))
            target_event = min(known_targets, key=lambda x: x[0])[1] if known_targets else None
            for depth_fraction in depth_fractions:
                for reaction_number in reaction_numbers:
                    outcome = simulate_pending_retest(
                        event, label, target_event, m1_bars, m1_times,
                        int(trigger["confirmation_time"]), str(trigger["event_id"]),
                        args.round_trip_cost_atr, depth_fraction, reaction_number,
                    )
                    if outcome:
                        potential.append(outcome)
                        diagnostics[tf + "_filled"] += 1
                        diagnostics[tf + "_filled_depth_" + outcome["penetration_bin"]] += 1
                        diagnostics[tf + "_filled_reaction_" + str(reaction_number)] += 1
                    else:
                        diagnostics[tf + "_trigger_no_fill_or_invalid_geometry"] += 1
    potential.sort(key=lambda x: (int(x["signal_time"]), x["event_id"]))
    print("POTENTIAL_FILLED_RETURNS", len(potential), flush=True)

    # Event-driven walk-forward: only outcomes that had fully exited before a signal
    # are visible to that signal's learning gate. Outcomes of all eligible patterns
    # inform the estimator, while accepted OOS trades are tracked separately.
    history: Dict[str, List[float]] = defaultdict(list)
    outcomes_by_end = sorted(potential, key=lambda x: (int(x["label_end_time"]), int(x["signal_time"])))
    end_cursor = 0
    accepted = []
    decision_counts = defaultdict(int)
    for row in potential:
        signal_time = int(row["signal_time"])
        while end_cursor < len(outcomes_by_end) and int(outcomes_by_end[end_cursor]["label_end_time"]) < signal_time:
            completed = outcomes_by_end[end_cursor]
            history[key_for(completed, completed)] .append(float(completed["net_R"]))
            end_cursor += 1
        key = key_for(row, row)
        prior = history.get(key, [])
        if len(prior) < args.min_samples:
            decision_counts["insufficient_history"] += 1
            continue
        win_rate = sum(x > 0 for x in prior) / len(prior)
        mean_net = sum(prior) / len(prior)
        net_variance = sum((value - mean_net) ** 2 for value in prior) / (len(prior) - 1) if len(prior) > 1 else 1e18
        mean_net_se = math.sqrt(net_variance / len(prior))
        if (win_rate < args.min_win_rate or mean_net < args.min_mean_net_r
                or mean_net - 2.5 * mean_net_se < args.min_mean_net_r):
            decision_counts["historical_gate_rejected"] += 1
            continue
        decision_counts["walk_forward_accepted"] += 1
        accepted.append(row)

    # Train the research artifact on all outcomes completed before the last observed
    # bar timestamp; this artifact is NOT automatically activated in the trading loop.
    last_ts = max((int(b[-1]["time"]) for b in bars_by_tf.values() if b), default=0)
    trained: Dict[str, List[float]] = defaultdict(list)
    for row in potential:
        if int(row["label_end_time"]) < last_ts:
            trained[key_for(row, row)].append(float(row["net_R"]))
    model_groups = {}
    for key, vals in trained.items():
        n = len(vals)
        win_rate = sum(x > 0 for x in vals) / n
        mean_net = sum(vals) / n
        import math
        se = math.sqrt(max(win_rate * (1 - win_rate), 0.0) / n)
        net_variance = sum((value - mean_net) ** 2 for value in vals) / (n - 1) if n > 1 else 1e18
        net_se = math.sqrt(net_variance / n)
        model_groups[key] = {"samples": n, "win_rate": win_rate, "mean_net_r": mean_net,
                             "standard_error": se, "mean_net_r_standard_error": net_se,
                             "net_r_samples": n}

    report = {
        "status": "RESEARCH_ONLY_NOT_TRADING_READY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": "XAUUSD", "data_source": "Alpari MT5 Demo broker-specific OHLC history",
        "configuration": {"scan_steps": STEPS, "m1_max_bars": args.m1_max_bars,
                          "pending_entry": "Depth-grid limit retest from near edge to far edge, with revisit ordinal 1..N counted after M1 confirmation; order expires after 8 child-timeframe bars",
                          "depth_fractions_from_near_edge": depth_fractions,
                          "reaction_numbers_after_m1_trigger": reaction_numbers,
                          "reaction_numbering": "Each contiguous return into the selected child Base zone after the M1 trigger counts as one visit; a visit must touch the specified limit price to fill",
                          "m1_timing": "first direction-aligned M1 Base departure after the M15/M5 setup, with close beyond the child Base in the setup direction",
                          "stop": "outside origin Base by 0.15 ATR",
                          "target": "previously known next Base edge; 3R structural fallback when no valid destination edge exists",
                          "wave_exit": "breakeven at +1R, 2.5 ATR trail after +1.5R, two profitable closes inside origin Base",
                          "cost_model": "round-trip 0.05 ATR sensitivity proxy; not broker costs",
                          "same_fill_candle": "excluded from post-fill path to avoid OHLC ordering assumptions",
                          "portfolio_constraints": "not modeled; overlapping event trades are independent",
                          "limitations": ["sampled base detector", "bar data cannot resolve intrabar order",
                                          "no real spread/commission/slippage model", "research artifact not activated"]},
        "potential_filled_trades": summarize(potential),
        "selection_diagnostics": dict(diagnostics),
        "target_source_counts": {source: sum(row.get("target_source") == source for row in potential)
                                 for source in sorted({str(row.get("target_source")) for row in potential})},
        "walk_forward": {"accepted_trades": summarize(accepted),
                         "decision_counts": dict(decision_counts),
                         "note": "Each decision only uses outcomes with exit timestamps before its signal; event trades can overlap."},
        "model_groups": len(model_groups),
        "model_groups_passing_gates": sum(1 for v in model_groups.values()
            if v["samples"] >= args.min_samples and v["win_rate"] >= args.min_win_rate
            and v["mean_net_r"] >= args.min_mean_net_r
            and v["mean_net_r"] - 2.5 * v["mean_net_r_standard_error"] >= args.min_mean_net_r),
        "timeframes": {tf: {"events": len(events_by_tf[tf]), "bars": len(bars_by_tf[tf])} for tf in FILES},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    model = {"version": 1, "min_samples": args.min_samples, "min_win_rate": args.min_win_rate,
             "min_mean_net_r": args.min_mean_net_r, "as_of": last_ts, "groups": model_groups,
             "status": "RESEARCH_ONLY_NOT_ACTIVATED"}
    model_path = Path(args.model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model, indent=2, allow_nan=False), encoding="utf-8")
    print("REPORT", out, flush=True)
    print("MODEL", model_path, "groups", len(model_groups), "as_of", last_ts, flush=True)
    print("SUMMARY", json.dumps({"potential": report["potential_filled_trades"],
          "walk_forward": report["walk_forward"], "model_groups": len(model_groups),
          "passing_groups": report["model_groups_passing_gates"]}), flush=True)


if __name__ == "__main__":
    main()
