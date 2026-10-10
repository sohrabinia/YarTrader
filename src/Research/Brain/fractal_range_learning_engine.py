"""Research-only pooled fractal range learning pipeline.

Builds causal, nested multi-timeframe range snapshots and future outcome labels.
Training labels are created offline; inference features only use bars available by
the snapshot timestamp. No order execution or profitability claims are made here.
"""
from __future__ import annotations

import math
from bisect import bisect_right
from typing import Any, Dict, List, Mapping, Sequence

TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
TF_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600,
    "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000,
}
# Split true data outages while allowing ordinary weekend closures on higher bars.
MAX_GAP_SECONDS = {
    # M1 remains strict; coarser bars allow normal daily closures, while H4/D1
    # allow a normal weekend. Longer outages still split samples.
    "M1": 90, "M5": 6 * 3600, "M15": 6 * 3600, "M30": 6 * 3600,
    "H1": 6 * 3600, "H4": 4 * 86400, "D1": 4 * 86400,
    "W1": 21 * 86400, "MN1": 62 * 86400,
}
BASE_FEATURES = (
    "range_atr", "close_position", "net_displacement", "path_efficiency",
    "body_atr", "upper_wick_atr", "lower_wick_atr", "up_fraction",
    "down_fraction", "reversal_fraction", "range_width_pct", "timeframe_seconds_log",
)
CROSS_TF_FEATURES = tuple(
    f"context_{tf}_{field}"
    for tf in TIMEFRAMES
    for field in (
        "position", "range_atr", "displacement", "present",
        "candidate_duration_norm", "candidate_width_atr", "candidate_score",
        "candidate_efficiency", "candidate_displacement", "candidate_position",
    )
)
FEATURES = BASE_FEATURES + CROSS_TF_FEATURES
RANGE_CANDIDATE_LENGTHS = (8, 24, 48, 96)


def _timestamp(bar: Mapping[str, Any]) -> int:
    value = bar.get("time", bar.get("timestamp", bar.get("time_unix")))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        from datetime import datetime, timezone
        try:
            return int(float(value))
        except ValueError:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
    raise ValueError("Missing/invalid candle timestamp")


def _completed_times(tf: str, rows: Sequence[Mapping[str, float]]) -> List[int]:
    """Return conservative candle-close timestamps; calendar months are variable length."""
    if tf == "MN1":
        return [
            int(rows[i + 1]["time"]) if i + 1 < len(rows)
            else int(row["time"]) + 31 * 86400
            for i, row in enumerate(rows)
        ]
    seconds = TF_SECONDS.get(tf, 3600)
    return [int(row["time"]) + seconds for row in rows]


def _clean(bars: Sequence[Mapping[str, Any]]) -> List[Dict[str, float]]:
    # Fast path for sorted, unique numeric MT5 exports. Copy only list pointers:
    # build_dataset trims incomplete tails, so it must not mutate the caller's list.
    if isinstance(bars, list):
        previous_time = None
        already_clean = True
        for bar in bars:
            if (
                not isinstance(bar, Mapping)
                or not all(k in bar for k in ("time", "open", "high", "low", "close"))
                or any(
                    isinstance(bar[k], bool) or not isinstance(bar[k], (int, float))
                    for k in ("time", "open", "high", "low", "close")
                )
            ):
                already_clean = False
                break
            try:
                t = _timestamp(bar)
                o, h, l, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
            except (TypeError, ValueError):
                already_clean = False
                break
            if (
                not all(math.isfinite(v) for v in (o, h, l, c))
                or min(o, h, l, c) <= 0
                or h < max(o, c, l)
                or l > min(o, c, h)
                or (previous_time is not None and t <= previous_time)
            ):
                already_clean = False
                break
            previous_time = t
        if already_clean:
            return list(bars)

    result: List[Dict[str, float]] = []
    for bar in bars:
        try:
            row = {
                "time": _timestamp(bar),
                "open": float(bar.get("open", bar.get("Open"))),
                "high": float(bar.get("high", bar.get("High"))),
                "low": float(bar.get("low", bar.get("Low"))),
                "close": float(bar.get("close", bar.get("Close"))),
            }
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(v) for v in row.values()):
            continue
        if min(row["open"], row["high"], row["low"], row["close"]) <= 0:
            continue
        if row["high"] < max(row["open"], row["close"], row["low"]):
            continue
        if row["low"] > min(row["open"], row["close"], row["high"]):
            continue
        result.append(row)
    result.sort(key=lambda x: x["time"])
    dedup = {}
    for row in result:
        dedup[row["time"]] = row
    return list(dedup.values())


