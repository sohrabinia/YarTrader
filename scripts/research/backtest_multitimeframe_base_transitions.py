"""Run YarTrader's multitimeframe base/transition event study on MT5 CSV bars.

Example:
  python scripts/research/backtest_multitimeframe_base_transitions.py
  python ... --m1-max-bars 300000 --scan-m1 30
Research-only; no orders or production signal changes.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Research.Brain.multitimeframe_base_transition_engine import (
    TIMEFRAME_ORDER, detect_base_departures, attach_market_context, build_hierarchy,
    label_exit_to_next_base, simulate_departure_trades
)

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
DEFAULT_OUT = DATA / "multitimeframe_base_transition_study.json"
FILES = ("MN1","W1","D1","H4","H1","M15","M5","M1")
DEFAULT_STEPS = {"MN1":1,"W1":1,"D1":1,"H4":2,"H1":2,"M15":5,"M5":10,"M1":20}


def load_bars(tf: str, max_bars: int):
    path = DATA / f"{tf}.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, usecols=lambda c: c in {"time","timestamp","open","high","low","close"})
    if "time" not in df.columns and "timestamp" in df.columns:
        df = df.rename(columns={"timestamp":"time"})
    if not {"time","open","high","low","close"}.issubset(df.columns):
        return []
    for c in ("time","open","high","low","close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["time","open","high","low","close"]).drop_duplicates("time").sort_values("time")
    if max_bars > 0 and len(df) > max_bars:
        df = df.iloc[-max_bars:]
    # Tuple rows avoid pandas' per-cell overhead; dictionaries are the public engine contract.
    return [{"time":int(t),"open":float(o),"high":float(h),"low":float(l),"close":float(c)}
            for t,o,h,l,c in df[["time","open","high","low","close"]].itertuples(index=False, name=None)]


def pct(num, den):
    return round(100.0*num/den, 2) if den else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--m1-max-bars", type=int, default=600000,
                        help="Keep only most recent N M1 bars to bound memory; 0 means all bars")
    parser.add_argument("--scan-m1", type=int, default=DEFAULT_STEPS["M1"])
    parser.add_argument("--scan-m5", type=int, default=DEFAULT_STEPS["M5"])
    parser.add_argument("--scan-m15", type=int, default=DEFAULT_STEPS["M15"])
    parser.add_argument("--scan-h1", type=int, default=DEFAULT_STEPS["H1"])
    parser.add_argument("--scan-h4", type=int, default=DEFAULT_STEPS["H4"])
    args = parser.parse_args()
    steps = dict(DEFAULT_STEPS, M1=args.scan_m1, M5=args.scan_m5, M15=args.scan_m15,
                 H1=args.scan_h1, H4=args.scan_h4)
    bars_by_tf, events_by_tf, tf_meta = {}, {}, {}
    for tf in FILES:
        bars = load_bars(tf, args.m1_max_bars if tf == "M1" else 0)
        bars_by_tf[tf] = bars
        if len(bars) < 50:
            events_by_tf[tf] = []
            tf_meta[tf] = {"status":"INSUFFICIENT_DATA","bars":len(bars)}
            print(tf, "insufficient bars", len(bars), flush=True)
            continue
        events = detect_base_departures(bars, tf, scan_step=steps[tf])
        events_by_tf[tf] = events
        tf_meta[tf] = {
            "status":"EVALUATED", "bars":len(bars), "scan_step":steps[tf],
            "start_utc":datetime.fromtimestamp(bars[0]["time"],timezone.utc).isoformat(),
            "end_utc":datetime.fromtimestamp(bars[-1]["time"],timezone.utc).isoformat(),
            "detected_events":len(events),
            "base_types":dict(Counter(e["base_type"] for e in events)),
            "warning":"sampled scan; some base departures may be missed"
        }
        print(tf, "bars", len(bars), "events", len(events), flush=True)

    # Attach context using only candles whose close time is <= the event's confirmation time.
    print("ATTACHING_CAUSAL_CONTEXT", flush=True)
    attach_market_context(events_by_tf, bars_by_tf)
    print("BUILDING_NESTED_HIERARCHY", flush=True)
    hierarchy = build_hierarchy(events_by_tf)
    print("LABELING_EXIT_TRANSITIONS", flush=True)
    transitions = label_exit_to_next_base(events_by_tf, bars_by_tf, horizon_bars=24)
    print("SIMULATING_BASELINE_TRADES", flush=True)
    baseline_trade_backtest = simulate_departure_trades(
        events_by_tf, bars_by_tf, transitions, horizon_bars=24,
        stop_buffer_atr=0.1, target_r=2.0, round_trip_cost_atr=0.05
    )
    transition_counts = {}
    for tf in FILES:
        tf_rows = [x for x in transitions if x["timeframe"] == tf]
        counts = Counter(x["first_transition"] for x in tf_rows)
        transition_counts[tf] = {
            "n":len(tf_rows), "first_transition_counts":dict(counts),
            "first_transition_pct":{k:pct(v,len(tf_rows)) for k,v in counts.items()},
            "origin_retest_n":sum(x["origin_retest_bars"] is not None for x in tf_rows),
            "failed_exit_closeback_n":sum(x.get("failed_exit_closeback_bars") is not None for x in tf_rows),
            "ambiguous_same_bar_n":sum(x["first_transition"] == "ambiguous_same_bar" for x in tf_rows),
            "next_base_touch_n":sum(x["next_base_touch_bars"] is not None for x in tf_rows),
            "corridor_pause_candidate_n":sum(x["corridor_pause_candidate"] for x in tf_rows),
            "corridor_pause_departure_n":sum(x.get("corridor_pause_departure_direction") is not None for x in tf_rows),
            "corridor_pause_aligned_departure_n":sum(x.get("corridor_pause_departure_aligned") is True for x in tf_rows),
            "corridor_pause_opposed_departure_n":sum(x.get("corridor_pause_departure_aligned") is False for x in tf_rows),
        }
    type_transition = {}
    for tf in FILES:
        type_transition[tf] = {}
        for typ in ("RBR","DBD","DBR","RBD"):
            rows = [x for x in transitions if x["timeframe"] == tf and x["base_type"] == typ]
            counts = Counter(x["first_transition"] for x in rows)
            type_transition[tf][typ] = {
                "n":len(rows), "first_transition_counts":dict(counts),
                "first_transition_pct":{k:pct(v,len(rows)) for k,v in counts.items()},
                "next_base_touch_pct":pct(sum(x["next_base_touch_bars"] is not None for x in rows),len(rows)),
                "origin_retest_pct":pct(sum(x["origin_retest_bars"] is not None for x in rows),len(rows)),
                "corridor_pause_pct":pct(sum(x["corridor_pause_candidate"] for x in rows),len(rows)),
                "corridor_pause_departure_pct":pct(sum(x.get("corridor_pause_departure_direction") is not None for x in rows),len(rows)),
                "corridor_pause_aligned_departure_pct":pct(sum(x.get("corridor_pause_departure_aligned") is True for x in rows),len(rows)),
            }
    event_by_id = {e["event_id"]:e for vals in events_by_tf.values() for e in vals}
    hierarchy_by_id = {x["event_id"]:x for x in hierarchy}
    hierarchy_transition_summary = {}
    context_transition_summary = {}
    for tf in FILES:
        tf_rows = [x for x in transitions if x["timeframe"] == tf]
        hierarchy_transition_summary[tf] = {}
        buckets = {}
        for row in tf_rows:
            h = hierarchy_by_id.get(row["event_id"], {})
            aligned, opposing = h.get("child_alignment_count",0), h.get("child_opposition_count",0)
            bucket = ("mixed_children" if aligned and opposing else
                      "aligned_children" if aligned else
                      "opposing_children" if opposing else "no_confirmed_children")
            buckets.setdefault(bucket, []).append(row)
        for bucket, rows in buckets.items():
            counts = Counter(x["first_transition"] for x in rows)
            hierarchy_transition_summary[tf][bucket] = {
                "n":len(rows), "first_transition_counts":dict(counts),
                "first_transition_pct":{k:pct(v,len(rows)) for k,v in counts.items()}
            }
        context_transition_summary[tf] = {}
        for context_tf in ("D1","H4","H1"):
            context_transition_summary[tf][context_tf] = {"trend_regime":{}, "volatility_regime":{}}
            for axis in ("trend_regime","volatility_regime"):
                groups = {}
                for row in tf_rows:
                    ev = event_by_id.get(row["event_id"], {})
                    ctx = ev.get("market_context",{}).get(context_tf,{})
                    if ctx.get("status") != "AVAILABLE":
                        continue
                    value = ctx.get(axis)
                    if value is not None:
                        groups.setdefault(value, []).append(row)
                for value, rows in groups.items():
                    counts = Counter(x["first_transition"] for x in rows)
                    context_transition_summary[tf][context_tf][axis][value] = {
                        "n":len(rows), "first_transition_counts":dict(counts),
                        "first_transition_pct":{k:pct(v,len(rows)) for k,v in counts.items()}
                    }

    report = {
        "status":"RESEARCH_ONLY_NOT_TRADING_READY",
        "algorithm_version":"mtf_base_transition_v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "symbol":"XAUUSD", "source":"Alpari-MT5-Demo broker-specific OHLC history",
        "definitions":{
            "base":"2-6 bars, width <= 1.5 rolling ATR, mean body <= 0.55 ATR",
            "incoming_leg":"4-bar close displacement >= 0.8 ATR",
            "exit":"confirmed close beyond base edge with >= 1.0 ATR displacement from midpoint, confirmation within 1-3 bars",
            "types":{"RBR":"up leg, up departure","DBD":"down leg, down departure","DBR":"down leg, up departure","RBD":"up leg, down departure"},
            "nested":"child base time span lies inside parent base; child departure must already be confirmed by parent departure timestamp",
            "next_base":"nearest other base zone whose departure was confirmed before the current exit; future-confirmed zones are excluded",
            "transition_labels":"first of continuation +/-1 ATR barrier, reversal +/-1 ATR barrier, origin retest, failed-exit closeback, next-known-base touch; 24 bars; simultaneous first hits are marked ambiguous",
            "market_context":"trend and ATR/rolling-median volatility for each timeframe, using only bars whose close time is <= event confirmation time",
            "limitations":["sampled scans miss some candidates","transition outcomes are event diagnostics, not a net-PnL backtest",
                          "no spread, commission, slippage, entry/exit execution model or position sizing",
                          "M1 is capped to most recent N bars unless --m1-max-bars 0; lower-TF context outside that window is unavailable",
                          "same-bar competing barriers may be ambiguous in OHLC data",
                          "no live signal or order integration"]
        },
        "configuration":{"scan_steps":steps,"m1_max_bars":args.m1_max_bars,"horizon_bars":24},
        "timeframes":tf_meta,
        "hierarchy_summary":{
            "events_with_child_bases":sum(bool(any(v["count"] for v in x["child_bases"].values())) for x in hierarchy),
            "events_with_aligned_children":sum(x["child_alignment_count"]>0 for x in hierarchy),
            "events_with_opposing_children":sum(x["child_opposition_count"]>0 for x in hierarchy),
            "n":len(hierarchy)
        },
        "transition_summary":transition_counts,
        "transition_by_base_type":type_transition,
        "transition_by_nested_child_alignment":hierarchy_transition_summary,
        "transition_by_closed_higher_timeframe_regime":context_transition_summary,
        "baseline_trade_backtest":baseline_trade_backtest,
        "events_by_timeframe":events_by_tf,
        "hierarchy_events":hierarchy,
        "transition_events":transitions
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print("OUTPUT",out,flush=True)
    print("HIERARCHY",json.dumps(report["hierarchy_summary"]),flush=True)
    print("TRANSITIONS",json.dumps(transition_counts),flush=True)


if __name__ == "__main__":
    main()
