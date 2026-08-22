"""
YarTrader Forensic Fractal Research — Gate 3 Multi-Scale Base Detection Engine
Ratio-agnostic, deterministic, versioned, and fully reproducible Base detection.
Detects candidate market Bases independently at every constructed scale without look-ahead bias,
without assuming fractality is true, and strictly excluding partial trailing groups.
"""

import math
from typing import List, Dict, Any, Optional

class Gate3BaseDetectorEngine:
    """
    Ratio-Agnostic Gate 3 Base Detection Engine.
    Detects candidate market Bases independently at any scale level.
    Strictly excludes look-ahead information from Base detection and scoring.
    """

    ALGORITHM_VERSION = "base_detector_v1.2.0"

    def __init__(
        self,
        min_duration_bars: int = 4,
        max_compression_threshold: float = 1.2,
        expansion_threshold: float = 1.5
    ):
        self.min_duration_bars = min_duration_bars
        self.max_compression_threshold = max_compression_threshold
        self.expansion_threshold = expansion_threshold

    @staticmethod
    def _calculate_atr(bars: List[Dict[str, Any]], period: int = 14) -> List[float]:
        if not bars:
            return []
        atrs = []
        tr_list = []
        for i, bar in enumerate(bars):
            if i == 0:
                tr = bar["high"] - bar["low"]
            else:
                prev_close = bars[i - 1]["close"]
                tr = max(
                    bar["high"] - bar["low"],
                    abs(bar["high"] - prev_close),
                    abs(bar["low"] - prev_close)
                )
            tr_list.append(tr)
            if len(tr_list) < period:
                atrs.append(sum(tr_list) / len(tr_list))
            else:
                atrs.append(sum(tr_list[-period:]) / period)
        return atrs

    def detect_bases_at_scale(
        self,
        bars: List[Dict[str, Any]],
        scale_label: str = "x1",
        family: str = "x4"
    ) -> Dict[str, Any]:
        """
        Detects candidate Bases in a given bar series at a specific scale.
        Strictly excludes partial trailing groups and uses 100% intra-base backward-looking metrics only.
        Memory-optimized to handle large datasets (100,000+ bars).
        """
        # Filter out partial trailing groups
        valid_bars = [b for b in bars if not b.get("is_partial_trailing_group", False)]
        excluded_partial_count = len(bars) - len(valid_bars)

        if not valid_bars or len(valid_bars) < self.min_duration_bars:
            return {
                "scale": scale_label,
                "family": family,
                "valid_bar_count": len(valid_bars),
                "partial_groups_excluded": excluded_partial_count,
                "accepted_bases": [],
                "rejected_count": 0,
                "rejected_candidates": []
            }

        atrs = self._calculate_atr(valid_bars)
        accepted_bases = []
        rejected_count = 0
        sample_rejected = []
        n = len(valid_bars)
        i = 0

        while i <= n - self.min_duration_bars:
            best_candidate = None

            for length in range(self.min_duration_bars, min(n - i + 1, 50)):
                window = valid_bars[i : i + length]
                local_high = max(b["high"] for b in window)
                local_low = min(b["low"] for b in window)
                local_range = local_high - local_low
                local_mid = (local_high + local_low) / 2.0
                local_atr = atrs[i + length - 1] if (i + length - 1) < len(atrs) else 1.0

                if local_atr <= 0:
                    local_atr = 0.0001

                compression_ratio = local_range / local_atr
                start_ts = window[0].get("timestamp") or window[0].get("start_timestamp")
                end_ts = window[-1].get("timestamp") or window[-1].get("end_timestamp")
                closes = [b["close"] for b in window]
                open_start = window[0]["open"]
                close_end = window[-1]["close"]

                return_pct = (close_end - open_start) / open_start if open_start > 0 else 0.0
                normalized_range = local_range / local_mid if local_mid > 0 else 0.0

                mean_close = sum(closes) / len(closes)
                std_close = math.sqrt(sum((c - mean_close) ** 2 for c in closes) / len(closes)) if len(closes) > 1 else 0.0

                # Count internal swing reversals
                internal_movement_count = 0
                direction = 0
                for k in range(1, len(closes)):
                    diff = closes[k] - closes[k - 1]
                    if diff > 0 and direction <= 0:
                        internal_movement_count += 1
                        direction = 1
                    elif diff < 0 and direction >= 0:
                        internal_movement_count += 1
                        direction = -1

                # INTRA-BASE STRICTLY BACKWARD-LOOKING DETECTION SCORE & CONFIDENCE (NO LOOKAHEAD)
                tightness_score = max(0.0, 1.0 - (compression_ratio / self.max_compression_threshold))
                duration_score = min(1.0, length / 20.0)
                detection_score = round(min(1.0, 0.6 * tightness_score + 0.4 * duration_score), 4)
                confidence = round(min(1.0, 0.5 * detection_score + 0.5 * (1.0 - min(1.0, std_close / (local_range or 1.0)))), 4)

                is_accepted = compression_ratio <= self.max_compression_threshold

                candidate_record = {
                    "base_id": f"base_{scale_label}_{start_ts}_{length}",
                    "scale": scale_label,
                    "family": family,
                    "start_index": i,
                    "end_index": i + length - 1,
                    "start_timestamp": start_ts,
                    "end_timestamp": end_ts,
                    "duration": length,
                    "high": round(local_high, 5),
                    "low": round(local_low, 5),
                    "open": round(open_start, 5),
                    "close": round(close_end, 5),
                    "range": round(local_range, 5),
                    "normalized_range": round(normalized_range, 5),
                    "midpoint": round(local_mid, 5),
                    "return_pct": round(return_pct, 6),
                    "volatility": round(std_close, 5),
                    "compression_ratio": round(compression_ratio, 5),
                    "internal_structure_statistics": {
                        "internal_movement_count": internal_movement_count,
                        "mean_close": round(mean_close, 5),
                        "std_close": round(std_close, 5)
                    },
                    "parent_child_eligibility": {
                        "eligible_parent": length >= 8,
                        "eligible_child": True,
                        "scale_family": family
                    },
                    "detection_score": detection_score,
                    "confidence": confidence,
                    "status": "ACCEPTED_BASE" if is_accepted else "REJECTED_CANDIDATE",
                    "detection_criteria": {
                        "min_duration_bars": self.min_duration_bars,
                        "max_compression_threshold": self.max_compression_threshold,
                        "expansion_threshold": self.expansion_threshold,
                        "detector_version": self.ALGORITHM_VERSION
                    }
                }

                if is_accepted:
                    if best_candidate is None or candidate_record["detection_score"] > best_candidate["detection_score"]:
                        best_candidate = candidate_record
                else:
                    rejected_count += 1
                    if len(sample_rejected) < 10:
                        sample_rejected.append(candidate_record)

            if best_candidate:
                accepted_bases.append(best_candidate)
                i += best_candidate["duration"]
            else:
                i += 1

        return {
            "scale": scale_label,
            "family": family,
            "valid_bar_count": len(valid_bars),
            "partial_groups_excluded": excluded_partial_count,
            "accepted_bases": accepted_bases,
            "rejected_count": rejected_count,
            "rejected_candidates": sample_rejected
        }

    def detect_multiscale_bases(
        self,
        scale_family_map: Dict[str, List[Dict[str, Any]]],
        family: str = "x4"
    ) -> Dict[str, Any]:
        """
        Detects candidate Bases independently across all scale levels in a scale family.
        """
        results_by_scale = {}
        total_accepted = 0
        total_rejected = 0
        total_partials_excluded = 0

        for scale_key, bar_series in scale_family_map.items():
            label = f"x{scale_key}" if isinstance(scale_key, int) or (isinstance(scale_key, str) and scale_key.isdigit()) else str(scale_key)
            res = self.detect_bases_at_scale(bar_series, scale_label=label, family=family)
            results_by_scale[label] = res
            total_accepted += len(res["accepted_bases"])
            total_rejected += res["rejected_count"]
            total_partials_excluded += res["partial_groups_excluded"]

        return {
            "family": family,
            "total_accepted_bases": total_accepted,
            "total_rejected_candidates": total_rejected,
            "total_partial_groups_excluded": total_partials_excluded,
            "results_by_scale": results_by_scale,
            "algorithm_version": self.ALGORITHM_VERSION
        }
