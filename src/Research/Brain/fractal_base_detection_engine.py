"""
YarTrader — Gate 3 Multi-Scale Base Detection Engine
=====================================================

Causal, deterministic, fail-closed base detection for research/backtesting.

Design rules
------------
* Online detection uses ONLY bars supplied to this call. It never inspects
  future bars relative to a candidate base.
* Future-dependent outcomes (breakout/retest/failed-breakout/return-to-base/
  post-base expansion) are available only through the explicit offline-label
  API and must never be consumed by online inference.
* Missing or invalid market data is rejected; no price/time/ATR fabrication.
* Incomplete/partial scale bars are excluded from online structural detection.
* Returned numeric features are finite and derived only from observed input.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Gate3BaseDetectorEngine:
    """
    Causal Gate 3 base detector.

    `detect_bases_at_scale()` is the ONLINE / inference-safe API.
    `label_bases_at_scale_offline()` is the explicit OFFLINE outcome-label API.

    The public result schema is intentionally dictionary-based to preserve
    compatibility with existing YarTrader callers.
    """

    ALGORITHM_VERSION = "base_detector_v1.0.0"

    _REQUIRED_FIELDS = ("open", "high", "low", "close", "timestamp")

    def __init__(
        self,
        min_duration_bars: int = 4,
        max_compression_threshold: float = 1.2,
        expansion_threshold: float = 1.5,
        atr_period: int = 14,
        max_base_duration_bars: int = 50,
        offline_lookahead_bars: int = 20,
    ) -> None:
        self.min_duration_bars = self._require_int(
            min_duration_bars, "min_duration_bars", minimum=2
        )
        self.max_compression_threshold = self._require_positive_float(
            max_compression_threshold, "max_compression_threshold"
        )
        self.expansion_threshold = self._require_positive_float(
            expansion_threshold, "expansion_threshold"
        )
        self.atr_period = self._require_int(
            atr_period, "atr_period", minimum=1
        )
        self.max_base_duration_bars = self._require_int(
            max_base_duration_bars, "max_base_duration_bars", minimum=self.min_duration_bars
        )
        self.offline_lookahead_bars = self._require_int(
            offline_lookahead_bars, "offline_lookahead_bars", minimum=1
        )

    @staticmethod
    def _require_int(value: Any, name: str, minimum: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer, not bool")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if parsed < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return parsed

    @staticmethod
    def _require_positive_float(value: Any, name: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be numeric, not bool")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric") from exc
        if not math.isfinite(parsed) or parsed <= 0.0:
            raise ValueError(f"{name} must be finite and > 0")
        return parsed

    @staticmethod
    def _timestamp_is_valid(value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return math.isfinite(float(value))
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return False
            try:
                numeric = float(text)
                return math.isfinite(numeric)
            except ValueError:
                pass
            try:
                datetime.fromisoformat(text.replace("Z", "+00:00"))
                return True
            except ValueError:
                return False
        return False

    @classmethod
    def _normalize_bars(
        cls,
        bars: List[Dict[str, Any]],
        *,
        reject_partial: bool = True,
    ) -> List[Dict[str, Any]]:
        if not isinstance(bars, list):
            raise ValueError("bars must be a list")

        normalized: List[Dict[str, Any]] = []

        for index, raw in enumerate(bars):
            if not isinstance(raw, dict):
                raise ValueError(f"bar[{index}] must be a dictionary")

            if reject_partial and bool(raw.get("is_partial", False)):
                continue
            if reject_partial and bool(raw.get("partial", False)):
                continue
            if reject_partial and raw.get("complete") is False:
                continue

            raw_dict = dict(raw)
            if "timestamp" not in raw_dict or raw_dict["timestamp"] is None:
                if "start_timestamp" in raw_dict and raw_dict["start_timestamp"] is not None:
                    raw_dict["timestamp"] = raw_dict["start_timestamp"]
                elif "time" in raw_dict and raw_dict["time"] is not None:
                    raw_dict["timestamp"] = raw_dict["time"]

            for field in cls._REQUIRED_FIELDS:
                if field not in raw_dict or raw_dict[field] is None:
                    raise ValueError(
                        f"bar[{index}] missing required field: {field}"
                    )

            if not cls._timestamp_is_valid(raw_dict["timestamp"]):
                raise ValueError(f"bar[{index}] has invalid timestamp")

            values: Dict[str, float] = {}
            for field in ("open", "high", "low", "close"):
                value = raw_dict[field]
                if isinstance(value, bool):
                    raise ValueError(f"bar[{index}].field must be numeric")
                try:
                    parsed = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"bar[{index}].{field} is not numeric"
                    ) from exc
                if not math.isfinite(parsed):
                    raise ValueError(f"bar[{index}].{field} is not finite")
                values[field] = parsed

            if values["high"] < max(values["open"], values["close"]):
                raise ValueError(f"bar[{index}] high is below open/close")
            if values["low"] > min(values["open"], values["close"]):
                raise ValueError(f"bar[{index}] low is above open/close")
            if values["high"] < values["low"]:
                raise ValueError(f"bar[{index}] high is below low")

            result = dict(raw_dict)
            result.update(values)

            if "volume" in raw_dict and raw_dict["volume"] is not None:
                if isinstance(raw_dict["volume"], bool):
                    raise ValueError(f"bar[{index}].volume must be numeric")
                try:
                    volume = float(raw_dict["volume"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"bar[{index}].volume is not numeric"
                    ) from exc
                if not math.isfinite(volume) or volume < 0.0:
                    raise ValueError(f"bar[{index}].volume is invalid")
                result["volume"] = volume

            normalized.append(result)

        # Deterministic ordering is required for causal rolling computations.
        for i in range(1, len(normalized)):
            prev = normalized[i - 1]["timestamp"]
            curr = normalized[i]["timestamp"]
            if isinstance(prev, datetime) and isinstance(curr, datetime):
                prev_dt = prev
                curr_dt = curr
            else:
                prev_dt = cls._parse_timestamp(prev)
                curr_dt = cls._parse_timestamp(curr)
            if curr_dt <= prev_dt:
                raise ValueError("bars must be strictly increasing by timestamp")

        return normalized

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        text = str(value).strip()
        try:
            numeric = float(text)
        except ValueError:
            numeric = None

        if numeric is not None:
            if not math.isfinite(numeric):
                raise ValueError("invalid numeric timestamp")
            return datetime.fromtimestamp(numeric, tz=timezone.utc)

        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _calculate_atr(
        bars: List[Dict[str, Any]],
        period: int = 14,
    ) -> List[Optional[float]]:
        """
        Causal rolling ATR.

        For each bar i, ATR uses only bars <= i.
        `None` is returned until at least one valid true range exists; no
        arbitrary ATR fallback is used.
        """
        if not bars:
            return []

        period = max(1, int(period))
        true_ranges: List[float] = []
        atrs: List[Optional[float]] = []

        for i, bar in enumerate(bars):
            if i == 0:
                tr = bar["high"] - bar["low"]
            else:
                prev_close = bars[i - 1]["close"]
                tr = max(
                    bar["high"] - bar["low"],
                    abs(bar["high"] - prev_close),
                    abs(bar["low"] - prev_close),
                )

            if not math.isfinite(tr) or tr < 0.0:
                atrs.append(None)
                true_ranges.append(float("nan"))
                continue

            true_ranges.append(tr)
            valid_window = [
                x for x in true_ranges[max(0, len(true_ranges) - period):]
                if math.isfinite(x)
            ]
            atr = sum(valid_window) / len(valid_window) if valid_window else None
            atrs.append(atr if atr is not None and math.isfinite(atr) and atr > 0.0 else None)

        return atrs

    @staticmethod
    def _internal_movement_count(closes: List[float]) -> int:
        count = 0
        direction = 0
        for idx in range(1, len(closes)):
            diff = closes[idx] - closes[idx - 1]
            if diff > 0.0 and direction <= 0:
                count += 1
                direction = 1
            elif diff < 0.0 and direction >= 0:
                count += 1
                direction = -1
        return count

    def _candidate_from_window(
        self,
        window: List[Dict[str, Any]],
        *,
        scale_label: str,
        start_index: int,
        local_atr: float,
    ) -> Dict[str, Any]:
        local_high = max(b["high"] for b in window)
        local_low = min(b["low"] for b in window)
        local_range = local_high - local_low

        if not math.isfinite(local_range) or local_range < 0.0:
            raise ValueError("invalid local range")

        if local_atr <= 0.0 or not math.isfinite(local_atr):
            raise ValueError("invalid ATR")

        local_mid = (local_high + local_low) / 2.0
        if not math.isfinite(local_mid) or local_mid <= 0.0:
            raise ValueError("invalid positive-price midpoint")

        compression_ratio = local_range / local_atr
        if not math.isfinite(compression_ratio):
            raise ValueError("invalid compression ratio")

        if compression_ratio > self.max_compression_threshold:
            raise ValueError("window is not compressed enough")

        closes = [b["close"] for b in window]
        open_start = window[0]["open"]
        close_end = window[-1]["close"]

        if open_start <= 0.0 or not math.isfinite(open_start):
            raise ValueError("invalid positive opening price")

        mean_close = sum(closes) / len(closes)
        variance = sum((c - mean_close) ** 2 for c in closes) / len(closes)
        volatility = math.sqrt(max(0.0, variance))

        normalized_range = local_range / local_mid
        return_pct = (close_end - open_start) / open_start

        tightness_score = max(
            0.0,
            1.0 - (compression_ratio / self.max_compression_threshold),
        )
        duration_score = min(1.0, len(window) / 20.0)

        detection_score = round(
            min(
                1.0,
                0.7 * tightness_score + 0.3 * duration_score,
            ),
            4,
        )

        return {
            "base_id": f"base_{scale_label}_{window[0]['timestamp']}_{len(window)}",
            "scale": scale_label,
            "start_index": start_index,
            "end_index": start_index + len(window) - 1,
            "start_timestamp": window[0]["timestamp"],
            "end_timestamp": window[-1]["timestamp"],
            "duration_bars": len(window),
            "high": round(local_high, 5),
            "low": round(local_low, 5),
            "range": round(local_range, 5),
            "normalized_range": round(normalized_range, 5),
            "midpoint": round(local_mid, 5),
            "return_pct": round(return_pct, 6),
            "volatility": round(volatility, 5),
            "compression_ratio": round(compression_ratio, 5),
            "internal_movement_count": self._internal_movement_count(closes),
            "detection_score": detection_score,
            "detector_version": self.ALGORITHM_VERSION,
            "evidence_mode": "ONLINE_CAUSAL",
            "causal_mode": "ONLINE_CAUSAL",
            # Future-dependent outcomes are intentionally unavailable online.
            "breakout": False,
            "failed_breakout": False,
            "retest": False,
            "exit_index": None,
            "return_to_base": False,
            "expansion_ratio": 0.0,
            "outcome_status": "UNLABELED",
            "thresholds": {
                "min_duration_bars": self.min_duration_bars,
                "max_compression_threshold": self.max_compression_threshold,
                "expansion_threshold": self.expansion_threshold,
                "atr_period": self.atr_period,
            },
        }

    def detect_bases_at_scale(
        self,
        bars: List[Dict[str, Any]],
        scale_label: str = "x1",
        enable_offline_lookahead_labeling: bool = False
    ) -> List[Dict[str, Any]]:
        """
        ONLINE / CAUSAL base detection.

        Only the supplied history is inspected. There is no look-ahead.
        If enable_offline_lookahead_labeling=True, calls explicit offline outcome labeler.
        """
        if enable_offline_lookahead_labeling:
            return self.label_bases_at_scale_offline(bars, scale_label=scale_label)

        normalized = self._normalize_bars(bars, reject_partial=True)

        if len(normalized) < self.min_duration_bars:
            return []

        atrs = self._calculate_atr(normalized, period=self.atr_period)
        bases: List[Dict[str, Any]] = []

        i = 0
        n = len(normalized)

        while i <= n - self.min_duration_bars:
            best_base: Optional[Dict[str, Any]] = None

            max_length = min(
                self.max_base_duration_bars,
                n - i,
            )

            for length in range(self.min_duration_bars, max_length + 1):
                end_index = i + length - 1
                local_atr = atrs[end_index]

                # No arbitrary ATR fallback. If the observed ATR is invalid,
                # this candidate is simply not eligible.
                if local_atr is None:
                    continue

                window = normalized[i:end_index + 1]

                try:
                    candidate = self._candidate_from_window(
                        window,
                        scale_label=scale_label,
                        start_index=i,
                        local_atr=local_atr,
                    )
                except ValueError:
                    continue

                if (
                    best_base is None
                    or candidate["detection_score"] > best_base["detection_score"]
                    or (
                        candidate["detection_score"] == best_base["detection_score"]
                        and candidate["duration_bars"] > best_base["duration_bars"]
                    )
                ):
                    best_base = candidate

            if best_base is not None:
                bases.append(best_base)
                i += best_base["duration_bars"]
            else:
                i += 1

        return bases

    def label_bases_at_scale_offline(
        self,
        bars: List[Dict[str, Any]],
        scale_label: str = "x1",
    ) -> List[Dict[str, Any]]:
        """
        OFFLINE historical outcome labeling.

        This method is intentionally separate from online detection because it
        is allowed to inspect future bars. Its output MUST NOT be fed into
        online inference or PPO observations as a feature.

        The base geometry itself is generated by the causal detector; only the
        post-base outcome fields are labeled from future observations.
        """
        normalized = self._normalize_bars(bars, reject_partial=True)
        online_bases = self.detect_bases_at_scale(normalized, scale_label=scale_label, enable_offline_lookahead_labeling=False)

        if not online_bases:
            return []

        labelled: List[Dict[str, Any]] = []
        n = len(normalized)

        for base in online_bases:
            start = int(base["start_index"])
            end = int(base["end_index"])

            horizon_end = min(
                n,
                end + 1 + self.offline_lookahead_bars,
            )

            future = normalized[end + 1:horizon_end]

            breakout = False
            failed_breakout = False
            retest = False
            return_to_base = False
            exit_idx: Optional[int] = None
            expansion = 0.0

            local_high = float(base["high"])
            local_low = float(base["low"])
            local_range = float(base["range"])

            if local_range <= 0.0:
                future = []

            for offset, ahead_bar in enumerate(future, start=end + 1):
                close = ahead_bar["close"]

                if local_range > 0.0:
                    exp_val = abs(close - float(base["midpoint"])) / local_range
                    if math.isfinite(exp_val):
                        expansion = max(expansion, exp_val)

                outside = close > local_high or close < local_low

                if outside and not breakout:
                    breakout = True
                    exit_idx = offset

                if breakout and (
                    abs(ahead_bar["low"] - local_high) <= local_range * 0.2
                    or abs(ahead_bar["high"] - local_low) <= local_range * 0.2
                ):
                    retest = True

                if breakout and local_low <= close <= local_high:
                    failed_breakout = True
                    return_to_base = True

            result = dict(base)
            result.update(
                {
                    "breakout": breakout,
                    "failed_breakout": failed_breakout,
                    "retest": retest,
                    "exit_index": exit_idx,
                    "return_to_base": return_to_base,
                    "expansion_ratio": round(expansion, 5),
                    "evidence_mode": "OFFLINE_OUTCOME_LABEL",
                    "causal_mode": "OFFLINE_LABELING",
                    "outcome_status": "LABELED",
                }
            )
            labelled.append(result)

        return labelled

    def detect_multiscale_bases(
        self,
        scale_family_map: Dict[str, List[Dict[str, Any]]],
        enable_offline_lookahead_labeling: bool = False
    ) -> Dict[str, Any]:
        """
        Online/causal multi-scale detection.

        Partial/incomplete source bars are ignored by the per-scale detector.
        Future-dependent outcomes are NOT attached when enable_offline_lookahead_labeling=False.
        """
        if not isinstance(scale_family_map, dict):
            raise ValueError("scale_family_map must be a dictionary")

        results_by_scale: Dict[str, Dict[str, Any]] = {}
        total_bases = 0

        for scale_label, bar_series in scale_family_map.items():
            detected = self.detect_bases_at_scale(
                bar_series,
                scale_label=str(scale_label),
                enable_offline_lookahead_labeling=enable_offline_lookahead_labeling
            )
            results_by_scale[str(scale_label)] = {
                "bar_count": len(bar_series),
                "base_count": len(detected),
                "bases": detected,
                "evidence_mode": "OFFLINE_OUTCOME_LABEL" if enable_offline_lookahead_labeling else "ONLINE_CAUSAL",
            }
            total_bases += len(detected)

        verdict = (
            "BASE_STRUCTURE_DETECTED"
            if total_bases >= 10
            else (
                "WEAK_EVIDENCE"
                if total_bases > 0
                else "NO_BASE_STRUCTURE_DETECTED"
            )
        )

        return {
            "gate": 3,
            "gate_name": "Multi-Scale Base Detection",
            "verdict": verdict,
            "total_bases_detected": total_bases,
            "results_by_scale": results_by_scale,
            "algorithm_version": self.ALGORITHM_VERSION,
            "ratio_agnostic": True,
            "evidence_mode": "OFFLINE_OUTCOME_LABEL" if enable_offline_lookahead_labeling else "ONLINE_CAUSAL",
            "DATA_CLASSIFICATION": "REAL_HISTORICAL",
        }

    def label_multiscale_bases_offline(
        self,
        scale_family_map: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Explicit offline labeling counterpart to `detect_multiscale_bases()`.
        """
        if not isinstance(scale_family_map, dict):
            raise ValueError("scale_family_map must be a dictionary")

        results_by_scale: Dict[str, Dict[str, Any]] = {}
        total_bases = 0

        for scale_label, bar_series in scale_family_map.items():
            labelled = self.label_bases_at_scale_offline(
                bar_series,
                scale_label=str(scale_label),
            )
            results_by_scale[str(scale_label)] = {
                "bar_count": len(bar_series),
                "base_count": len(labelled),
                "bases": labelled,
                "evidence_mode": "OFFLINE_OUTCOME_LABEL",
            }
            total_bases += len(labelled)

        verdict = (
            "LABELED_BASE_STRUCTURE"
            if total_bases > 0
            else "NO_BASE_STRUCTURE_LABELED"
        )

        return {
            "gate": 3,
            "gate_name": "Multi-Scale Base Outcome Labeling",
            "verdict": verdict,
            "total_bases_labeled": total_bases,
            "results_by_scale": results_by_scale,
            "algorithm_version": self.ALGORITHM_VERSION,
            "evidence_mode": "OFFLINE_OUTCOME_LABEL",
            "DATA_CLASSIFICATION": "REAL_HISTORICAL",
        }
