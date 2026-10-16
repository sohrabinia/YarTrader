"""Compare interpretable feature subsets on frozen historical samples.

This script never downloads data or touches broker/runtime execution. It reuses the
persisted sample set and applies the same chronological fold boundaries to simple
and range-only models. Full-model scores from the same source directory are the comparator.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Research.Brain.fractal_range_learning_engine import FractalRangeLearningEngine

DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="fractal_range_training_20261010_v4")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    source_name = Path(args.source).name
    source = (DATA / source_name).resolve()
    output = Path(args.output).resolve() if args.output else DATA / f"{source_name}_simple_feature_comparison.json"
    started = time.time()
    summary = json.loads((source / "dataset_summary.json").read_text(encoding="utf-8"))
    samples = []
    with (source / "dataset_samples.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                samples.append(json.loads(line))
    dataset = {
        "samples": samples,
        "feature_names": summary["feature_names"],
        "timeframes": summary.get("timeframes", []),
        "label_definition": summary.get("label_definition", {}),
    }
    ordered = sorted({int(s["time"]) for s in samples})
    if len(ordered) < 1000:
        raise SystemExit(f"Insufficient persisted samples: {len(ordered)}")
    engine = FractalRangeLearningEngine()
    modes = ("simple", "range_only")
    folds = ((0.50, 0.65), (0.65, 0.80), (0.80, 0.95))
    results = []
    for fold_index, (train_frac, test_frac) in enumerate(folds, 1):
        train_cut = ordered[min(len(ordered) - 1, int((len(ordered) - 1) * train_frac))]
        test_cut = ordered[min(len(ordered) - 1, int((len(ordered) - 1) * test_frac))]
        fold = {
            "fold": fold_index,
            "train_cut_epoch": train_cut,
            "test_cut_epoch": test_cut,
            "modes": {},
        }
        for mode in modes:
            result = engine.train_evaluate(
                dataset, train_fraction=0.70, train_until=train_cut,
                test_until=test_cut, feature_mode=mode,
            )
            result.pop("model", None)
            fold["modes"][mode] = result
        results.append(fold)

    prior_path = source / "evaluation_report.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    full_by_fold = {}
    for item in prior.get("walk_forward", []):
        full_by_fold[str(item.get("fold"))] = {
            "status": item.get("status"),
            "train_samples": item.get("train_samples"),
            "test_samples": item.get("test_samples"),
            "metrics": item.get("metrics", {}),
        }
    report = {
        "status": "RESEARCH_ONLY",
        "symbol": "XAUUSD",
        "source_samples": str(source / "dataset_samples.jsonl"),
        "sample_count": len(samples),
        "feature_modes": {
            "full": "Full-model metrics from this source directory are reused without retraining.",
            "simple": "13 interpretable features: local range geometry plus M15/H1/H4/D1 position and range width.",
            "range_only": "4 local range geometry features only.",
        },
        "folds": results,
        "prior_full_model_walk_forward": full_by_fold,
        "guardrails": [
            "All folds are chronological; training samples whose label end crosses train cutoff are purged.",
            "No random shuffle, downloader, broker, order routing, or live inference.",
            "Historical feature selection is diagnostic and does not authorize production model promotion.",
        ],
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    compact = {
        "output": str(output),
        "sample_count": len(samples),
        "elapsed_seconds": report["elapsed_seconds"],
        "folds": [
            {
                "fold": f["fold"],
                "simple": {
                    "status": f["modes"]["simple"].get("status"),
                    "features": f["modes"]["simple"].get("feature_count"),
                    "metrics": f["modes"]["simple"].get("metrics", {}),
                },
                "range_only": {
                    "status": f["modes"]["range_only"].get("status"),
                    "features": f["modes"]["range_only"].get("feature_count"),
                    "metrics": f["modes"]["range_only"].get("metrics", {}),
                },
                "prior_full": full_by_fold.get(str(f["fold"]), {}),
            }
            for f in results
        ],
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
