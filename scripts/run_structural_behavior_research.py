"""Run reproducible, non-trading structural Base research on local MT4 HST history."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
from src.Research.Brain.multitimeframe_base_transition_engine import (
    TIMEFRAME_ORDER, detect_base_departures,
)
from src.Intelligence.Execution.structural_behavior_mining import (
    mine_structural_behaviors, persist_and_aggregate_structural_behaviors,
    validate_structural_behavior_samples,
)


def _utc(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--horizon-bars", type=int, default=20)
    parser.add_argument("--min-motif-samples", type=int, default=5)
    parser.add_argument("--walk-forward-fractions", default="0.6,0.7,0.8",
                        help="Comma-separated chronological train fractions for robustness checks")
    parser.add_argument("--output", default=None)
    parser.add_argument("--database", default=None)
    args = parser.parse_args()
    if args.horizon_bars < 1 or args.min_motif_samples < 2:
        parser.error("horizon-bars must be >= 1 and min-motif-samples must be >= 2")

    provider = MT4HistoricalDataProvider()
    bars_by_tf = {}
    coverage = {}
    for tf in TIMEFRAME_ORDER:
        path = provider._history_file(args.symbol, tf)
        rows = provider._read_hst(path) if path.exists() else []
        bars = sorted(
            ({"time": int(row["time"]), "open": float(row["open"]),
              "high": float(row["high"]), "low": float(row["low"]),
              "close": float(row["close"])} for row in rows),
            key=lambda row: row["time"],
        )
        bars_by_tf[tf] = bars
        if bars:
            coverage[tf] = {
                "bars": len(bars), "first_utc": _utc(bars[0]["time"]),
                "last_utc": _utc(bars[-1]["time"]),
            }
    if not any(bars_by_tf.values()):
        raise RuntimeError(f"No local MT4 history available for {args.symbol}.")

    events_by_tf = {}
    for tf, bars in bars_by_tf.items():
        step = 1 if tf in {"M30", "M15", "M5", "M1"} else 2
        events_by_tf[tf] = detect_base_departures(
            bars, tf, scan_step=step, horizon=0,
        ) if len(bars) >= 50 else []
    latest_epoch = max(bar["time"] for bars in bars_by_tf.values() for bar in bars)
    research = mine_structural_behaviors(
        events_by_tf, bars_by_tf, now=latest_epoch,
        horizon_bars=args.horizon_bars,
        min_pattern_samples=args.min_motif_samples,
    )
    try:
        walk_forward_fractions = sorted({float(value.strip()) for value in args.walk_forward_fractions.split(",")})
    except ValueError as exc:
        parser.error(f"Invalid --walk-forward-fractions: {exc}")
    if not walk_forward_fractions or any(not 0.0 < value < 1.0 for value in walk_forward_fractions):
        parser.error("walk-forward fractions must be between 0 and 1")
    walk_forward_sensitivity = {
        f"train_fraction_{fraction:.2f}": validate_structural_behavior_samples(
            research["samples"], train_fraction=fraction,
        )
        for fraction in walk_forward_fractions
    }
    database = Path(args.database) if args.database else (
        ROOT / "runtime_logs" / "research" / f"structural_behavior_{args.symbol.upper()}.sqlite3"
    )
    result = persist_and_aggregate_structural_behaviors(
        research, str(database), min_pattern_samples=args.min_motif_samples,
    )
    report = {
        "report_version": 2,
        "algorithm_version": "structural_v2",
        "symbol": args.symbol.upper(),
        "data_source": "LOCAL_MT4_HST",
        "data_cutoff_utc": _utc(latest_epoch),
        "timeframe_coverage": coverage,
        "base_events_by_timeframe": {tf: len(events) for tf, events in events_by_tf.items()},
        "structural_behavior_analysis": result,
        "walk_forward_sensitivity": walk_forward_sensitivity,
        "research_only": True,
        "trade_edge_validated": False,
        "notes": [
            "This report is descriptive research, not a strategy profitability backtest.",
            "The chronological holdout evaluates price excursions only; no broker-costed fills are simulated.",
            "Classic QM/flag detectors were not found in the inspected code path, so no direct legacy-pattern comparison is claimed.",
        ],
    }
    output = Path(args.output) if args.output else (
        ROOT / "runtime_logs" / "research" / f"structural_behavior_{args.symbol.upper()}_latest.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temp.replace(output)
    print(json.dumps({
        "status": result.get("status"),
        "symbol": args.symbol.upper(),
        "data_cutoff_utc": _utc(latest_epoch),
        "timeframes_with_data": len(coverage),
        "events": sum(len(v) for v in events_by_tf.values()),
        "completed_touch_samples": result.get("completed_touch_samples"),
        "durable_observation_count": result.get("durable_observation_count"),
        "motifs": result.get("motif_count"),
        "walk_forward_validation": result.get("walk_forward_validation"),
        "walk_forward_sensitivity": {
            key: {
                "status": value.get("status"),
                "training_samples_after_embargo": value.get("training_samples_after_embargo"),
                "oos_samples": value.get("oos_samples"),
                "matched_oos_samples": value.get("matched_oos_samples"),
                "mean_continuation_delta_vs_parent_only": value.get("mean_continuation_delta_vs_parent_only"),
                "mean_reversal_delta_vs_parent_only": value.get("mean_reversal_delta_vs_parent_only"),
                "trade_edge_validated": value.get("trade_edge_validated", False),
            }
            for key, value in walk_forward_sensitivity.items()
        },
        "output": str(output),
        "database": str(database),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
