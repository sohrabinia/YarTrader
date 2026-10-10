"""Research repeated reactions to detected Base zones; no trading or broker interaction."""
from __future__ import annotations
import argparse, csv, json, math, sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Research.Brain.multitimeframe_base_transition_engine import detect_base_departures, _bar_end_time

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
TFS = ("H4", "H1", "M15", "M5", "M1")
STEPS = {"H4": 2, "H1": 2, "M15": 5, "M5": 10, "M1": 10}
SECONDS = {"H4": 14400, "H1": 3600, "M15": 900, "M5": 300, "M1": 60}

def load_bars(tf: str, max_bars: int) -> List[Dict[str, Any]]:
    path = DATA / (tf + ".csv")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        tc = "time" if "time" in fields else "timestamp"
        rows = deque(maxlen=max_bars if max_bars > 0 else None)
        last = None
        for r in reader:
            try:
                t = int(float(r[tc]))
                b = {"time": t, "open": float(r["open"]), "high": float(r["high"]),
                     "low": float(r["low"]), "close": float(r["close"])}
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
            if not all(math.isfinite(b[k]) for k in ("open", "high", "low", "close")):
                continue
            if last is not None and t < last:
                raise ValueError(f"{path} is not chronological")
            if t == last:
                continue
            rows.append(b); last = t
    return list(rows)

def analyze_base(e: Mapping[str, Any], bars: Sequence[Mapping[str, Any]], tf: str,
                 horizon: int, reaction_window: int) -> tuple[dict, list[dict]]:
    start = int(e["confirmation_index"]) + 1
    end = min(len(bars), start + horizon)
    lo, hi, atr = float(e["base_low"]), float(e["base_high"]), float(e["base_atr"])
    direction = int(e["exit_direction"])
    if atr <= 0 or start >= end:
        return {"event_id": e["event_id"], "timeframe": tf, "base_type": e["base_type"],
                "base_reactions": 0, "invalidated": False}, []
    buffer = 0.15 * atr
    reactions = []
    in_touch = False
    touch_start = -1
    touch_no = 0
    invalidated = False
    j = start
    while j < end:
        b = bars[j]
        close = float(b["close"])
        if (direction > 0 and close < lo-buffer) or (direction < 0 and close > hi+buffer):
            invalidated = True
            break
        overlaps = float(b["low"]) <= hi and float(b["high"]) >= lo
        if overlaps and not in_touch:
            touch_start = j
            in_touch = True
            touch_no += 1
        if in_touch and (not overlaps or j == end-1):
            # End of one touch episode. Measure favorable excursion in a fixed forward window.
            episode_end = j if overlaps else j-1
            wend = min(end, touch_start + reaction_window)
            peak_idx = touch_start
            if direction > 0:
                peak = max(float(bars[k]["high"]) for k in range(touch_start, wend))
                peak_idx = max(range(touch_start, wend), key=lambda k: float(bars[k]["high"]))
                move = max(0.0, peak - hi)
            else:
                peak = min(float(bars[k]["low"]) for k in range(touch_start, wend))
                peak_idx = min(range(touch_start, wend), key=lambda k: float(bars[k]["low"]))
                move = max(0.0, lo - peak)
            peak_atr = move / atr
            ts = int(bars[touch_start]["time"])
            dt = datetime.fromtimestamp(ts, timezone.utc)
            reactions.append({
                "event_id": e["event_id"], "timeframe": tf, "base_type": e["base_type"],
                "direction": "UP" if direction > 0 else "DOWN", "reaction_number": touch_no,
                "touch_time": ts, "touch_utc_hour": dt.hour, "touch_weekday_utc": dt.strftime("%a"),
                "bars_since_departure": touch_start - int(e["confirmation_index"]),
                "elapsed_hours_since_departure": round((ts-int(e["confirmation_time"]))/3600, 3),
                "touch_episode_bars": max(1, episode_end-touch_start+1),
                "reaction_window_bars": min(reaction_window, end-touch_start),
                "reaction_peak_time": int(bars[peak_idx]["time"]),
                "bars_to_peak": peak_idx-touch_start,
                "favorable_reaction_atr": round(peak_atr, 4),
                "reaction_ge_0_5_atr": peak_atr >= 0.5,
                "reaction_ge_1_atr": peak_atr >= 1.0,
                "base_invalidated_later_in_scan": False,
            })
            in_touch = False
        j += 1
    # Annotate invalidation status at the base-level; this is an outcome, not a live feature.
    for r in reactions:
        r["base_invalidated_later_in_scan"] = invalidated
    base = {
        "event_id": e["event_id"], "timeframe": tf, "base_type": e["base_type"],
        "direction": "UP" if direction > 0 else "DOWN",
        "confirmation_time": int(e["confirmation_time"]), "base_start_time": int(e["base_start_time"]),
        "base_low": lo, "base_high": hi, "base_width_atr": float(e["base_width_atr"]),
        "scan_bars": max(0, j-start), "base_reactions": len(reactions),
        "invalidated": invalidated, "first_reaction_atr": reactions[0]["favorable_reaction_atr"] if reactions else None,
        "best_reaction_atr": max((r["favorable_reaction_atr"] for r in reactions), default=None),
        "best_reaction_number": max(reactions, key=lambda r:r["favorable_reaction_atr"])["reaction_number"] if reactions else None,
        "first_touch_time": reactions[0]["touch_time"] if reactions else None,
    }
    return base, reactions

