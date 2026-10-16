"""Exploratory score-vs-outcome audit for variable-duration range candidates."""
import csv, json, statistics, sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Research.Brain.fractal_nested_range_discovery import FractalNestedRangeDiscovery

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
OUT = DATA / "fractal_nested_range_score_buckets_20261010.json"
TFS = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
KEEP, STEP, HORIZON = 6000, 25, 24
detector = FractalNestedRangeDiscovery(min_duration=8, max_duration=96, candidate_lengths=8)
report = {
    "status": "EXPLORATORY_DESCRIPTIVE_NOT_OOS_MODEL_EVALUATION",
    "method": "For each sampled endpoint, score all candidate lengths using past bars only; compare score groups to next 24-bar boundary breaches.",
    "caveats": ["Overlapping windows/outcomes are dependent.", "Score groups are not an independent test.",
                "Boundary breaches are not trade profitability.", "Monthly sample count may be too small."],
    "configuration": {"trailing_bars": KEEP, "step_bars": STEP, "horizon_bars": HORIZON,
                      "candidate_durations": [8, 96], "candidate_lengths": 8},
    "timeframes": {}
}
for tf in TFS:
    path = DATA / f"{tf}.csv"
    if not path.is_file():
        report["timeframes"][tf] = {"status": "MISSING_FILE"}
        continue
    tail = deque(maxlen=KEEP)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                tail.append({"time": int(float(row["time"])), "open": float(row["open"]),
                             "high": float(row["high"]), "low": float(row["low"]),
                             "close": float(row["close"])})
            except (ValueError, TypeError, KeyError):
                continue
    rows = list(tail)
    all_candidates = []
    endpoint_count = 0
    for end in range(96, len(rows) - HORIZON, STEP):
        history = rows[end-95:end+1]
        future = rows[end+1:end+1+HORIZON]
        candidates = detector.discover_at(history, tf, top_k=8)["candidates"]
        if not candidates:
            continue
        endpoint_count += 1
        future_high = max(b["high"] for b in future)
        future_low = min(b["low"] for b in future)
        for c in candidates:
            up = future_high > c["high"]
            down = future_low < c["low"]
            all_candidates.append({
                "score": float(c["candidate_score"]),
                "duration": int(c["duration_bars"]),
                "width_atr": float(c["width_atr"]),
                "up_breach": bool(up), "down_breach": bool(down),
                "both_breaches": bool(up and down),
            })
    all_candidates.sort(key=lambda x: x["score"])
    n = len(all_candidates)
    buckets = []
    if n:
        for label, lo, hi in (("LOW_SCORE", 0, n//3), ("MID_SCORE", n//3, (2*n)//3), ("HIGH_SCORE", (2*n)//3, n)):
            group = all_candidates[lo:hi]
            if not group:
                continue
            buckets.append({
                "bucket": label, "candidate_count": len(group),
                "score_min": min(x["score"] for x in group),
                "score_max": max(x["score"] for x in group),
                "median_duration_bars": statistics.median(x["duration"] for x in group),
                "median_width_atr": statistics.median(x["width_atr"] for x in group),
                "up_boundary_breach_rate": sum(x["up_breach"] for x in group)/len(group),
                "down_boundary_breach_rate": sum(x["down_breach"] for x in group)/len(group),
                "both_boundary_breach_rate": sum(x["both_breaches"] for x in group)/len(group),
            })
    report["timeframes"][tf] = {
        "status": "EVALUATED" if n else "INSUFFICIENT_DATA",
        "bars_loaded": len(rows), "sampled_endpoints": endpoint_count,
        "candidate_observations": n,
        "independent_endpoints_warning": "Candidate observations reuse the same future path at each endpoint.",
        "score_tertiles": buckets,
    }
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "output": str(OUT),
                  "timeframes": {tf: {"sampled_endpoints": v.get("sampled_endpoints"),
                                      "candidate_observations": v.get("candidate_observations"),
                                      "score_tertiles": v.get("score_tertiles")}
                                 for tf, v in report["timeframes"].items()}}, indent=2))
