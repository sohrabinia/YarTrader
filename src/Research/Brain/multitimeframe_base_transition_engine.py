"""Causal multitimeframe base/transition research primitives.

Detection features are known at departure confirmation; future outcomes are
emitted only by label_exit_to_next_base(). Timestamps are Unix seconds.
Research-only: no order execution.
"""
from __future__ import annotations
from bisect import bisect_left, bisect_right, insort
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence
import math

TIMEFRAME_SECONDS = {"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,
                     "H4":14400,"D1":86400,"W1":604800,"MN1":2592000}
TIMEFRAME_ORDER = ["MN1","W1","D1","H4","H1","M30","M15","M5","M1"]



def _bar_end_time(bars: Sequence[Mapping[str, Any]], index: int, timeframe: str) -> int:
    """Return a conservative candle-close timestamp; monthly bars use calendar boundaries."""
    start = int(bars[index]["time"])
    if timeframe == "MN1":
        if index+1 < len(bars):
            return int(bars[index+1]["time"])
        dt = datetime.fromtimestamp(start, tz=timezone.utc)
        if dt.month == 12:
            return int(datetime(dt.year+1, 1, 1, tzinfo=timezone.utc).timestamp())
        return int(datetime(dt.year, dt.month+1, 1, tzinfo=timezone.utc).timestamp())
    nominal = start + TIMEFRAME_SECONDS.get(timeframe, 60)
    if index+1 < len(bars):
        next_start = int(bars[index+1]["time"])
        # Use observed next open to handle broker DST shifts, but do not bridge weekend/session gaps.
        if abs((next_start-start)-TIMEFRAME_SECONDS.get(timeframe, 60)) <= 3600:
            return next_start
    return nominal


