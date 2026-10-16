"""Cross-timeframe, scale-normalized range behavior analysis.

This is an inference-time descriptive engine, not a trained price predictor.
It uses only supplied bars and does not claim that fractal similarity implies
future-price certainty. Outcome labels belong in a separate offline dataset.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence


class MultiscaleRangeBehaviorEngine:
    """Describe ranges comparably across all supplied timeframes at once."""

    TIMEFRAME_ORDER = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")

    def __init__(self, window: int = 32, min_bars: int = 8) -> None:
        if window < 4 or min_bars < 4 or min_bars > window:
            raise ValueError("Require window >= min_bars >= 4")
        self.window = int(window)
        self.min_bars = int(min_bars)

    @staticmethod
    def _number(bar: Any, *keys: str) -> Optional[float]:
        for key in keys:
            value = bar.get(key) if isinstance(bar, Mapping) else getattr(bar, key, None)
            if value is not None:
                try:
                    result = float(value)
                    if math.isfinite(result):
                        return result
                except (TypeError, ValueError):
                    pass
        return None

    def _clean_bars(self, bars: Sequence[Any]) -> List[Dict[str, float]]:
        clean: List[Dict[str, float]] = []
        for bar in bars:
            o = self._number(bar, "open", "Open", "open_price")
            h = self._number(bar, "high", "High")
            l = self._number(bar, "low", "Low")
            c = self._number(bar, "close", "Close", "close_price")
            if None in (o, h, l, c) or min(o, h, l, c) <= 0:
                continue
            if h < max(o, c, l) or l > min(o, c, h):
                continue
            clean.append({"open": o, "high": h, "low": l, "close": c})
        return clean

    def describe_timeframe(self, timeframe: str, bars: Sequence[Any]) -> Dict[str, Any]:
        clean = self._clean_bars(bars)
        if len(clean) < self.min_bars:
            return {"timeframe": timeframe.upper(), "status": "INSUFFICIENT_DATA",
                    "bars_used": len(clean), "evidence_state": "NO_EVIDENCE"}

        sample = clean[-self.window:]
        highs = [b["high"] for b in sample]
        lows = [b["low"] for b in sample]
        closes = [b["close"] for b in sample]
        opens = [b["open"] for b in sample]
        high, low = max(highs), min(lows)
        width = high - low
        if width <= 0 or not math.isfinite(width):
            return {"timeframe": timeframe.upper(), "status": "DEGENERATE_RANGE",
                    "bars_used": len(sample), "evidence_state": "NO_EVIDENCE"}

        # ATR-like scale is derived solely from this observed window.
        true_ranges = []
        prev_close = None
        for b in sample:
            tr = b["high"] - b["low"]
            if prev_close is not None:
                tr = max(tr, abs(b["high"] - prev_close), abs(b["low"] - prev_close))
            true_ranges.append(tr)
            prev_close = b["close"]
        atr = sum(true_ranges) / len(true_ranges)
        body_sizes = [abs(c-o) for o, c in zip(opens, closes)]
        upper_wicks = [b["high"] - max(b["open"], b["close"]) for b in sample]
        lower_wicks = [min(b["open"], b["close"]) - b["low"] for b in sample]
        returns = [(closes[i] - closes[i-1]) / max(atr, 1e-12) for i in range(1, len(closes))]
        up_steps = sum(1 for x in returns if x > 0)
        down_steps = sum(1 for x in returns if x < 0)
        path_steps = sum(abs(x) for x in returns)
        net_displacement = (closes[-1] - closes[0]) / max(width, 1e-12)
        position = (closes[-1] - low) / width
        edge_band = 0.2
        if position <= edge_band:
            zone = "LOWER"
        elif position >= 1.0 - edge_band:
            zone = "UPPER"
        else:
            zone = "MIDDLE"

        # Descriptive direction only: not a future outcome label or trade signal.
        if net_displacement > 0.15:
            observed_bias = "UP"
        elif net_displacement < -0.15:
            observed_bias = "DOWN"
        else:
            observed_bias = "SIDEWAYS"

        features = {
            "range_width_over_atr": width / max(atr, 1e-12),
            "close_position_0_1": max(0.0, min(1.0, position)),
            "net_displacement_over_range": net_displacement,
            "path_efficiency_0_1": min(1.0, abs(closes[-1] - closes[0]) / max(sum(abs(closes[i]-closes[i-1]) for i in range(1, len(closes))), 1e-12)),
            "mean_body_over_atr": (sum(body_sizes) / len(body_sizes)) / max(atr, 1e-12),
            "mean_upper_wick_over_atr": (sum(upper_wicks) / len(upper_wicks)) / max(atr, 1e-12),
            "mean_lower_wick_over_atr": (sum(lower_wicks) / len(lower_wicks)) / max(atr, 1e-12),
            "up_step_fraction": up_steps / max(1, len(returns)),
            "down_step_fraction": down_steps / max(1, len(returns)),
            "edge_zone": zone,
            "observed_bias": observed_bias,
        }
        return {
            "timeframe": timeframe.upper(), "status": "DESCRIBED",
            "evidence_state": "DESCRIPTIVE_ONLY", "bars_used": len(sample),
            "range_high": high, "range_low": low, "range_mid": low + width / 2,
            "atr_scale": atr, "features": features,
        }

    @staticmethod
    def _similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> Optional[float]:
        fa, fb = a.get("features"), b.get("features")
        if not isinstance(fa, Mapping) or not isinstance(fb, Mapping):
            return None
        keys = ("range_width_over_atr", "close_position_0_1",
                "net_displacement_over_range", "path_efficiency_0_1",
                "mean_body_over_atr", "mean_upper_wick_over_atr",
                "mean_lower_wick_over_atr", "up_step_fraction", "down_step_fraction")
        # Bounded per-feature differences keep unlike scales comparable.
        diffs = []
        for key in keys:
            x, y = float(fa[key]), float(fb[key])
            scale = max(1.0, abs(x), abs(y))
            diffs.append(min(1.0, abs(x-y) / scale))
        score = 1.0 - sum(diffs) / len(diffs)
        if fa.get("observed_bias") != fb.get("observed_bias"):
            score *= 0.75
        return round(max(0.0, min(1.0, score)), 4)

    def analyze(self, candles_by_timeframe: Mapping[str, Sequence[Any]]) -> Dict[str, Any]:
        """Analyze every supplied timeframe in one pooled pass, not only adjacent pairs."""
        reports: Dict[str, Dict[str, Any]] = {}
        for tf, bars in candles_by_timeframe.items():
            reports[str(tf).upper()] = self.describe_timeframe(str(tf), bars)
        valid = [r for r in reports.values() if r.get("status") == "DESCRIBED"]

        comparisons = []
        for i, left in enumerate(valid):
            for right in valid[i + 1:]:
                score = self._similarity(left, right)
                if score is not None:
                    comparisons.append({
                        "timeframes": [left["timeframe"], right["timeframe"]],
                        "similarity_score": score,
                        "bias_match": left["features"]["observed_bias"] == right["features"]["observed_bias"],
                    })

        # Whole-set summaries prevent the report being limited to adjacent TF pairs.
        groups: Dict[str, List[str]] = {"UP": [], "DOWN": [], "SIDEWAYS": []}
        for report in valid:
            groups[report["features"]["observed_bias"]].append(report["timeframe"])
        mean_similarity = (sum(x["similarity_score"] for x in comparisons) / len(comparisons)
                           if comparisons else None)
        return {
            "engine": "MultiscaleRangeBehaviorEngine",
            "algorithm_version": "1.0.0",
            "status": "ACTIVE" if valid else "INSUFFICIENT_DATA",
            "interpretation": "DESCRIPTIVE_SIMILARITY_NOT_A_VALIDATED_FORECAST",
            "timeframe_count": len(reports),
            "valid_timeframe_count": len(valid),
            "timeframe_reports": reports,
            "all_timeframe_comparisons": comparisons,
            "comparison_count": len(comparisons),
            "mean_pairwise_similarity": round(mean_similarity, 4) if mean_similarity is not None else None,
            "observed_behavior_groups": groups,
            "prediction_claim": False,
        }
