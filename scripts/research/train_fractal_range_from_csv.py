"""Train the research-only fractal range classifier from MT5 XAUUSD CSV exports.

This script consumes the broker-exported CSV files without placing orders or changing
runtime/production configuration. Output artifacts are written to the chosen research
output directory only.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Research.Brain.fractal_range_learning_engine import FractalRangeLearningEngine, TIMEFRAMES


def read_csv(path):
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"time", "open", "high", "low", "close"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"{path.name}: expected columns {sorted(required)}")
        for row in reader:
            try:
                rows.append({
                    "time": int(float(row["time"])),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })
            except (TypeError, ValueError, KeyError):
                continue
    return rows


def evaluate_numeric_targets(engine, dataset, cutoff):
    """Research-only OOS regression for excursion magnitude and barrier timing."""
    import numpy as np
    samples = dataset["samples"]
    train = [s for s in samples if int(s["time"]) < cutoff and int(s["label_end_time"]) <= cutoff]
    test = [s for s in samples if int(s["time"]) >= cutoff]
    if len(train) < 100 or len(test) < 50:
        return ({"status": "INSUFFICIENT_DATA", "train_samples": len(train), "test_samples": len(test)}, None)
    feature_names = dataset["feature_names"]
    x_train = np.asarray([[float(s["features"].get(k, 0.0)) for k in feature_names] for s in train])
    x_test = np.asarray([[float(s["features"].get(k, 0.0)) for k in feature_names] for s in test])
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-9] = 1.0
    x_train = np.clip((x_train - mean) / scale, -10, 10)
    x_test = np.clip((x_test - mean) / scale, -10, 10)
    design_train = np.column_stack([np.ones(len(x_train)), x_train])
    design_test = np.column_stack([np.ones(len(x_test)), x_test])
    targets = (
        "future_up_atr", "future_down_atr", "bars_to_up_barrier", "bars_to_down_barrier",
        "swing_start_up_offset_atr", "swing_start_down_offset_atr",
        "swing_target_up_atr", "swing_target_down_atr",
        "bars_to_swing_start_up", "bars_to_swing_start_down",
        "bars_to_swing_target_up", "bars_to_swing_target_down",
    )
    report = {"status": "EVALUATED_OOS", "train_samples": len(train), "test_samples": len(test),
              "cutoff_epoch": cutoff, "targets": {}}
    coefficients = {}
    for name in targets:
        y_train = np.asarray([float(s[name]) for s in train])
        y_test = np.asarray([float(s[name]) for s in test])
        penalty = np.eye(design_train.shape[1]) * 2.0
        penalty[0, 0] = 0.0
        coef = np.linalg.solve(design_train.T @ design_train + penalty, design_train.T @ y_train)
        prediction = design_test @ coef
        baseline = np.full(len(y_test), float(np.median(y_train)))
        mae = float(np.mean(np.abs(prediction - y_test)))
        baseline_mae = float(np.mean(np.abs(baseline - y_test)))
        report["targets"][name] = {
            "mae": mae,
            "rmse": float(np.sqrt(np.mean((prediction - y_test) ** 2))),
            "median_baseline_mae": baseline_mae,
            "beats_median_baseline": mae < baseline_mae,
            "test_target_mean": float(np.mean(y_test)),
            "test_prediction_mean": float(np.mean(prediction)),
        }
        coefficients[name] = coef
    return report, {"mean": mean, "scale": scale, "feature_names": feature_names,
                    "target_names": targets, "coefficients": coefficients}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--window", type=int, default=32)
    parser.add_argument("--horizon", type=int, default=12)
    parser.add_argument("--move-threshold-atr", type=float, default=1.0)
    parser.add_argument("--max-samples-per-tf", type=int, default=50000)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    args = parser.parse_args()

    source = Path(args.csv_dir)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    candles = {}
    input_report = {}
    started = time.time()
    for tf in TIMEFRAMES:
        path = source / f"{tf}.csv"
        if not path.is_file():
            input_report[tf] = {"status": "MISSING_FILE"}
            continue
        rows = read_csv(path)
        if rows:
            candles[tf] = rows
            input_report[tf] = {
                "status": "LOADED",
                "rows": len(rows),
                "first_epoch": rows[0]["time"],
                "last_epoch": rows[-1]["time"],
            }
        else:
            input_report[tf] = {"status": "EMPTY_OR_INVALID"}

    if not candles:
        raise SystemExit(f"No usable timeframe CSV files in {source}")

    engine = FractalRangeLearningEngine(
        window=args.window,
        horizon=args.horizon,
        move_threshold_atr=args.move_threshold_atr,
        max_samples_per_tf=args.max_samples_per_tf,
    )
    dataset = engine.build_dataset(candles)
    # Release the raw CSV rows before model arrays are materialized.
    del candles

    # Persist the exact sampled rows and labels so this experiment is reproducible.
    samples_path = out / "dataset_samples.jsonl"
    with samples_path.open("w", encoding="utf-8", newline="\n") as handle:
        for sample in dataset["samples"]:
            handle.write(json.dumps(sample, separators=(",", ":")) + "\n")

    result = engine.train_evaluate(dataset, train_fraction=args.train_fraction)
    model = result.pop("model", None)
    numeric_report = {"status": "NOT_RUN"}
    numeric_model = None
    test_range = result.get("metrics", {}).get("test_time_range", [])
    if result.get("status") == "EVALUATED_OOS" and test_range:
        numeric_report, numeric_model = evaluate_numeric_targets(engine, dataset, int(test_range[0]))

    # Three expanding-window folds with non-overlapping test windows. Each fold
    # uses a single timestamp cutoff across all timeframes and purges overlapping labels.
    ordered_times = sorted({int(sample["time"]) for sample in dataset["samples"]})
    walk_forward = []
    fold_edges = (0.50, 0.65, 0.80, 0.95)
    for fold_index, (train_fraction, test_fraction) in enumerate(zip(fold_edges, fold_edges[1:]), 1):
        train_cut = ordered_times[min(len(ordered_times) - 1, int((len(ordered_times) - 1) * train_fraction))]
        test_cut = ordered_times[min(len(ordered_times) - 1, int((len(ordered_times) - 1) * test_fraction))]
        fold_result = engine.train_evaluate(
            dataset, train_fraction=args.train_fraction,
            train_until=train_cut, test_until=test_cut,
        )
        fold_result.pop("model", None)
        walk_forward.append({
            "fold": fold_index,
            "train_until_epoch": train_cut,
            "test_until_epoch": test_cut,
            "status": fold_result.get("status"),
            "train_samples": fold_result.get("train_samples", 0),
            "test_samples": fold_result.get("test_samples", 0),
            "metrics": fold_result.get("metrics", {}),
            "reason": fold_result.get("reason"),
        })

    summary = {key: value for key, value in dataset.items() if key != "samples"}
    summary["sample_counts_by_timeframe"] = {
        tf: sum(s["timeframe"] == tf for s in dataset["samples"])
        for tf in dataset["timeframes"]
    }
    summary["input_files"] = input_report
    summary["sampling"] = "Evenly spaced over each timeframe's full eligible history; latest eligible sample included."
    summary["temporal_validation"] = {
        "method": "single global chronological holdout with label-window purge",
        "train_fraction_requested": args.train_fraction,
        "cutoff_epoch": result.get("metrics", {}).get("test_time_range", [None])[0],
    }
    (out / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = {
        "symbol": "XAUUSD",
        "source": str(source.resolve()),
        "output": str(out.resolve()),
        "dataset": summary,
        "evaluation": result,
        "numeric_regression_evaluation": numeric_report,
        "walk_forward": walk_forward,
        "sample_dataset": samples_path.name,
        "elapsed_seconds": round(time.time() - started, 2),
        "safety": "RESEARCH_ONLY_NOT_CONNECTED_TO_ORDER_EXECUTION",
        "limitations": [
            "Numeric regression estimates future excursion magnitude and bars-to-barrier, but does not estimate a validated move-start zone.",
            "No profitability or live-trading claim is made.",
            "The holdout result is historical and may not generalize to future market regimes.",
        ],
    }
    if model is not None:
        import numpy as np
        np.savez_compressed(
            out / "fractal_range_model.npz",
            weights=model["weights"], bias=model["bias"], mean=model["mean"],
            scale=model["scale"], classes=model["classes"],
        )
        (out / "model_features.json").write_text(json.dumps({
            "feature_names": model["feature_names"],
            "version": engine.VERSION,
            "label_definition": dataset["label_definition"],
        }, indent=2), encoding="utf-8")
        report["model_artifact"] = "fractal_range_model.npz"
    if numeric_model is not None:
        import numpy as np
        np.savez_compressed(
            out / "fractal_range_numeric_model.npz",
            mean=numeric_model["mean"], scale=numeric_model["scale"],
            **{f"coef_{name}": coef for name, coef in numeric_model["coefficients"].items()},
        )
        (out / "numeric_model_features.json").write_text(json.dumps({
            "feature_names": numeric_model["feature_names"],
            "target_names": numeric_model["target_names"],
            "target_units": {
                "future_up_atr": "ATR multiples",
                "future_down_atr": "ATR multiples",
                "bars_to_up_barrier": "primary timeframe bars; horizon+1 means barrier not reached",
                "bars_to_down_barrier": "primary timeframe bars; horizon+1 means barrier not reached",
                "swing_start_up_offset_atr": "ATR multiples from decision close; retrospective swing-origin proxy",
                "swing_start_down_offset_atr": "ATR multiples from decision close; retrospective swing-origin proxy",
                "swing_target_up_atr": "upward swing target distance in ATR multiples",
                "swing_target_down_atr": "downward swing target distance in ATR multiples",
                "bars_to_swing_start_up": "bars from decision to retrospective swing-origin proxy",
                "bars_to_swing_start_down": "bars from decision to retrospective swing-origin proxy",
                "bars_to_swing_target_up": "bars from decision to future swing high",
                "bars_to_swing_target_down": "bars from decision to future swing low",
            },
        }, indent=2), encoding="utf-8")
        report["numeric_model_artifact"] = "fractal_range_numeric_model.npz"
    (out / "evaluation_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "status": result.get("status"),
        "samples": dataset["sample_count"],
        "timeframes": dataset["timeframes"],
        "output": str(out.resolve()),
        "elapsed_seconds": report["elapsed_seconds"],
        "metrics": result.get("metrics", {}),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
