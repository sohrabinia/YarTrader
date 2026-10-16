"""Summarize the trained Base-reaction grid by depth/revisit/timeframe.

This aggregates already-computed model cells. It is descriptive only: overlapping
Base events and alternative entry configurations are not independent trades.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def summarize_cells(cells):
    n = sum(int(x["samples"]) for x in cells)
    if not n:
        return {"samples": 0}
    wins = sum(float(x["win_rate"]) * int(x["samples"]) for x in cells)
    mean = sum(float(x["mean_net_r"]) * int(x["samples"]) for x in cells) / n
    # Recover within-cell sum of squares from each cell's standard error, then
    # add between-cell variation for the aggregate sample standard error.
    sse = 0.0
    for x in cells:
        ni = int(x["samples"])
        if ni > 1:
            se = float(x.get("mean_net_r_standard_error", 1e9))
            sse += se * se * ni * (ni - 1)
        sse += ni * (float(x["mean_net_r"]) - mean) ** 2
    variance = sse / (n - 1) if n > 1 else 1e18
    se_mean = math.sqrt(max(0.0, variance) / n)
    win_rate = wins / n
    return {"samples": n, "win_rate_pct": round(100 * win_rate, 2),
            "mean_net_R_proxy": round(mean, 4),
            "mean_net_R_standard_error": round(se_mean, 4),
            "mean_net_R_95pct_lower_bound": round(mean - 1.96 * se_mean, 4),
            "profit_factor_not_available_from_cell_summary": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    dimensions = {
        "by_timeframe": lambda f: (f[0],),
        "by_depth": lambda f: (f[6],),
        "by_reaction_number": lambda f: (f[5],),
        "by_timeframe_depth": lambda f: (f[0], f[6]),
        "by_timeframe_reaction": lambda f: (f[0], f[5]),
        "by_depth_reaction": lambda f: (f[6], f[5]),
        "by_parent_relation": lambda f: (f[3],),
    }
    buckets = {name: defaultdict(list) for name in dimensions}
    cells = []
    for key, stat in model.get("groups", {}).items():
        fields = key.split("|")
        if len(fields) != 7:
            continue
        cells.append(stat)
        for name, selector in dimensions.items():
            buckets[name][selector(fields)].append(stat)
    result = {
        "status": "DESCRIPTIVE_SENSITIVITY_ONLY_NOT_TRADING_READY",
        "source_model": str(args.model),
        "model_groups": len(cells),
        "minimum_profile_samples": model.get("min_samples", 40),
        "overall_cell_summary": summarize_cells(cells),
        "aggregations": {},
        "limitations": [
            "Aggregates overlap across Base events and alternative depth/revisit strategies.",
            "Aggregated groups are not a single executable strategy and do not prove an edge.",
            "Costs are a 0.05 ATR round-trip proxy, not measured broker costs.",
            "Use chronological holdout, effective independent sample estimates and multiple-comparison correction.",
        ],
    }
    for name, groups in buckets.items():
        result["aggregations"][name] = [
            {"key": list(key), **summarize_cells(vals)}
            for key, vals in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0]))
        ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print("SUMMARY", out, "model_groups", len(cells), "dimensions", len(dimensions))
    print("OVERALL", json.dumps(result["overall_cell_summary"]))
    for name in ("by_depth", "by_reaction_number", "by_timeframe_depth", "by_timeframe_reaction"):
        print(name, json.dumps(result["aggregations"][name]))


if __name__ == "__main__":
    main()