def detect_base_departures(bars: Sequence[Mapping[str, Any]], timeframe: str,
                           scan_step: int = 1, min_incoming_base_width: float = 1.5,
                           min_departure_base_width: float = 1.0,
                           max_base_width_to_incoming_leg: float = 0.8,
                           max_mean_body_to_base_width: float = 0.55,
                           horizon: int = 24) -> List[Dict[str, Any]]:
    """Detect RBR/DBD/DBR/RBD using Base geometry and raw price only.

    No technical indicator is calculated or consulted. Consolidation width is the
    unit of measurement for the incoming leg, departure, and invalidation buffer.
    """
    if scan_step < 1:
        raise ValueError("scan_step must be >= 1")
    n = len(bars)
    if n < 50:
        return []
    events, last_conf = [], -10**9
    for conf in range(30, n-horizon-1, scan_step):
        best = None
        for delay in (1, 2, 3):
            bend = conf-delay
            for length in (2, 3, 4, 5, 6):
                bs = bend-length+1
                if bs < 10:
                    continue
                base = bars[bs:bend+1]
                hi = max(float(x["high"]) for x in base)
                lo = min(float(x["low"]) for x in base)
                width = hi-lo
                if not math.isfinite(width) or width <= 0:
                    continue
                mean_body = sum(abs(float(x["close"])-float(x["open"])) for x in base)/length
                if mean_body > max_mean_body_to_base_width*width:
                    continue
                # The incoming leg is measured directly in price, relative to the
                # candidate Base width; no rolling range/volatility indicator.
                incoming = float(bars[bs-1]["close"])-float(bars[max(0,bs-5)]["close"])
                if abs(incoming) < min_incoming_base_width*width:
                    continue
                if width > max_base_width_to_incoming_leg*abs(incoming):
                    continue
                mid = (hi+lo)/2
                close = float(bars[conf]["close"])
                dist = close-mid
                if abs(dist) < min_departure_base_width*width:
                    continue
                buffer = 0.15*width
                if close > hi+buffer:
                    outdir = 1
                    if any(float(bars[j]["close"]) > hi+buffer for j in range(bend, conf)):
                        continue
                elif close < lo-buffer:
                    outdir = -1
                    if any(float(bars[j]["close"]) < lo-buffer for j in range(bend, conf)):
                        continue
                else:
                    continue
                score = abs(dist)/width + 0.01*abs(incoming)/width-length*0.0001
                if best is None or score > best[0]:
                    best = (score, bs, bend, hi, lo, width, 1 if incoming > 0 else -1,
                            outdir, length, delay, incoming, dist)
        if best is None or conf-last_conf < max(3, horizon//2):
            continue
        _, bs, bend, hi, lo, width, indir, outdir, length, delay, incoming, dist = best
        typ = ("R" if indir > 0 else "D")+"B"+("R" if outdir > 0 else "D")
        confirmation_time = _bar_end_time(bars, conf, timeframe)
        events.append({
            "event_id": f"{timeframe}:{confirmation_time}:{typ}",
            "timeframe": timeframe, "base_start_index": bs, "base_end_index": bend,
            "confirmation_index": conf, "base_start_time": int(bars[bs]["time"]),
            "base_end_time": _bar_end_time(bars, bend, timeframe), "confirmation_time": confirmation_time,
            "base_high": hi, "base_low": lo, "base_mid": (hi+lo)/2, "base_width": width,
            "base_length": length,
            "incoming_direction": indir, "exit_direction": outdir, "base_type": typ,
            "incoming_leg_base_widths": incoming/width,
            "departure_size_base_widths": abs(dist)/width,
            "departure_delay_bars": delay, "detector_version": "base_geometry_price_only_v2",
            "feature_cutoff_time": confirmation_time,
        })
        last_conf = conf
    return events



def attach_market_context(events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                          bars_by_tf: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    """Attach closed-candle raw-price context only; never calculate indicators."""
    cache = {}
    for tf, bars in bars_by_tf.items():
        if not bars:
            continue
        ends = [_bar_end_time(bars, i, tf) for i in range(len(bars))]
        closes = [float(b["close"]) for b in bars]
        cache[tf] = (ends, closes)
    for events in events_by_tf.values():
        for event in events:
            ts = int(event["confirmation_time"])
            context = {}
            for tf in TIMEFRAME_ORDER:
                if tf not in cache:
                    context[tf] = {"status":"UNAVAILABLE"}
                    continue
                ends, closes = cache[tf]
                idx = bisect_right(ends, ts)-1
                if idx < 10:
                    context[tf] = {"status":"INSUFFICIENT_CLOSED_BARS"}
                    continue
                prior_close = closes[idx-10]
                current_close = closes[idx]
                delta = current_close-prior_close
                trend = "BULLISH" if delta > 0 else ("BEARISH" if delta < 0 else "NEUTRAL")
                context[tf] = {
                    "status":"AVAILABLE", "closed_bar_time":ends[idx],
                    "price_change_over_10_bars":round(delta, 8),
                    "price_direction_over_10_bars":trend,
                }
            event["market_context"] = context


def build_hierarchy(events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    """Summarize contained lower-TF bases confirmed no later than the parent exit."""
    rank = {tf:i for i,tf in enumerate(TIMEFRAME_ORDER)}
    by_tf = {tf:sorted((dict(e) for e in events_by_tf.get(tf, [])),
                       key=lambda x:x["base_start_time"]) for tf in TIMEFRAME_ORDER}
    start_times = {tf:[e["base_start_time"] for e in vals] for tf,vals in by_tf.items()}
    summaries = []
    for p_tf in TIMEFRAME_ORDER:
        for parent in by_tf[p_tf]:
            children = []
            for c_tf in TIMEFRAME_ORDER[rank[p_tf]+1:]:
                vals = by_tf[c_tf]
                lo_i = bisect_left(start_times[c_tf], parent["base_start_time"])
                hi_i = bisect_right(start_times[c_tf], parent["base_end_time"])
                for child in vals[lo_i:hi_i]:
                    if child["confirmation_time"] > parent["confirmation_time"]:
                        continue
                    if child["base_end_time"] > parent["base_end_time"]:
                        continue
                    if child["base_mid"] < parent["base_low"] or child["base_mid"] > parent["base_high"]:
                        continue
                    children.append(child)
            child_summary = {}
            for tf in ("H4","H1","M30","M15","M5","M1"):
                vals = [c for c in children if c["timeframe"] == tf]
                child_summary[tf] = {
                    "count":len(vals),
                    "types":{typ:sum(c["base_type"] == typ for c in vals) for typ in ("RBR","DBD","DBR","RBD")},
                    "last_confirmed_direction":vals[-1]["exit_direction"] if vals else None,
                }
            summaries.append({
                "event_id":parent["event_id"], "timeframe":p_tf,
                "confirmation_time":parent["confirmation_time"], "base_type":parent["base_type"],
                "child_bases":child_summary,
                # Preserve every child, not just one representative child per parent.
                # A child can legitimately be nested in multiple active higher-TF bases.
                "child_events":[{
                    "event_id":c["event_id"],"timeframe":c["timeframe"],
                    "base_type":c["base_type"],"base_start_time":c["base_start_time"],
                    "base_end_time":c["base_end_time"],"confirmation_time":c["confirmation_time"],
                    "exit_direction":c["exit_direction"],
                    "parent_child_relation":"ALIGNED" if c["exit_direction"] == parent["exit_direction"] else "OPPOSED",
                    "child_zone_within_parent":True,
                } for c in sorted(children,key=lambda x:(x["base_start_time"],TIMEFRAME_ORDER.index(x["timeframe"])))],
                "child_alignment_count":sum(c["exit_direction"] == parent["exit_direction"] for c in children),
                "child_opposition_count":sum(c["exit_direction"] != parent["exit_direction"] for c in children),
                "known_at_confirmation_only":True,
            })
    return summaries


def label_base_reentry_reactions(events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                                 bars_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                                 horizon_bars: int = 96,
                                 departure_buffer_base_widths: float = 0.1) -> List[Dict[str, Any]]:
    """Label repeated post-confirmation interactions with each Base, not only departures.

    Emits one row per distinct re-entry episode per Base. It records entry side,
    penetration depth, time spent/accepted inside the zone, and the first subsequent
    rejection/escape direction. These are outcome labels for offline learning, never
    features available before the interaction and never direct trading instructions.
    """
    if horizon_bars < 1:
        raise ValueError("horizon_bars must be >= 1")
    outputs = []
    for tf, events in events_by_tf.items():
        bars = bars_by_tf.get(tf, [])
        if not bars:
            continue
        for event in events:
            if "confirmation_index" not in event:
                continue
            conf = int(event["confirmation_index"])
            lo, hi = float(event["base_low"]), float(event["base_high"])
            width = hi-lo
            base_width = float(event.get("base_width", 0.0))
            if width <= 0 or base_width <= 0 or conf+1 >= len(bars):
                continue
            end = min(len(bars), conf+1+horizon_bars)
            active = False
            episode = None
            episode_num = 0
            episodes = []
            for i in range(conf+1, end):
                b = bars[i]
                touched = float(b["low"]) <= hi and float(b["high"]) >= lo
                if touched and not active:
                    episode_num += 1
                    previous_close = float(bars[i-1]["close"])
                    open_side = "FROM_ABOVE" if previous_close > hi else ("FROM_BELOW" if previous_close < lo else "INTERIOR_OR_AMBIGUOUS_OHLC")
                    episode = {"episode_number":episode_num,"start_index":i,
                               "start_time":int(b["time"]),"entry_side":open_side,
                               "touch_bars":0,"closes_inside":0,"max_penetration_fraction":0.0,
                               "lowest_price":float(b["low"]),"highest_price":float(b["high"]),
                               "close_inside_streak":0,"max_close_inside_streak":0}
                if touched and episode is not None:
                    episode["touch_bars"] += 1
                    episode["lowest_price"] = min(episode["lowest_price"],float(b["low"]))
                    episode["highest_price"] = max(episode["highest_price"],float(b["high"]))
                    penetration = min(1.0,max(0.0,(hi-float(b["low"])) / width,
                                               (float(b["high"])-lo) / width))
                    episode["max_penetration_fraction"] = max(episode["max_penetration_fraction"],penetration)
                    inside = lo <= float(b["close"]) <= hi
                    episode["closes_inside"] += int(inside)
                    episode["close_inside_streak"] = episode["close_inside_streak"]+1 if inside else 0
                    episode["max_close_inside_streak"] = max(episode["max_close_inside_streak"],episode["close_inside_streak"])
                if not touched and active and episode is not None:
                    episode["end_index"] = i-1
                    episode["end_time"] = int(bars[i-1]["time"])
                    episodes.append(episode)
                    episode = None
                active = touched
            if active and episode is not None:
                episode["end_index"] = end-1
                episode["end_time"] = int(bars[end-1]["time"])
                episodes.append(episode)
            for ep in episodes:
                escape = "UNRESOLVED"
                escape_bars = None
                follow_end = min(end, int(ep["end_index"])+1+max(3, min(12, horizon_bars//4)))
                for j in range(int(ep["end_index"])+1, follow_end):
                    close = float(bars[j]["close"])
                    if close > hi+departure_buffer_base_widths*base_width:
                        escape, escape_bars = "UP_REJECTION_OR_ESCAPE", j-int(ep["end_index"])
                        break
                    if close < lo-departure_buffer_base_widths*base_width:
                        escape, escape_bars = "DOWN_REJECTION_OR_ESCAPE", j-int(ep["end_index"])
                        break
                ep["reaction_outcome"] = escape
                ep["reaction_outcome_bars"] = escape_bars
                ep["accepted_inside_zone"] = ep["max_close_inside_streak"] >= 2
                ep["reaction_aligned_with_base_departure"] = (
                    (escape == "UP_REJECTION_OR_ESCAPE" and int(event.get("exit_direction",0)) > 0) or
                    (escape == "DOWN_REJECTION_OR_ESCAPE" and int(event.get("exit_direction",0)) < 0)
                ) if escape != "UNRESOLVED" else None
                ep["label_end_time"] = int(bars[min(end-1, int(ep["end_index"])+12)]["time"])
                outputs.append({"event_id":event["event_id"],"timeframe":tf,
                                "base_type":event.get("base_type"),"base_role":"MOTHER_OR_CHILD_CONTEXTUAL",
                                "base_zone":{"low":lo,"high":hi},"feature_cutoff_time":event["confirmation_time"],
                                "interaction":ep,"label_mode":"OFFLINE_REENTRY_OUTCOME_ONLY"})
    return outputs


def label_exit_to_next_base(events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                            bars_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                            horizon_bars: int = 24) -> List[Dict[str, Any]]:
    """Offline labels for continuation, reversal, origin retest, next known base and pause."""
    all_events = sorted((dict(e) for values in events_by_tf.values() for e in values),
                        key=lambda x:x["confirmation_time"])
    # A price-sorted index of zones confirmed strictly before the current timestamp.
    known_zones = []
    outputs = []
    parent_index = {}
    for parent_tf in TIMEFRAME_ORDER:
        rows = sorted((dict(x) for x in events_by_tf.get(parent_tf, [])
                       if x.get("base_start_time") is not None),
                      key=lambda x: int(x["base_start_time"]))
        parent_index[parent_tf] = (rows, [int(x["base_start_time"]) for x in rows])
    cursor = 0
    while cursor < len(all_events):
        ts = all_events[cursor]["confirmation_time"]
        end_group = cursor
        while end_group < len(all_events) and all_events[end_group]["confirmation_time"] == ts:
            end_group += 1
        group = all_events[cursor:end_group]
        for e in group:
            tf = e["timeframe"]
            bars = bars_by_tf.get(tf, [])
            if not bars or "confirmation_index" not in e:
                continue
            i = int(e["confirmation_index"])
            if i+1 >= len(bars) or i+horizon_bars >= len(bars):
                continue
            direction = int(e["exit_direction"])
            origin_hi, origin_lo = float(e["base_high"]), float(e["base_low"])
            close0, base_width = float(bars[i]["close"]), float(e["base_width"])
            if not math.isfinite(base_width) or base_width <= 0:
                continue
            target = None
            if direction > 0:
                pos = bisect_right(known_zones, (close0, chr(0x10ffff), {}))
                for zone_row in known_zones[pos:]:
                    if float(zone_row[2]["base_low"]) > close0:
                        target = zone_row[2]
                        break
            else:
                pos = bisect_left(known_zones, (close0, "", {}))-1
                for zone_row in reversed(known_zones[:pos+1]):
                    if float(zone_row[2]["base_high"]) < close0:
                        target = zone_row[2]
                        break
            future = bars[i+1:min(len(bars), i+1+horizon_bars)]
            retest_idx = target_idx = cont_idx = rev_idx = failed_idx = None
            corridor_pause = False
            pause_start = pause_departure = pause_direction = None
            pause_range_base_widths = None
            pause_high = pause_low = None
            for k, b in enumerate(future, start=1):
                hi, lo = float(b["high"]), float(b["low"])
                cl = float(b["close"])
                if retest_idx is None and lo <= origin_hi and hi >= origin_lo:
                    retest_idx = k
                if failed_idx is None and origin_lo <= cl <= origin_hi:
                    failed_idx = k
                if target is not None and target_idx is None and lo <= float(target["base_high"]) and hi >= float(target["base_low"]):
                    target_idx = k
                if cont_idx is None and ((hi-close0 >= base_width) if direction > 0 else (close0-lo >= base_width)):
                    cont_idx = k
                if rev_idx is None and ((close0-lo >= base_width) if direction > 0 else (hi-close0 >= base_width)):
                    rev_idx = k
                if pause_start is None and 3 <= k <= horizon_bars-2:
                    recent = future[max(0,k-3):k+1]
                    rng = max(float(x["high"]) for x in recent)-min(float(x["low"]) for x in recent)
                    mean_body = sum(abs(float(x["close"])-float(x["open"])) for x in recent)/len(recent)
                    if rng <= 0.75*base_width and mean_body <= 0.35*base_width:
                        corridor_pause = True
                        pause_start = k
                        pause_range_base_widths = rng/base_width
                        pause_high = max(float(x["high"]) for x in recent)
                        pause_low = min(float(x["low"]) for x in recent)
            if pause_start is not None:
                for j in range(pause_start+1, len(future)+1):
                    close_after_pause = float(future[j-1]["close"])
                    if close_after_pause > pause_high+0.15*base_width:
                        pause_departure, pause_direction = j, 1
                        break
                    if close_after_pause < pause_low-0.15*base_width:
                        pause_departure, pause_direction = j, -1
                        break
            candidates = [(cont_idx,"continuation_barrier"),(rev_idx,"reversal_barrier"),
                          (retest_idx,"origin_retest"),(failed_idx,"failed_exit_closeback"),
                          (target_idx,"next_base_touch")]
            candidates = [(idx,name) for idx,name in candidates if idx is not None]
            if not candidates:
                first = "horizon_expired"
            else:
                earliest = min(idx for idx,_ in candidates)
                first_names = [name for idx,name in candidates if idx == earliest]
                if set(first_names).issubset({"origin_retest","failed_exit_closeback"}) and "failed_exit_closeback" in first_names:
                    first = "failed_exit_closeback"
                else:
                    first = first_names[0] if len(first_names) == 1 else "ambiguous_same_bar"
            # Conservatively mark labels as available only after the full forward horizon closes.
            label_end_index = min(len(bars)-1, i+horizon_bars)
            nested_parents = []
            transition_parents = []
            child_rank = TIMEFRAME_ORDER.index(tf) if tf in TIMEFRAME_ORDER else len(TIMEFRAME_ORDER)
            child_start = int(e.get("base_start_time", 0))
            child_end = int(e.get("base_end_time", 0))
            child_confirm = int(e.get("confirmation_time", 0))
            child_low, child_high = float(e.get("base_low", -math.inf)), float(e.get("base_high", math.inf))
            child_mid, child_dir = float(e.get("base_mid", 0.0)), int(e.get("exit_direction", 0))
            # Keep two distinct causal relationships: strict temporal nesting, and a
            # later child Base in the departure corridor of an already-confirmed parent.
            for parent_tf in TIMEFRAME_ORDER[:child_rank]:
                parent_events, parent_starts = parent_index[parent_tf]
                seconds = TIMEFRAME_SECONDS.get(parent_tf, 60)
                lo_i = bisect_left(parent_starts, child_start - 24*seconds)
                hi_i = bisect_right(parent_starts, child_start)
                for candidate in parent_events[lo_i:hi_i]:
                    parent_confirm = int(candidate.get("confirmation_time", 0))
                    if parent_confirm > child_confirm or child_confirm - parent_confirm > 24*seconds:
                        continue
                    p_low, p_high = float(candidate.get("base_low", -math.inf)), float(candidate.get("base_high", math.inf))
                    p_mid = float(candidate.get("base_mid", (p_low+p_high)/2))
                    contains_time = int(candidate.get("base_end_time", 0)) >= child_end
                    contains_price = p_low <= child_low and p_high >= child_high
                    if contains_time and contains_price:
                        nested_parents.append(candidate)
                        continue
                    overlaps_zone = child_low <= p_high and child_high >= p_low
                    directional_corridor = (child_mid >= p_mid) if child_dir > 0 else ((child_mid <= p_mid) if child_dir < 0 else False)
                    if overlaps_zone or directional_corridor:
                        transition_parents.append(candidate)
            if nested_parents:
                parent = max(nested_parents, key=lambda x: (TIMEFRAME_ORDER.index(x["timeframe"]), int(x["confirmation_time"])))
                parent_relation = "NESTED"
            elif transition_parents:
                parent = max(transition_parents, key=lambda x: (TIMEFRAME_ORDER.index(x["timeframe"]), int(x["confirmation_time"])))
                parent_relation = "TRANSITION_CONTEXT"
            else:
                parent, parent_relation = None, "NONE"
            outputs.append({
                "event_id":e["event_id"],"timeframe":tf,"base_type":e["base_type"],
                "exit_direction":direction,"label_horizon_bars":horizon_bars,"first_transition":first,
                "label_end_time":_bar_end_time(bars, label_end_index, tf),
                "parent_timeframe":parent.get("timeframe") if parent else "NONE",
                "parent_relation":parent_relation,
                "parent_aligned":bool(parent and int(parent.get("exit_direction", 0)) == direction),
                "continuation_barrier_bars":cont_idx,"reversal_barrier_bars":rev_idx,
                "origin_retest_bars":retest_idx,"failed_exit_closeback_bars":failed_idx,
                "next_base_id":target["event_id"] if target else None,
                "next_base_distance_base_widths":abs(float(target["base_mid"])-close0)/base_width if target else None,
                "next_base_touch_bars":target_idx,"corridor_pause_candidate":corridor_pause,
                "corridor_pause_start_bar":pause_start,"corridor_pause_range_base_widths":round(pause_range_base_widths,4) if pause_range_base_widths is not None else None,
                "corridor_pause_departure_bars":pause_departure,"corridor_pause_departure_direction":pause_direction,
                "corridor_pause_departure_aligned":(pause_direction == direction) if pause_direction is not None else None,
                "label_mode":"OFFLINE_OUTCOME_ONLY","feature_cutoff_time":e["confirmation_time"],
            })
        # Same-time events are not allowed to be each other's prior-known target.
        for e in group:
            insort(known_zones,(float(e["base_mid"]),str(e["event_id"]),e))
        cursor = end_group
    return outputs


def simulate_departure_trades(events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                              bars_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
                              transition_labels: Sequence[Mapping[str, Any]],
                              horizon_bars: int = 24, stop_buffer_base_widths: float = 0.1,
                              target_r: float = 2.0, round_trip_cost_base_widths: float = 0.05) -> Dict[str, Any]:
    """Conservative baseline trade simulation; entry is next-bar open, stop wins same-bar ties.

    Cost is an base_width-based sensitivity proxy, not broker spread or a claim of net profitability.
    """
    event_map = {e["event_id"]:e for vals in events_by_tf.values() for e in vals}
    label_map = {x["event_id"]:x for x in transition_labels}
    trades = []
    for tf, events in events_by_tf.items():
        bars = bars_by_tf.get(tf, [])
        for e in events:
            i = int(e["confirmation_index"])
            if i+1 >= len(bars) or i+horizon_bars >= len(bars):
                continue
            direction = int(e["exit_direction"])
            base_width = float(e["base_width"])
            entry = float(bars[i+1]["open"])
            stop = (float(e["base_low"])-stop_buffer_base_widths*base_width if direction > 0
                    else float(e["base_high"])+stop_buffer_base_widths*base_width)
            risk = direction*(entry-stop)
            if not math.isfinite(risk) or risk <= 0 or not math.isfinite(base_width) or base_width <= 0:
                continue
            label = label_map.get(e["event_id"], {})
            for mode in ("fixed_2R", "next_base", "wave_rider"):
                target = None if mode == "wave_rider" else entry + direction*target_r*risk
                if mode == "wave_rider" and tf not in ("M15","M5","M1"):
                    continue
                if mode == "next_base":
                    zone = event_map.get(label.get("next_base_id"))
                    if not zone:
                        continue
                    edge = float(zone["base_low"] if direction > 0 else zone["base_high"])
                    if (direction > 0 and edge <= entry) or (direction < 0 and edge >= entry):
                        edge = float(zone["base_mid"])
                    if (direction > 0 and edge <= entry) or (direction < 0 and edge >= entry):
                        continue
                    target = edge
                # Fixed-target baselines expire after the configured horizon. The wave rider
                # instead trails the move and has a longer intraday evaluation cap.
                trade_horizon = (240 if tf == "M1" else 96 if tf == "M5" else 48) if mode == "wave_rider" else horizon_bars
                end = min(len(bars)-1, i+trade_horizon)
                exit_price, exit_reason, exit_index = float(bars[end]["close"]), "evaluation_horizon_close", end
                active_stop = stop
                favorable_extreme = entry
                inside_origin_closes = 0
                for j in range(i+1, end+1):
                    hi, lo, cl = float(bars[j]["high"]), float(bars[j]["low"]), float(bars[j]["close"])
                    if mode == "wave_rider":
                        # Test against the stop carried into this candle before updating the extreme,
                        # avoiding use of the same candle's high to tighten a stop before its low.
                        stop_hit = lo <= active_stop if direction > 0 else hi >= active_stop
                        if stop_hit:
                            exit_price, exit_reason, exit_index = active_stop, ("trailing_stop" if active_stop != stop else "initial_stop"), j
                            break
                        if direction > 0:
                            favorable_extreme = max(favorable_extreme, hi)
                            best_move = favorable_extreme-entry
                        else:
                            favorable_extreme = min(favorable_extreme, lo)
                            best_move = entry-favorable_extreme
                        if best_move >= risk:
                            # Once +1R has been reached, never allow the protective stop below breakeven.
                            active_stop = max(active_stop, entry) if direction > 0 else min(active_stop, entry)
                        if best_move >= 1.5*risk:
                            trail = favorable_extreme - direction*2.5*base_width
                            active_stop = max(active_stop, trail) if direction > 0 else min(active_stop, trail)
                        # Exit only after two closes back inside the origin base, and only if still profitable.
                        inside = float(e["base_low"]) <= cl <= float(e["base_high"])
                        inside_origin_closes = inside_origin_closes+1 if inside else 0
                        if inside_origin_closes >= 2 and direction*(cl-entry) > 0:
                            exit_price, exit_reason, exit_index = cl, "profitable_origin_reentry", j
                            break
                        continue
                    stop_hit = lo <= stop if direction > 0 else hi >= stop
                    target_hit = hi >= target if direction > 0 else lo <= target
                    if stop_hit and target_hit:
                        exit_price, exit_reason, exit_index = stop, "ambiguous_stop_first", j
                        break
                    if stop_hit:
                        exit_price, exit_reason, exit_index = stop, "stop", j
                        break
                    if target_hit:
                        exit_price, exit_reason, exit_index = target, "target", j
                        break
                gross_r = direction*(exit_price-entry)/risk
                cost_r = round_trip_cost_base_widths*base_width/risk
                trades.append({
                    "event_id":e["event_id"],"timeframe":tf,"base_type":e["base_type"],
                    "strategy":mode,"confirmation_time":e["confirmation_time"],
                    "entry_price":entry,"stop_price":stop,"target_price":target,
                    "exit_price":exit_price,"exit_reason":exit_reason,"exit_index":exit_index,
                    "risk_price":risk,"gross_R":gross_r,"cost_R_proxy":cost_r,
                    "net_R_proxy":gross_r-cost_r,
                    "market_context":e.get("market_context",{}),
                })
    def summarize(rows):
        if not rows:
            return {"trades":0}
        net = [x["net_R_proxy"] for x in rows]
        gross = [x["gross_R"] for x in rows]
        wins = sum(x > 0 for x in net)
        pos, neg = sum(x for x in net if x > 0), -sum(x for x in net if x < 0)
        eq, peak, max_dd = 0.0, 0.0, 0.0
        for value in net:
            eq += value
            peak = max(peak, eq)
            max_dd = max(max_dd, peak-eq)
        return {
            "trades":len(rows),"net_win_rate_pct":round(100*wins/len(rows),2),
            "mean_gross_R":round(sum(gross)/len(rows),4),
            "mean_net_R_proxy":round(sum(net)/len(rows),4),
            "profit_factor_proxy":round(pos/neg,4) if neg else None,
            "max_drawdown_R_proxy":round(max_dd,3),
            "exit_reasons":{k:sum(x["exit_reason"]==k for x in rows) for k in sorted({x["exit_reason"] for x in rows})},
        }
    summary = {}
    for tf in events_by_tf:
        summary[tf] = {}
        tf_rows = sorted([x for x in trades if x["timeframe"] == tf], key=lambda x:x["confirmation_time"])
        for mode in ("fixed_2R","next_base","wave_rider"):
            rows = [x for x in tf_rows if x["strategy"] == mode]
            summary[tf][mode] = {"overall":summarize(rows),"by_base_type":{},"by_direction":{},
                                     "by_higher_timeframe_context":{},"chronological_split":{}}
            for typ in ("RBR","DBD","DBR","RBD"):
                summary[tf][mode]["by_base_type"][typ] = summarize([x for x in rows if x["base_type"] == typ])
            for direction, name in ((1,"long"),(-1,"short")):
                summary[tf][mode]["by_direction"][name] = summarize([
                    x for x in rows if int(event_map[x["event_id"]]["exit_direction"]) == direction
                ])
            event_times = sorted(e["confirmation_time"] for e in events_by_tf.get(tf, []))
            cutoff = event_times[min(len(event_times)-1, int(len(event_times)*0.7))] if event_times else None
            early = [x for x in rows if cutoff is not None and x["confirmation_time"] < cutoff]
            late = [x for x in rows if cutoff is not None and x["confirmation_time"] >= cutoff]
            summary[tf][mode]["chronological_split"] = {
                "cutoff_time":cutoff, "first_70pct":summarize(early), "last_30pct":summarize(late),
                "note":"rough time holdout; parameters were not tuned on these slices"
            }
            for context_tf in ("D1","H4","H1"):
                summary[tf][mode]["by_higher_timeframe_context"][context_tf] = {"trend_regime":{},"volatility_regime":{}}
                for axis in ("trend_regime","volatility_regime"):
                    groups = {}
                    for trade in rows:
                        ctx = trade.get("market_context",{}).get(context_tf,{})
                        if ctx.get("status") == "AVAILABLE" and ctx.get(axis) is not None:
                            groups.setdefault(ctx[axis],[]).append(trade)
                    for value, subset in groups.items():
                        summary[tf][mode]["by_higher_timeframe_context"][context_tf][axis][value] = summarize(subset)
    return {
        "configuration":{"entry":"next bar open after departure confirmation","stop_buffer_base_widths":stop_buffer_base_widths,
                         "fixed_target_R":target_r,"round_trip_cost_base_widths_proxy":round_trip_cost_base_widths,
                         "same_bar_stop_target":"stop-first conservative","horizon_bars":horizon_bars,
                         "wave_rider":{"timeframes":["M15","M5","M1"],"fixed_profit_target":False,
                                       "breakeven_activation_R":1.0,"trailing_activation_R":1.5,
                                       "trailing_distance_base_widths":2.5,
                                       "exit_on_two_closes_back_inside_origin_base_if_profitable":True,
                                       "evaluation_cap_bars":{"M15":48,"M5":96,"M1":240},
                                       "note":"Research baseline only; cap closes remaining positions for evaluation, not a live time-based exit rule"}},
        "status":"BASELINE_RESEARCH_SIMULATION_NOT_BROKER_COSTED",
        "summary":summary,
    }