def _snapshot(rows: Sequence[Mapping[str, float]], tf: str, window: int) -> Dict[str, float]:
    s = list(rows[-window:])
    hi = max(x["high"] for x in s)
    lo = min(x["low"] for x in s)
    width = hi - lo
    closes = [x["close"] for x in s]
    atrs = []
    for i, row in enumerate(s):
        tr = row["high"] - row["low"]
        if i and int(row["time"]) - int(s[i - 1]["time"]) <= 1.5 * TF_SECONDS.get(tf, 3600):
            tr = max(
                tr,
                abs(row["high"] - s[i - 1]["close"]),
                abs(row["low"] - s[i - 1]["close"]),
            )
        atrs.append(tr)
    atr = sum(atrs) / len(atrs)
    net = (closes[-1] - closes[0]) / max(width, 1e-12)
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    up = sum(closes[i] > closes[i - 1] for i in range(1, len(closes)))
    down = sum(closes[i] < closes[i - 1] for i in range(1, len(closes)))
    reversals = sum(
        (closes[i] - closes[i - 1]) * (closes[i - 1] - closes[i - 2]) < 0
        for i in range(2, len(closes))
    )
    return {
        "range_atr": width / max(atr, 1e-12),
        "close_position": (closes[-1] - lo) / max(width, 1e-12),
        "net_displacement": net,
        "path_efficiency": abs(closes[-1] - closes[0]) / max(path, 1e-12),
        "body_atr": sum(abs(x["close"] - x["open"]) for x in s) / len(s) / max(atr, 1e-12),
        "upper_wick_atr": sum(x["high"] - max(x["open"], x["close"]) for x in s) / len(s) / max(atr, 1e-12),
        "lower_wick_atr": sum(min(x["open"], x["close"]) - x["low"] for x in s) / len(s) / max(atr, 1e-12),
        "up_fraction": up / max(1, len(closes) - 1),
        "down_fraction": down / max(1, len(closes) - 1),
        "reversal_fraction": reversals / max(1, len(closes) - 2),
        "range_width_pct": width / max(closes[-1], 1e-12),
        "timeframe_seconds_log": math.log1p(TF_SECONDS.get(tf, 3600)),
    }


def _variable_range_features(rows: Sequence[Mapping[str, float]], tf: str) -> Dict[str, float]:
    """Rank variable-duration range hypotheses from past-only bars."""
    default = {
        "candidate_duration_norm": 0.0, "candidate_width_atr": 0.0,
        "candidate_score": 0.0, "candidate_efficiency": 0.0,
        "candidate_displacement": 0.0, "candidate_position": 0.0,
    }
    available = len(rows)
    lengths = sorted({min(available, n) for n in RANGE_CANDIDATE_LENGTHS if min(available, n) >= 8})
    ranked = []
    for length in lengths:
        snap = _snapshot(rows[-length:], tf, length)
        width_atr = max(0.0, snap["range_atr"])
        efficiency = min(1.0, max(0.0, snap["path_efficiency"]))
        duration_support = math.log1p(length) / math.log1p(96)
        score = (
            0.50 / (1.0 + width_atr)
            + 0.35 * (1.0 - efficiency)
            + 0.15 * duration_support
        )
        ranked.append((score, length, snap))
    if not ranked:
        return default
    score, length, snap = max(ranked, key=lambda item: (item[0], item[1]))
    return {
        "candidate_duration_norm": length / 96.0,
        "candidate_width_atr": snap["range_atr"],
        "candidate_score": score,
        "candidate_efficiency": snap["path_efficiency"],
        "candidate_displacement": snap["net_displacement"],
        "candidate_position": snap["close_position"],
    }


