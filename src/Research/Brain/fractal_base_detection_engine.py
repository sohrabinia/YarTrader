"""
YarTrader Forensic Fractal Research — Gate 3 Multi-Scale Base Detection Engine
Ratio-agnostic, deterministic, versioned, and fully reproducible Base detection.
Detects candidate market Bases independently at every constructed scale without assuming fractality is true.
"""

import math
from typing import List, Dict, Any, Optional

class Gate3BaseDetectorEngine:
    """
    Ratio-Agnostic Gate 3 Base Detection Engine.
    Detects candidate market Bases independently at any scale level.
    """

    ALGORITHM_VERSION = "base_detector_v1.1.0"

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
        scale_label: str = "x1"
    ) -> List[Dict[str, Any]]:
        """
        Detects candidate Bases in a given bar series at a specific scale.
        """
        if not bars or len(bars) < self.min_duration_bars:
            return []

        atrs = self._calculate_atr(bars)
        bases = []
        n = len(bars)
        i = 0

        while i <= n - self.min_duration_bars:
            best_base = None
            for length in range(self.min_duration_bars, min(n - i + 1, 50)):
                window = bars[i : i + length]
                local_high = max(b["high"] for b in window)
                local_low = min(b["low"] for b in window)
                local_range = local_high - local_low
                local_mid = (local_high + local_low) / 2.0
                local_atr = atrs[i + length - 1] if (i + length - 1) < len(atrs) else 1.0

                if local_atr <= 0:
                    local_atr = 0.0001

                compression_ratio = local_range / local_atr

                if compression_ratio <= self.max_compression_threshold:
                    start_ts = window[0]["timestamp"]
                    end_ts = window[-1]["timestamp"]
                    closes = [b["close"] for b in window]
                    open_start = window[0]["open"]
                    close_end = window[-1]["close"]

                    return_pct = (close_end - open_start) / open_start if open_start > 0 else 0.0
                    normalized_range = local_range / local_mid if local_mid > 0 else 0.0

                    mean_close = sum(closes) / len(closes)
                    volatility = math.sqrt(sum((c - mean_close) ** 2 for c in closes) / len(closes)) if len(closes) > 1 else 0.0

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

                    # Lookahead for breakout & transition
                    breakout = False
                    failed_breakout = False
                    retest = False
                    exit_idx = None
                    return_to_base = False
                    expansion = 0.0

                    lookahead_start = i + length
                    for j in range(lookahead_start, min(n, lookahead_start + 20)):
                        ahead_bar = bars[j]
                        dist_from_mid = abs(ahead_bar["close"] - local_mid)
                        if local_range > 0:
                            exp_val = dist_from_mid / local_range
                            if exp_val > expansion:
                                expansion = exp_val

                        if ahead_bar["close"] > local_high or ahead_bar["close"] < local_low:
                            if not breakout:
                                breakout = True
                                exit_idx = j

                            if breakout and (abs(ahead_bar["low"] - local_high) <= local_range * 0.2 or abs(ahead_bar["high"] - local_low) <= local_range * 0.2):
                                retest = True

                        if breakout and (local_low <= ahead_bar["close"] <= local_high):
                            failed_breakout = True
                            return_to_base = True

                    # Detection Score (0.0 to 1.0)
                    tightness_score = max(0.0, 1.0 - (compression_ratio / self.max_compression_threshold))
                    duration_score = min(1.0, length / 20.0)
                    breakout_bonus = 0.2 if breakout else 0.0
                    detection_score = round(min(1.0, 0.5 * tightness_score + 0.3 * duration_score + breakout_bonus), 4)

                    base_record = {
                        "base_id": f"base_{scale_label}_{start_ts}_{length}",
                        "scale": scale_label,
                        "start_index": i,
                        "end_index": i + length - 1,
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "duration_bars": length,
                        "high": round(local_high, 5),
                        "low": round(local_low, 5),
                        "range": round(local_range, 5),
                        "normalized_range": round(normalized_range, 5),
                        "midpoint": round(local_mid, 5),
                        "return_pct": round(return_pct, 6),
                        "volatility": round(volatility, 5),
                        "compression_ratio": round(compression_ratio, 5),
                        "internal_movement_count": internal_movement_count,
                        "expansion_ratio": round(expansion, 5),
                        "breakout": breakout,
                        "failed_breakout": failed_breakout,
                        "retest": retest,
                        "exit_index": exit_idx,
                        "return_to_base": return_to_base,
                        "detection_score": detection_score,
                        "detector_version": self.ALGORITHM_VERSION,
                        "thresholds": {
                            "min_duration_bars": self.min_duration_bars,
                            "max_compression_threshold": self.max_compression_threshold,
                            "expansion_threshold": self.expansion_threshold
                        }
                    }
                    best_base = base_record

            if best_base:
                bases.append(best_base)
                i += best_base["duration_bars"]
            else:
                i += 1

        return bases

    def detect_multiscale_bases(
        self,
        scale_family_map: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Detects candidate Bases independently across all scale levels in a scale family map.
        """
        results_by_scale = {}
        total_bases = 0

        for scale_label, bar_series in scale_family_map.items():
            detected = self.detect_bases_at_scale(bar_series, scale_label=scale_label)
            results_by_scale[scale_label] = {
                "bar_count": len(bar_series),
                "base_count": len(detected),
                "bases": detected
            }
            total_bases += len(detected)

        verdict = "BASE_STRUCTURE_DETECTED" if total_bases >= 10 else ("WEAK_EVIDENCE" if total_bases > 0 else "NO_BASE_STRUCTURE_DETECTED")

        return {
            "gate": 3,
            "gate_name": "Multi-Scale Base Detection",
            "verdict": verdict,
            "total_bases_detected": total_bases,
            "results_by_scale": results_by_scale,
            "algorithm_version": self.ALGORITHM_VERSION,
            "ratio_agnostic": True,
            "DATA_CLASSIFICATION": "REAL_HISTORICAL"
        }
