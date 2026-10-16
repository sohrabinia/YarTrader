"""Nested chronological regularization tuning for the research-only fractal model."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN4 = ROOT / "runtime_logs" / "mt5_gold_history_full" / "fractal_range_training_20261010_v4"
RUN3 = ROOT / "runtime_logs" / "mt5_gold_history_full" / "fractal_range_training_20261010_v3"
report4 = json.loads((RUN4 / "evaluation_report.json").read_text(encoding="utf-8"))
meta4 = json.loads((RUN4 / "model_features.json").read_text(encoding="utf-8"))
meta3 = json.loads((RUN3 / "model_features.json").read_text(encoding="utf-8"))
num_meta = json.loads((RUN4 / "numeric_model_features.json").read_text(encoding="utf-8"))
samples = [json.loads(line) for line in (RUN4 / "dataset_samples.jsonl").open(encoding="utf-8") if line.strip()]
cutoff = int(report4["evaluation"]["metrics"]["test_time_range"][0])
feature_names = meta4["feature_names"]
old_feature_names = meta3["feature_names"]
targets = num_meta["target_names"]
train = [s for s in samples if int(s["time"]) < cutoff and int(s["label_end_time"]) <= cutoff]
test = [s for s in samples if int(s["time"]) >= cutoff]
train.sort(key=lambda s: (s["time"], s["timeframe"]))
test.sort(key=lambda s: (s["time"], s["timeframe"]))
train_times = sorted(set(int(s["time"]) for s in train))
inner_cutoff = train_times[int(0.80 * (len(train_times) - 1))]
inner_train = [s for s in train if int(s["time"]) < inner_cutoff and int(s["label_end_time"]) <= inner_cutoff]
validation = [s for s in train if int(s["time"]) >= inner_cutoff and int(s["time"]) < cutoff]

def matrix(rows, names):
    return np.asarray([[float(s["features"].get(k, 0.0)) for k in names] for s in rows], dtype=float)

def scores(y, pred, classes):
    recalls = [float(np.mean(pred[y == c] == c)) for c in classes if np.any(y == c)]
    return {"accuracy": float(np.mean(pred == y)), "balanced_accuracy": float(np.mean(recalls))}

def fit_logistic(rows, names, penalty, epochs=200):
    x = matrix(rows, names)
    y = np.asarray([int(s["label"]) for s in rows], dtype=int)
    classes = np.asarray(sorted(set(y)), dtype=int)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-9] = 1.0
    x = np.clip((x - mean) / scale, -10, 10)
    idx = {int(c): i for i, c in enumerate(classes)}
    yi = np.asarray([idx[int(v)] for v in y], dtype=int)
    onehot = np.eye(len(classes))[yi]
    w = np.zeros((x.shape[1], len(classes)))
    b = np.zeros(len(classes))
    for epoch in range(epochs):
        logits = np.clip(x @ w + b, -30, 30)
        logits -= logits.max(axis=1, keepdims=True)
        ex = np.exp(logits)
        probs = ex / ex.sum(axis=1, keepdims=True)
        err = (probs - onehot) / len(y)
        lr = 0.12 / (1.0 + epoch * 0.015)
        w -= lr * (x.T @ err + penalty * w)
        b -= lr * err.sum(axis=0)
    return {"weights": w, "bias": b, "mean": mean, "scale": scale, "classes": classes,
            "feature_names": list(names), "penalty": penalty}

def predict_logistic(model, rows, names):
    x = matrix(rows, names)
    x = np.clip((x - model["mean"]) / np.where(model["scale"] < 1e-9, 1.0, model["scale"]), -10, 10)
    logits = np.clip(x @ model["weights"] + model["bias"], -30, 30)
    logits -= logits.max(axis=1, keepdims=True)
    ex = np.exp(logits)
    probs = ex / ex.sum(axis=1, keepdims=True)
    pred = model["classes"][np.argmax(probs, axis=1)]
    y = np.asarray([int(s["label"]) for s in rows])
    result = scores(y, pred, model["classes"])
    class_index = {int(c): i for i, c in enumerate(model["classes"])}
    result["log_loss"] = float(-np.log(np.maximum(
        probs[np.arange(len(y)), [class_index[int(v)] for v in y]], 1e-12
    )).mean()) if all(int(v) in class_index for v in y) else None
    return result

# Direct ablation: score the old model on the exact v4 test samples, using its old feature subset.
old_npz = np.load(RUN3 / "fractal_range_model.npz")
old_model = {
    "weights": old_npz["weights"], "bias": old_npz["bias"], "mean": old_npz["mean"],
    "scale": old_npz["scale"], "classes": old_npz["classes"],
}
old_pred = predict_logistic(old_model, test, old_feature_names)
old_pred["model"] = "v3_existing_model_on_v4_test_rows"

penalties = (0.001, 0.005, 0.01, 0.03, 0.1)
classifier_validation = {}
for penalty in penalties:
    model = fit_logistic(inner_train, feature_names, penalty)
    classifier_validation[str(penalty)] = predict_logistic(model, validation, feature_names)
best_penalty = max(penalties, key=lambda p: (
    classifier_validation[str(p)]["balanced_accuracy"],
    -classifier_validation[str(p)]["log_loss"]
))
final_classifier = fit_logistic(train, feature_names, best_penalty)
classifier_test = predict_logistic(final_classifier, test, feature_names)
classifier_test["selected_penalty"] = best_penalty
classifier_test["inner_validation_results"] = classifier_validation
classifier_test["old_v3_model_same_test_rows"] = old_pred
np.savez_compressed(
    RUN4 / "fractal_range_model_tuned.npz",
    weights=final_classifier["weights"], bias=final_classifier["bias"],
    mean=final_classifier["mean"], scale=final_classifier["scale"],
    classes=final_classifier["classes"],
)
# Tune ridge penalty on a chronological inner validation slice for all numeric targets.
x_inner_train = matrix(inner_train, num_meta["feature_names"])
x_val = matrix(validation, num_meta["feature_names"])
x_train = matrix(train, num_meta["feature_names"])
x_test = matrix(test, num_meta["feature_names"])
def standardize(train_x, *others):
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1e-9] = 1.0
    normed = [np.clip((x - mean) / scale, -10, 10) for x in (train_x, *others)]
    return mean, scale, normed
_, _, (xin, xv) = standardize(x_inner_train, x_val)
din = np.column_stack([np.ones(len(xin)), xin])
dv = np.column_stack([np.ones(len(xv)), xv])
inner_y = {t: np.asarray([float(s[t]) for s in inner_train]) for t in targets}
val_y = {t: np.asarray([float(s[t]) for s in validation]) for t in targets}
ridge_penalties = (2.0, 10.0, 50.0, 100.0, 250.0, 500.0)
ridge_validation = {}
for alpha in ridge_penalties:
    penalty = np.eye(din.shape[1]) * alpha
    penalty[0, 0] = 0.0
    rel_maes = []
    per_target = {}
    for t in targets:
        coef = np.linalg.solve(din.T @ din + penalty, din.T @ inner_y[t])
        pred = dv @ coef
        mae = float(np.mean(np.abs(pred - val_y[t])))
        baseline = float(np.mean(np.abs(np.median(inner_y[t]) - val_y[t])))
        per_target[t] = {"mae": mae, "median_baseline_mae": baseline}
        rel_maes.append(mae / max(baseline, 1e-12))
    ridge_validation[str(alpha)] = {"mean_relative_mae": float(np.mean(rel_maes)), "targets": per_target}
best_alpha = min(ridge_penalties, key=lambda a: ridge_validation[str(a)]["mean_relative_mae"])
# Refit selected ridge models on the complete outer training split and evaluate untouched OOS rows.
_, _, (xt, xe) = standardize(x_train, x_test)
dt = np.column_stack([np.ones(len(xt)), xt])
de = np.column_stack([np.ones(len(xe)), xe])
penalty = np.eye(dt.shape[1]) * best_alpha
penalty[0, 0] = 0.0
numeric_test = {}
numeric_coefs = {}
for t in targets:
    yt = np.asarray([float(s[t]) for s in train])
    ye = np.asarray([float(s[t]) for s in test])
    coef = np.linalg.solve(dt.T @ dt + penalty, dt.T @ yt)
    pred = de @ coef
    baseline_value = float(np.median(yt))
    mae = float(np.mean(np.abs(pred - ye)))
    baseline_mae = float(np.mean(np.abs(baseline_value - ye)))
    numeric_test[t] = {
        "mae": mae, "rmse": float(np.sqrt(np.mean((pred - ye) ** 2))),
        "median_baseline_mae": baseline_mae, "beats_median_baseline": mae < baseline_mae,
    }
    numeric_coefs[t] = coef
np.savez_compressed(
    RUN4 / "fractal_range_numeric_model_tuned.npz",
    mean=x_train.mean(axis=0),
    scale=np.where(x_train.std(axis=0) < 1e-9, 1.0, x_train.std(axis=0)),
    **{f"coef_{name}": coef for name, coef in numeric_coefs.items()},
)
result = {
    "status": "NESTED_CHRONOLOGICAL_TUNING_EVALUATED",
    "outer_cutoff_epoch": cutoff,
    "inner_validation_cutoff_epoch": inner_cutoff,
    "samples": {"inner_train": len(inner_train), "validation": len(validation), "outer_train": len(train), "outer_test": len(test)},
    "classifier": {
        "selected_penalty": best_penalty,
        "inner_validation": classifier_validation,
        "outer_test": classifier_test,
        "outer_test_majority_baseline_accuracy": report4["evaluation"]["metrics"]["majority_baseline_accuracy"],
    },
    "numeric_regression": {
        "selected_ridge_alpha": best_alpha,
        "inner_validation": ridge_validation,
        "outer_test_targets": numeric_test,
        "targets_beating_median_baseline": [t for t, m in numeric_test.items() if m["beats_median_baseline"]],
    },
    "artifacts": ["fractal_range_model_tuned.npz", "fractal_range_numeric_model_tuned.npz"],
    "safety": "Research-only; no inference runtime or order execution integration.",
}
out_path = RUN4 / "regularization_tuning_report.json"
out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({
    "output": str(out_path),
    "selected_classifier_penalty": best_penalty,
    "classifier_test": classifier_test,
    "selected_ridge_alpha": best_alpha,
    "numeric_targets_beating_baseline": result["numeric_regression"]["targets_beating_median_baseline"],
    "numeric_test": numeric_test,
}, indent=2))
