"""Research repeated reactions to confirmed Base zones.

Offline descriptive event study only; no broker access or orders. A reaction is a
new contiguous visit to the zone after departure. Outcomes are measured forward
from the deepest price reached during that visit, with no overlapping-touch
bar credited as post-touch movement.
"""
from __future__ import annotations
import argparse, csv, json, math, sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Research.Brain.multitimeframe_base_transition_engine import detect_base_departures

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
TFS = ("H4", "H1", "M15", "M5", "M1")
STEPS = {"H4": 2, "H1": 2, "M15": 5, "M5": 10, "M1": 10}
HORIZONS = (1, 3, 6, 12, 24)

def load_bars(tf: str, max_bars: int) -> List[Dict[str, Any]]:
    path = DATA / (tf + ".csv")
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        tc = "time" if "time" in fields else "timestamp" if "timestamp" in fields else None
        if not tc or not {"open", "high", "low", "close"}.issubset(fields):
            return []
        rows = deque(maxlen=max_bars if max_bars > 0 else None)
        last = None
        for raw in reader:
            try:
                t = int(float(raw[tc]))
                b = {"time": t, "open": float(raw["open"]), "high": float(raw["high"]),
                     "low": float(raw["low"]), "close": float(raw["close"])}
            except (TypeError, ValueError, KeyError, OverflowError):
                continue
            if not all(math.isfinite(b[k]) for k in ("open", "high", "low", "close")):
                continue
            if last is not None and t < last:
                raise ValueError(f"{path} is not chronological")
            if t == last:
                continue
            rows.append(b); last = t
    return list(rows)

def reaction_rows(event: Mapping[str, Any], bars: Sequence[Mapping[str, Any]],
                  max_horizon: int) -> List[Dict[str, Any]]:
    tf = str(event["timeframe"])
    start = int(event["confirmation_index"]) + 1
    end = min(len(bars)-max_horizon-1, start + max_horizon*20)
    if start >= len(bars) or end <= start:
        return []
    lo, hi, atr = float(event["base_low"]), float(event["base_high"]), float(event["base_atr"])
    width = hi-lo
    direction = int(event["exit_direction"])
    if width <= 0 or atr <= 0 or direction not in (-1, 1):
        return []
    # The base is invalidated by a close through its far edge against the departure.
    visits, active = [], []
    for i in range(start, end+1):
        b = bars[i]
        invalid = float(b["close"]) < lo-0.15*atr if direction > 0 else float(b["close"]) > hi+0.15*atr
        if invalid:
            if active:
                visits.append(active); active = []
            break
        touch = float(b["low"]) <= hi and float(b["high"]) >= lo
        if touch:
            active.append(i)
        elif active:
            visits.append(active); active = []
    if active:
        visits.append(active)
    output = []
    for nth, inds in enumerate(visits, 1):
        last_touch = inds[-1]
        # Deepest point reached inside the zone during this contiguous visit.
        if direction > 0:
            touch_price = max(lo, min(float(bars[i]["low"]) for i in inds))
            depth = (hi-touch_price)/width
        else:
            touch_price = min(hi, max(float(bars[i]["high"]) for i in inds))
            depth = (touch_price-lo)/width
        depth = max(0.0, min(1.0, depth))
        row = {"event_id": event["event_id"], "timeframe": tf, "base_type": event["base_type"],
               "direction": "LONG" if direction > 0 else "SHORT",
               "base_start_time": int(event["base_start_time"]),
               "departure_time": int(event["confirmation_time"]),
               "reaction_number": nth, "touch_start_time": int(bars[inds[0]]["time"]),
               "touch_end_time": int(bars[last_touch]["time"]),
               "touch_hour_utc": datetime.fromtimestamp(int(bars[inds[0]]["time"]), timezone.utc).hour,
               "touch_weekday_utc": datetime.fromtimestamp(int(bars[inds[0]]["time"]), timezone.utc).weekday(),
               "touch_bars": len(inds), "penetration_fraction": round(depth, 4),
               "penetration_quartile": min(3, int(depth*4)),
               "touch_price": touch_price, "base_width_atr": width/atr}
        for h in HORIZONS:
            end_i = last_touch+h
            if end_i >= len(bars):
                continue
            future = bars[last_touch+1:end_i+1]
            if not future:
                continue
            if direction > 0:
                favorable = max(float(x["high"]) for x in future)-touch_price
                adverse = touch_price-min(float(x["low"]) for x in future)
            else:
                favorable = touch_price-min(float(x["low"]) for x in future)
                adverse = max(float(x["high"]) for x in future)-touch_price
            r = favorable/atr
            row[f"favorable_atr_{h}"] = round(r, 4)
            row[f"adverse_atr_{h}"] = round(adverse/atr, 4)
            row[f"hit_0_5atr_{h}"] = r >= 0.5
            row[f"hit_1atr_{h}"] = r >= 1.0
            row[f"time_to_0_5atr_bars_{h}"] = next((j for j,x in enumerate(future,1)
                if (float(x["high"])-touch_price if direction > 0 else touch_price-float(x["low"])) >= 0.5*atr), None)
        output.append(row)
    return output

