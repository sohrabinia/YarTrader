"""Per-timeframe diagnostics for a trained research-only fractal model."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runtime_logs" / "mt5_gold_history_full" / "fractal_range_training_20261010_v3"
REPORT = json.loads((RUN / "evaluation_report.json").read_text(encoding="utf-8"))
FEATURE_META = json.loads((RUN / "model_features.json").read_text(encoding="utf-8"))
NUM_META = json.loads((RUN / "numeric_model_features.json").read_text(encoding="utf-8"))
with (RUN / "dataset_samples.jsonl").open(encoding="utf-8") as f:
    samples = [json.loads(line) for line in f if line.strip()]
cutoff = int(REPORT["evaluation"]["metrics"]["test_time_range"][0])
features = FEATURE_META["feature_names"]
num_targets = NUM_META["target_names"]
model = np.load(RUN / "fractal_range_model.npz")
num_model = np.load(RUN / "fractal_range_numeric_model.npz")
groups = defaultdict(list)
for s in samples:
    groups[s["timeframe"]].append(s)

out = {
    "status": "DIAGNOSTIC_ONLY",
    "run": str(RUN),
    "cutoff_epoch": cutoff,
    "note": "Global model scored separately by timeframe. Per-TF majority and median baselines are fit only on pre-cutoff samples whose label window ends by cutoff. No trading simulation.",
    "classification_by_timeframe": {},
    "numeric_by_timeframe": {},
}
for tf, rows in sorted(groups.items()):
    train = [s for s in rows if int(s["time"]) < cutoff and int(s["label_end_time"]) <= cutoff]
    test = [s for s in rows if int(s["time"]) >= cutoff]
    if not train or not test:
        out["classification_by_timeframe"][tf] = {"train": len(train), "test": len(test), "status": "INSUFFICIENT"}
        continue
    x = np.asarray([[float(s["features"].get(k, 0.0)) for k in features] for s in test])
    x = np.clip((x - model["mean"]) / np.where(model["scale"] < 1e-9, 1.0, model["scale"]), -10, 10)
    logits = np.clip(x @ model["weights"] + model["bias"], -30, 30)
    logits -= logits.max(axis=1, keepdims=True)
    probs = np.exp(logits); probs /= probs.sum(axis=1, keepdims=True)
    classes = model["classes"]
    pred = classes[np.argmax(probs, axis=1)]
    actual = np.asarray([int(s["label"]) for s in test])
    counts = Counter(int(s["label"]) for s in train)
    majority_class = counts.most_common(1)[0][0]
    baseline_acc = float(np.mean(actual == majority_class))
    recalls = [float(np.mean(pred[actual == c] == c)) for c in sorted(set(actual.tolist())) if np.any(actual == c)]
    out["classification_by_timeframe"][tf] = {
        "train_samples": len(train), "test_samples": len(test),
        "accuracy": float(np.mean(pred == actual)),
        "balanced_accuracy": float(np.mean(recalls)),
        "train_majority_class": majority_class,
        "per_tf_majority_baseline_accuracy": baseline_acc,
        "beats_per_tf_majority_baseline": bool(np.mean(pred == actual) > baseline_acc),
    }
    nx = np.asarray([[float(s["features"].get(k, 0.0)) for k in NUM_META["feature_names"]] for s in test])
    nx = np.clip((nx - num_model["mean"]) / np.where(num_model["scale"] < 1e-9, 1.0, num_model["scale"]), -10, 10)
    out["numeric_by_timeframe"][tf] = {"train_samples": len(train), "test_samples": len(test), "targets": {}}
    for name in num_targets:
        coef = num_model[f"coef_{name}"]
        prediction = np.column_stack([np.ones(len(nx)), nx]) @ coef
        y = np.asarray([float(s[name]) for s in test])
        baseline_value = float(np.median([float(s[name]) for s in train]))
        mae = float(np.mean(np.abs(prediction - y)))
        baseline_mae = float(np.mean(np.abs(baseline_value - y)))
        out["numeric_by_timeframe"][tf]["targets"][name] = {
            "mae": mae, "per_tf_median_baseline_mae": baseline_mae,
            "beats_per_tf_median_baseline": bool(mae < baseline_mae),
        }
path = RUN / "per_timeframe_diagnostics.json"
path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({
    "status": out["status"], "output": str(path),
    "classification": out["classification_by_timeframe"],
    "numeric_wins_by_tf": {
        tf: [name for name, m in v["targets"].items() if m["beats_per_tf_median_baseline"]]
        for tf, v in out["numeric_by_timeframe"].items()
    }
}, indent=2))