class FractalRangeLearningEngine:
    """Build a pooled cross-timeframe dataset and train/evaluate a classifier."""

    VERSION = "fractal_range_learning_v5_session_gap_aware_simple_modes"

    def __init__(
        self, window: int = 32, horizon: int = 12, min_bars: int = 16,
        move_threshold_atr: float = 1.0, max_samples_per_tf: int = 50000,
    ):
        if window < min_bars or min_bars < 8 or horizon < 1 or move_threshold_atr <= 0:
            raise ValueError("Invalid window, horizon, min_bars, or move threshold")
        self.window = int(window)
        self.horizon = int(horizon)
        self.min_bars = int(min_bars)
        self.move_threshold_atr = float(move_threshold_atr)
        self.max_samples_per_tf = int(max_samples_per_tf)

    def build_dataset(self, candles_by_timeframe: Mapping[str, Sequence[Mapping[str, Any]]]) -> Dict[str, Any]:
        clean = {str(tf).upper(): _clean(bars) for tf, bars in candles_by_timeframe.items()}
        latest_observed_open = max(
            (int(row["time"]) for rows in clean.values() for row in rows),
            default=0,
        )
        incomplete_tail_bars_dropped = {}
        for tf, rows in clean.items():
            close_times = _completed_times(tf, rows)
            dropped = 0
            while rows and close_times and close_times[-1] > latest_observed_open:
                rows.pop()
                close_times.pop()
                dropped += 1
            incomplete_tail_bars_dropped[tf] = dropped
        completed_times = {tf: _completed_times(tf, rows) for tf, rows in clean.items()}
        # Prefix counts and segment starts let us reject any sample whose feature
        # window or future label crosses a market/data gap, in O(1) per sample.
        gap_prefixes: Dict[str, List[int]] = {}
        segment_starts: Dict[str, List[int]] = {}
        for tf, rows in clean.items():
            prefix = [0] * len(rows)
            starts = [0] * len(rows)
            max_gap = MAX_GAP_SECONDS.get(tf, 2 * TF_SECONDS.get(tf, 3600))
            for index in range(1, len(rows)):
                is_gap = int(int(rows[index]["time"]) - int(rows[index - 1]["time"]) > max_gap)
                prefix[index] = prefix[index - 1] + is_gap
                starts[index] = index if is_gap else starts[index - 1]
            gap_prefixes[tf] = prefix
            segment_starts[tf] = starts
        samples = []
        skipped = {}
        ordered_tfs = [tf for tf in TIMEFRAMES if tf in clean]
        ordered_tfs += [tf for tf in clean if tf not in ordered_tfs]
        # Context features are reused across many lower-TF samples. Cache them by
        # the last fully closed bar index to keep full-history research practical.
        context_feature_cache: Dict[str, Dict[tuple[int, bool], Dict[str, float]]] = {
            context_tf: {} for context_tf in TIMEFRAMES
        }

        for tf in ordered_tfs:
            rows = clean[tf]
            if len(rows) < self.window + self.horizon:
                skipped[tf] = {"bars": len(rows), "reason": "INSUFFICIENT_HISTORY"}
                continue
            first_end = self.window - 1
            last_end = len(rows) - self.horizon - 1
            candidate_count = max(0, last_end - first_end + 1)
            sample_count = min(candidate_count, self.max_samples_per_tf)
            if sample_count <= 0:
                skipped[tf] = {"bars": len(rows), "reason": "INSUFFICIENT_FUTURE_BARS"}
                continue
            if sample_count == 1:
                sample_ends = [last_end]
            else:
                stride = (last_end - first_end) / (sample_count - 1)
                sample_ends = sorted({int(round(first_end + i * stride)) for i in range(sample_count)})

            for end in sample_ends:
                history_start = end - self.window + 1
                future_end = end + self.horizon
                if gap_prefixes[tf][future_end] - gap_prefixes[tf][history_start] > 0:
                    continue
                history = rows[history_start:end + 1]
                snap = _snapshot(history, tf, self.window)
                tr = []
                for j, x in enumerate(history):
                    v = x["high"] - x["low"]
                    if j and int(x["time"]) - int(history[j - 1]["time"]) <= 1.5 * TF_SECONDS.get(tf, 3600):
                        v = max(v, abs(x["high"] - history[j - 1]["close"]),
                                abs(x["low"] - history[j - 1]["close"]))
                    tr.append(v)
                atr = sum(tr) / len(tr)
                future = rows[end + 1:end + 1 + self.horizon]
                if len(future) < self.horizon or atr <= 0:
                    continue
                current = history[-1]["close"]
                future_up = max(x["high"] for x in future) - current
                future_down = current - min(x["low"] for x in future)
                up_barrier = self.move_threshold_atr * atr
                down_barrier = self.move_threshold_atr * atr
                up_hit = future_up >= up_barrier
                down_hit = future_down >= down_barrier
                up_hit_index = next((j for j, x in enumerate(future, 1)
                                     if x["high"] - current >= up_barrier), None)
                down_hit_index = next((j for j, x in enumerate(future, 1)
                                       if current - x["low"] >= down_barrier), None)
                up_target_index = max(range(len(future)), key=lambda j: future[j]["high"])
                down_target_index = min(range(len(future)), key=lambda j: future[j]["low"])
                up_start_index = min(range(up_target_index + 1), key=lambda j: future[j]["low"])
                down_start_index = max(range(down_target_index + 1), key=lambda j: future[j]["high"])
                up_start_price = future[up_start_index]["low"]
                down_start_price = future[down_start_index]["high"]
                up_target_price = future[up_target_index]["high"]
                down_target_price = future[down_target_index]["low"]
                label = 1 if up_hit == down_hit else (2 if up_hit else 0)
                decision_ts = completed_times[tf][end]

                for context_tf in TIMEFRAMES:
                    prefix = f"context_{context_tf}_"
                    pos = end if context_tf == tf else (
                        bisect_right(completed_times.get(context_tf, []), decision_ts) - 1
                    )
                    cache = context_feature_cache.setdefault(context_tf, {})
                    context_rows = clean.get(context_tf, [])
                    context_is_fresh = (
                        bool(context_rows) and 0 <= pos < len(context_rows)
                        and decision_ts - completed_times[context_tf][pos]
                        <= max(2 * TF_SECONDS.get(context_tf, 3600), MAX_GAP_SECONDS.get(context_tf, 2 * TF_SECONDS.get(context_tf, 3600)))
                    )
                    cache_key = (pos, bool(context_is_fresh))
                    context_features = cache.get(cache_key)
                    if context_features is None:
                        context_features = {
                            "position": 0.5, "range_atr": 0.0, "displacement": 0.0, "present": 0.0,
                            **_variable_range_features([], context_tf),
                        }
                        if context_is_fresh:
                            context_start = segment_starts[context_tf][pos]
                            available_in_segment = pos - context_start + 1
                        else:
                            context_start = 0
                            available_in_segment = 0
                        if context_is_fresh and available_in_segment >= self.min_bars:
                            other = context_rows[max(context_start, pos - self.window + 1):pos + 1]
                            range_rows = context_rows[max(context_start, pos - 95):pos + 1]
                            osnap = _snapshot(other, context_tf, self.window)
                            context_features.update({
                                "position": osnap["close_position"],
                                "range_atr": osnap["range_atr"],
                                "displacement": osnap["net_displacement"],
                                "present": 1.0,
                            })
                            context_features.update(_variable_range_features(range_rows, context_tf))
                        cache[cache_key] = context_features
                    for field, value in context_features.items():
                        snap[prefix + field] = value

                samples.append({
                    "time": decision_ts,
                    "label_end_time": completed_times[tf][end + self.horizon],
                    "timeframe": tf,
                    "features": snap,
                    "label": label,
                    "label_name": {0: "DOWN", 1: "AMBIGUOUS_OR_RANGE", 2: "UP"}[label],
                    "current_close": current,
                    "atr": atr,
                    "future_up_atr": future_up / atr,
                    "future_down_atr": future_down / atr,
                    "target_up_price": current + up_barrier,
                    "target_down_price": current - down_barrier,
                    "bars_to_up_barrier": up_hit_index if up_hit_index is not None else self.horizon + 1,
                    "bars_to_down_barrier": down_hit_index if down_hit_index is not None else self.horizon + 1,
                    "swing_start_up_price": up_start_price,
                    "swing_start_down_price": down_start_price,
                    "swing_target_up_price": up_target_price,
                    "swing_target_down_price": down_target_price,
                    "swing_start_up_offset_atr": (up_start_price - current) / atr,
                    "swing_start_down_offset_atr": (down_start_price - current) / atr,
                    "swing_target_up_atr": (up_target_price - current) / atr,
                    "swing_target_down_atr": (current - down_target_price) / atr,
                    "bars_to_swing_start_up": up_start_index + 1,
                    "bars_to_swing_start_down": down_start_index + 1,
                    "bars_to_swing_target_up": up_target_index + 1,
                    "bars_to_swing_target_down": down_target_index + 1,
                })

        samples.sort(key=lambda x: x["time"])
        return {
            "version": self.VERSION,
            "samples": samples,
            "sample_count": len(samples),
            "timeframes": ordered_tfs,
            "bars_by_timeframe": {k: len(v) for k, v in clean.items()},
            "incomplete_tail_bars_dropped": incomplete_tail_bars_dropped,
            "skipped_timeframes": skipped,
            "feature_names": list(FEATURES),
            "range_candidate_lengths": list(RANGE_CANDIDATE_LENGTHS),
            "label_definition": {
                "0": "DOWN barrier hit and UP barrier not hit",
                "1": "both barriers hit or neither hit within horizon",
                "2": "UP barrier hit and DOWN barrier not hit",
                "horizon_bars": self.horizon,
                "threshold_atr": self.move_threshold_atr,
            },
            "leakage_guard": "features use bars <= decision time; future bars only define offline labels",
            "gap_policy_seconds": {tf: MAX_GAP_SECONDS.get(tf, 2 * TF_SECONDS.get(tf, 3600)) for tf in clean},
            "gap_policy": "samples are rejected if a gap crosses the feature window or label horizon; context features restart at the latest contiguous segment",
        }

    def train_evaluate(
        self, dataset: Mapping[str, Any], train_fraction: float = 0.70,
        train_until: int | None = None, test_until: int | None = None,
        feature_mode: str = "full",
    ) -> Dict[str, Any]:
        samples = list(dataset.get("samples", []))
        if not 0.5 <= train_fraction <= 0.9:
            raise ValueError("train_fraction must be between 0.5 and 0.9")
        ordered_times = sorted(int(s["time"]) for s in samples)
        if not ordered_times:
            return {"status": "INSUFFICIENT_DATA", "train_samples": 0, "test_samples": 0,
                    "model_trained": False, "reason": "No samples available."}
        cutoff = int(train_until) if train_until is not None else ordered_times[
            min(len(ordered_times) - 1, int(len(ordered_times) * train_fraction))
        ]
        train = [
            s for s in samples
            if int(s["time"]) < cutoff
            and int(s.get("label_end_time", int(s["time"]) + self.horizon * TF_SECONDS.get(s["timeframe"], 3600))) <= cutoff
        ]
        test = [
            s for s in samples
            if int(s["time"]) >= cutoff
            and (test_until is None or int(s["time"]) < int(test_until))
        ]
        train.sort(key=lambda item: (item["time"], item["timeframe"]))
        test.sort(key=lambda item: (item["time"], item["timeframe"]))
        if len(train) < 60 or len(test) < 30 or len({x["label"] for x in train}) < 2:
            return {
                "status": "INSUFFICIENT_DATA", "train_samples": len(train), "test_samples": len(test),
                "model_trained": False,
                "reason": "Need more chronological samples and at least two training classes.",
            }
        try:
            import numpy as np
        except ImportError:
            return {
                "status": "DEPENDENCY_UNAVAILABLE", "model_trained": False,
                "reason": "NumPy is required for model training.",
            }

        all_feature_names = list(dataset.get("feature_names", list(FEATURES)))
        # Keep the existing full model as the default, but make simple, interpretable
        # hypotheses directly comparable on exactly the same chronological samples.
        if feature_mode == "full":
            feature_names = all_feature_names
        elif feature_mode == "simple":
            requested = (
                "range_atr", "close_position", "net_displacement", "path_efficiency",
                "timeframe_seconds_log", "context_M15_position", "context_M15_range_atr",
                "context_H1_position", "context_H1_range_atr", "context_H4_position",
                "context_H4_range_atr", "context_D1_position", "context_D1_range_atr",
            )
            feature_names = [name for name in requested if name in all_feature_names]
        elif feature_mode == "range_only":
            requested = ("range_atr", "close_position", "net_displacement", "path_efficiency")
            feature_names = [name for name in requested if name in all_feature_names]
        else:
            raise ValueError("feature_mode must be 'full', 'simple', or 'range_only'")
        if not feature_names:
            return {"status": "INSUFFICIENT_DATA", "train_samples": len(train), "test_samples": len(test),
                    "model_trained": False, "reason": "Selected feature mode has no features in this dataset."}
        x_train = np.asarray([[float(s["features"].get(k, 0.0)) for k in feature_names] for s in train], dtype=float)
        y_train = np.asarray([int(s["label"]) for s in train], dtype=int)
        x_test = np.asarray([[float(s["features"].get(k, 0.0)) for k in feature_names] for s in test], dtype=float)
        y_test = np.asarray([int(s["label"]) for s in test], dtype=int)
        classes = np.asarray(sorted(set(y_train)), dtype=int)
        if len(classes) < 2:
            return {
                "status": "INSUFFICIENT_DATA", "train_samples": len(train), "test_samples": len(test),
                "model_trained": False, "reason": "Training split contains fewer than two classes.",
            }
        mean = x_train.mean(axis=0)
        scale = x_train.std(axis=0)
        scale[scale < 1e-9] = 1.0
        x_train = np.clip((x_train - mean) / scale, -10, 10)
        x_test = np.clip((x_test - mean) / scale, -10, 10)
        class_index = {int(c): i for i, c in enumerate(classes)}
        y_index = np.asarray([class_index[int(v)] for v in y_train], dtype=int)
        onehot = np.eye(len(classes))[y_index]
        weights = np.zeros((x_train.shape[1], len(classes)), dtype=float)
        bias = np.zeros(len(classes), dtype=float)
        for epoch in range(250):
            logits = np.clip(x_train @ weights + bias, -30, 30)
            logits -= logits.max(axis=1, keepdims=True)
            exp = np.exp(logits)
            probabilities = exp / exp.sum(axis=1, keepdims=True)
            error = (probabilities - onehot) / len(y_train)
            learning_rate = 0.12 / (1.0 + epoch * 0.015)
            weights -= learning_rate * (x_train.T @ error + 0.01 * weights)
            bias -= learning_rate * error.sum(axis=0)
        logits = np.clip(x_test @ weights + bias, -30, 30)
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        probs = exp / exp.sum(axis=1, keepdims=True)
        pred = classes[np.argmax(probs, axis=1)]
        accuracy = float(np.mean(pred == y_test))
        recalls = []
        matrix = []
        for actual in classes:
            row = []
            mask = y_test == actual
            for guessed in classes:
                row.append(int(np.sum((y_test == actual) & (pred == guessed))))
            matrix.append(row)
            if np.any(mask):
                recalls.append(float(np.mean(pred[mask] == actual)))
        counts = {int(c): int(np.sum(y_train == c)) for c in classes}
        majority = max(counts, key=counts.get)
        # Explicitly flag test classes missing from training instead of silently mapping
        # them to class index zero in the log-loss calculation.
        if all(int(v) in class_index for v in y_test):
            log_loss = float(-np.log(np.maximum(
                probs[np.arange(len(y_test)), [class_index[int(v)] for v in y_test]], 1e-12
            )).mean())
        else:
            log_loss = None
        majority_accuracy = float(np.mean(y_test == majority))
        metrics = {
            "accuracy": accuracy,
            "balanced_accuracy": float(np.mean(recalls)),
            "confusion_matrix": matrix,
            "classes": [int(c) for c in classes],
            "test_class_counts": {str(int(c)): int(np.sum(y_test == c)) for c in sorted(set(y_test.tolist()))},
            "train_time_range": [train[0]["time"], train[-1]["time"]],
            "test_time_range": [test[0]["time"], test[-1]["time"]],
            "log_loss": log_loss,
            "majority_baseline_accuracy": majority_accuracy,
            "beats_majority_baseline": accuracy > majority_accuracy,
        }
        model = {
            "weights": weights, "bias": bias, "mean": mean, "scale": scale,
            "classes": classes, "feature_names": list(feature_names),
        }
        return {
            "status": "EVALUATED_OOS",
            "model_trained": True,
            "model_type": "RegularizedMultinomialLogisticRegression_NumPy",
            "feature_mode": feature_mode,
            "feature_count": len(feature_names),
            "train_samples": len(train),
            "test_samples": len(test),
            "metrics": metrics,
            "prediction_semantics": "Research probabilities only; not a trading signal or execution authorization.",
            "model": model,
        }