def summarize(rows: Sequence[Mapping[str, Any]], metric: str = "favorable_reaction_atr") -> dict:
    if not rows: return {"n": 0}
    vals = [float(r[metric]) for r in rows if r.get(metric) is not None]
    if not vals: return {"n": len(rows), "valid_metric_n": 0}
    return {
        "n": len(rows), "valid_metric_n": len(vals),
        "mean": round(sum(vals)/len(vals), 4),
        "median": round(sorted(vals)[len(vals)//2], 4),
        "ge_0_5_atr_pct": round(100*sum(v >= 0.5 for v in vals)/len(vals), 2),
        "ge_1_atr_pct": round(100*sum(v >= 1.0 for v in vals)/len(vals), 2),
    }

def grouped(rows: Sequence[Mapping[str, Any]], keyfn) -> dict:
    groups = defaultdict(list)
    for r in rows: groups[keyfn(r)].append(r)
    return {str(k): summarize(v) for k,v in sorted(groups.items(), key=lambda kv: str(kv[0]))}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1-max-bars", type=int, default=1200000)
    ap.add_argument("--horizon-bars", type=int, default=500, help="Maximum bars after departure to observe repeated reactions")
    ap.add_argument("--reaction-window-bars", type=int, default=24, help="Bars after each touch used to measure favorable reaction")
    ap.add_argument("--out", default=str(DATA / "base_repeated_reaction_study.json"))
    ap.add_argument("--events-out", default=str(DATA / "base_repeated_reaction_events.csv"))
    ap.add_argument("--reactions-out", default=str(DATA / "base_repeated_reaction_detail.csv"))
    args = ap.parse_args()
    bases, reactions, tf_summary = [], [], {}
    for tf in TFS:
        bars = load_bars(tf, args.m1_max_bars if tf == "M1" else 0)
        events = detect_base_departures(bars, tf, scan_step=STEPS[tf]) if len(bars) >= 50 else []
        tf_bases, tf_reactions = [], []
        for e in events:
            base, rs = analyze_base(e, bars, tf, args.horizon_bars, args.reaction_window_bars)
            tf_bases.append(base); tf_reactions.extend(rs)
        bases.extend(tf_bases); reactions.extend(tf_reactions)
        tf_summary[tf] = {
            "bars": len(bars), "detected_bases": len(events),
            "bases_with_at_least_one_reaction": sum(x["base_reactions"] > 0 for x in tf_bases),
            "mean_reactions_per_detected_base": round(sum(x["base_reactions"] for x in tf_bases)/len(tf_bases), 3) if tf_bases else None,
            "bases_invalidated_within_scan": sum(x["invalidated"] for x in tf_bases),
            "reaction_count": len(tf_reactions),
            "reaction_strength": summarize(tf_reactions),
            "by_base_type": grouped(tf_reactions, lambda x:x["base_type"]),
            "by_reaction_number": grouped(tf_reactions, lambda x:x["reaction_number"]),
            "by_utc_hour": grouped(tf_reactions, lambda x:x["touch_utc_hour"]),
            "by_weekday_utc": grouped(tf_reactions, lambda x:x["touch_weekday_utc"]),
            "by_elapsed_age_hours": grouped(tf_reactions, lambda x:
                "0-6h" if x["elapsed_hours_since_departure"] < 6 else
                "6-24h" if x["elapsed_hours_since_departure"] < 24 else
                "1-3d" if x["elapsed_hours_since_departure"] < 72 else "3d+"),
        }
        print("REACTION_SCAN", tf, "bars", len(bars), "bases", len(events),
              "reaction_episodes", len(tf_reactions), flush=True)
    report = {
        "status": "RESEARCH_ONLY_NOT_TRADING_READY",
        "created_utc": datetime.now(timezone.utc).isoformat(), "symbol": "XAUUSD",
        "data_source": "Alpari MT5 Demo historical OHLC; not live",
        "method": {
            "definition": "Base is a detected Base-departure event; reaction is a later contiguous episode where an OHLC bar range intersects the Base zone after departure.",
            "counting": "Consecutive intersecting bars count as one touch episode; a later re-entry after at least one non-intersecting bar counts as another reaction.",
            "strength": "Maximum favorable excursion beyond the departure-side edge within the configured forward window, normalized by the Base ATR.",
            "invalidation": "A close beyond the far edge of the zone by 0.15 Base ATR invalidates the Base for this scan.",
            "observation_horizon_bars": args.horizon_bars, "reaction_window_bars": args.reaction_window_bars,
            "important_caveats": ["Detector is sampled (scan steps are greater than one on some timeframes).",
                "Each detected event is analyzed independently; overlapping bases and overlapping reaction windows can duplicate market moves.",
                "UTC hour and weekday are reported; these are not DST-adjusted London/New York session labels.",
                "OHLC cannot show exact intrabar ordering; reaction strength is an offline outcome and not known at touch time.",
                "Results describe detected Base events, not every visually possible zone.", "No broker orders are placed."]
        },
        "timeframes": tf_summary,
        "all_timeframes": {
            "base_count": len(bases), "reaction_episode_count": len(reactions),
            "reactions_per_base_distribution": grouped(bases, lambda x:
                "0" if x["base_reactions"] == 0 else
                "1" if x["base_reactions"] == 1 else
                "2" if x["base_reactions"] == 2 else
                "3" if x["base_reactions"] == 3 else "4+"),
            "by_reaction_number": grouped(reactions, lambda x:x["reaction_number"]),
            "by_base_type": grouped(reactions, lambda x:x["base_type"]),
            "by_utc_hour": grouped(reactions, lambda x:x["touch_utc_hour"]),
            "by_weekday_utc": grouped(reactions, lambda x:x["touch_weekday_utc"]),
        }
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    for path, rows in ((Path(args.events_out), bases), (Path(args.reactions_out), reactions)):
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted({k for row in rows for k in row})
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
    print("REPORT", out, flush=True)
    print("EVENTS_CSV", args.events_out, "REACTIONS_CSV", args.reactions_out, flush=True)
    print("SUMMARY", json.dumps({tf: {"detected_bases": s["detected_bases"],
          "mean_reactions_per_detected_base": s["mean_reactions_per_detected_base"],
          "reaction_count": s["reaction_count"], "reaction_strength": s["reaction_strength"],
          "by_reaction_number": s["by_reaction_number"]} for tf,s in tf_summary.items()}), flush=True)

if __name__ == "__main__":
    main()
