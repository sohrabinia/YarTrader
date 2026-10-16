"""Run a bounded, research-only variable-range audit on real MT5 CSV history."""
import csv
import json
import statistics
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Research.Brain.fractal_nested_range_discovery import FractalNestedRangeDiscovery

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
OUT = DATA / "fractal_nested_range_audit_20261010.json"
TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
KEEP = 6000
STEP = 25
HORIZON = 24
detector = FractalNestedRangeDiscovery(min_duration=8, max_duration=96, candidate_lengths=8)
report = {
    "status": "RESEARCH_DIAGNOSTIC_ONLY",
    "algorithm_version": detector.VERSION,
    "configuration": {"trailing_bars_per_tf": KEEP, "sample_step_bars": STEP,
                      "horizon_bars": HORIZON, "candidate_lengths": 8,
                      "duration_range_bars": [8, 96]},
    "timeframes": {},
    "safety": "No orders; no inference integration; retrospective labels are diagnostics only.",
}
for tf in TIMEFRAMES:
    path = DATA / f"{tf}.csv"
    if not path.is_file():
        report["timeframes"][tf] = {"status": "MISSING_FILE"}
        continue
    tail = deque(maxlen=KEEP)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tail.append({"time": int(float(row["time"])), "open": float(row["open"]),
                             "high": float(row["high"]), "low": float(row["low"]),
                             "close": float(row["close"])})
            except (ValueError, TypeError, KeyError):
                continue
    rows = list(tail)
    if len(rows) < 200:
        report["timeframes"][tf] = {"status": "INSUFFICIENT_DATA", "bars": len(rows)}
        continue
    scores, durations, widths_atr, up_breaks, down_breaks, both_breaks = [], [], [], 0, 0, 0
    label_examples = []
    end_min = 96
    end_max = len(rows) - HORIZON - 1
    for end in range(end_min, end_max + 1, STEP):
        history = rows[end-96+1:end+1]
        future = rows[end+1:end+1+HORIZON]
        found = detector.discover_at(history, tf, top_k=1)
        if not found["candidates"]:
            continue
        candidate = found["candidates"][0]
        future_high = max(b["high"] for b in future)
        future_low = min(b["low"] for b in future)
        up = future_high > candidate["high"]
        down = future_low < candidate["low"]
        up_breaks += int(up)
        down_breaks += int(down)
        both_breaks += int(up and down)
        scores.append(candidate["candidate_score"])
        durations.append(candidate["duration_bars"])
        widths_atr.append(candidate["width_atr"])
        if len(label_examples) < 3:
            labels = detector.label_outcome(candidate, history + future, horizon=HORIZON)
            label_examples.append({
                "decision_time": candidate["end_time"],
                "duration_bars": candidate["duration_bars"],
                "candidate_score": candidate["candidate_score"],
                "future_label": labels,
            })
    n = len(scores)
    report["timeframes"][tf] = {
        "status": "EVALUATED" if n else "INSUFFICIENT_DATA",
        "bars_loaded": len(rows),
        "evaluated_candidates": n,
        "median_selected_duration_bars": statistics.median(durations) if n else None,
        "median_width_atr": statistics.median(widths_atr) if n else None,
        "median_candidate_score": statistics.median(scores) if n else None,
        "future_boundary_break_up_rate": up_breaks / n if n else None,
        "future_boundary_break_down_rate": down_breaks / n if n else None,
        "future_both_boundaries_breached_rate": both_breaks / n if n else None,
        "interpretation": "Boundary breach rates are descriptive and not predictive accuracy or profitability.",
        "examples": label_examples,
    }
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "output": str(OUT),
                  "timeframes": {tf: {k: v.get(k) for k in
                    ("status", "evaluated_candidates", "median_selected_duration_bars",
                     "median_width_atr", "future_boundary_break_up_rate",
                     "future_boundary_break_down_rate")}
                    for tf, v in report["timeframes"].items()}}, indent=2))