def stats(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows: return {"reactions": 0}
    out = {"reactions": len(rows), "unique_bases": len({r["event_id"] for r in rows}),
           "mean_penetration_fraction": round(sum(float(r["penetration_fraction"]) for r in rows)/len(rows), 4)}
    for h in HORIZONS:
        key = f"favorable_atr_{h}"
        vals = [float(r[key]) for r in rows if key in r]
        if vals:
            out[f"mean_favorable_atr_{h}"] = round(sum(vals)/len(vals), 4)
            out[f"hit_0_5atr_pct_{h}"] = round(100*sum(bool(r[f"hit_0_5atr_{h}"]) for r in rows if key in r)/len(vals), 2)
            out[f"hit_1atr_pct_{h}"] = round(100*sum(bool(r[f"hit_1atr_{h}"]) for r in rows if key in r)/len(vals), 2)
            av = [float(r[f"adverse_atr_{h}"]) for r in rows if f"adverse_atr_{h}" in r]
            out[f"mean_adverse_atr_{h}"] = round(sum(av)/len(av), 4) if av else None
    return out

def grouped(rows: Sequence[Mapping[str, Any]], field: str) -> Dict[str, Any]:
    buckets = defaultdict(list)
    for row in rows: buckets[str(row.get(field, "UNKNOWN"))].append(row)
    return {k: stats(v) for k,v in sorted(buckets.items(), key=lambda kv: kv[0])}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--m1-max-bars", type=int, default=1200000)
    p.add_argument("--out", default=str(DATA / "base_reaction_profile_1200k.json"))
    p.add_argument("--rows-out", default=str(DATA / "base_reaction_rows_1200k.jsonl"))
    p.add_argument("--max-horizon", type=int, default=24)
    a = p.parse_args()
    all_rows, inventory = [], {}
    for tf in TFS:
        bars = load_bars(tf, a.m1_max_bars if tf == "M1" else 0)
        events = detect_base_departures(bars, tf, scan_step=STEPS[tf]) if len(bars) >= 50 else []
        tf_rows = []
        for ev in events:
            tf_rows.extend(reaction_rows(ev, bars, a.max_horizon))
        all_rows.extend(tf_rows)
        inventory[tf] = {"bars": len(bars), "detected_bases": len(events),
                         "bases_with_reaction": len({x["event_id"] for x in tf_rows}),
                         "reaction_visits": len(tf_rows)}
        print("TF", tf, inventory[tf], flush=True)
        del bars, events, tf_rows
    report = {
        "status": "RESEARCH_ONLY_NOT_TRADING_READY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": "XAUUSD", "source": "Alpari MT5 Demo historical OHLC CSV",
        "definition": {
            "base_detector": "same detector as multitimeframe transition research; sampled scan",
            "reaction": "each contiguous visit to the zone after departure confirmation; separated visits count as repeat reactions",
            "touch_point": "deepest penetration within the zone during the visit, normalized 0=near edge, 1=far edge",
            "direction": "reaction measured in the original departure direction",
            "outcome": "favorable/adverse excursion from deepest touch price over next 1/3/6/12/24 bars; normalized by base ATR",
            "invalidated": "analysis stops at a close 0.15 ATR beyond the far edge against the original departure",
            "time": "touch hour and weekday in UTC; bar-count horizons, not clock-time horizons",
            "limitations": ["sampled detector misses some bases", "visits can overlap across different bases",
                            "OHLC cannot resolve intrabar path", "descriptive outcomes are not net trade PnL",
                            "no spread/commission/slippage", "historical outcomes must not enter live features"]
        },
        "inventory": inventory,
        "overall": stats(all_rows),
        "by_timeframe": grouped(all_rows, "timeframe"),
        "by_base_type": grouped(all_rows, "base_type"),
        "by_reaction_number": grouped(all_rows, "reaction_number"),
        "by_penetration_quartile": grouped(all_rows, "penetration_quartile"),
        "by_utc_hour": grouped(all_rows, "touch_hour_utc"),
        "by_utc_weekday": grouped(all_rows, "touch_weekday_utc"),
        "by_timeframe_and_base_type": {
            tf: {typ: stats([r for r in all_rows if r["timeframe"] == tf and r["base_type"] == typ])
                 for typ in ("RBR", "DBD", "DBR", "RBD")}
            for tf in TFS
        },
        "by_timeframe_and_reaction_number": {
            tf: {str(n): stats([r for r in all_rows if r["timeframe"] == tf and r["reaction_number"] == n])
                 for n in range(1, 6)}
            for tf in TFS
        },
        "by_timeframe_and_penetration_quartile": {
            tf: {str(q): stats([r for r in all_rows if r["timeframe"] == tf and r["penetration_quartile"] == q])
                 for q in range(4)}
            for tf in TFS
        },
        "note": "This is a descriptive event study, not a strategy selection or live-trading authorization."
    }
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    rows_out = Path(a.rows_out); rows_out.parent.mkdir(parents=True, exist_ok=True)
    with rows_out.open("w", encoding="utf-8") as f:
        for row in all_rows: f.write(json.dumps(row, allow_nan=False) + "\n")
    print("REPORT", out, flush=True)
    print("ROWS", rows_out, flush=True)
    print("OVERALL", json.dumps(report["overall"]), flush=True)

if __name__ == "__main__":
    main()
