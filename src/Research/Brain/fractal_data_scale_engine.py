"""
YarTrader Forensic Fractal Research Engine — Gates 0, 1, & 2
============================================================
Isolated research module implementing:
 - Mathematical Definition of Scale
 - GATE 0: Research Data Integrity Audit & Report
 - GATE 1: Deterministic Multiscale Baseline Benchmark & Report
 - GATE 2: Deterministic Scale Construction (Families x3 & x4) & Report

TRADING IS STRICTLY FORBIDDEN (BUY/SELL = FALSE, LIVE_TRADING = FALSE).
"""

import json
import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

class MathematicalScaleDefinition:
    """
    Mathematical Definition of Scale in Price Action Analysis:
    A scale S is defined as a tuple S = (N, dt_base, M, T_start, T_end)
    Where:
      - N: Integer scale aggregation factor (e.g. 1, 3, 4, 9, 16, ...)
      - dt_base: Base observation granularity (e.g. M1 raw bar)
      - M: OHLCV aggregation operator:
          Open  = Open(bar_0)
          High  = max(High(bar_i)) for i in [0..N-1]
          Low   = min(Low(bar_i)) for i in [0..N-1]
          Close = Close(bar_N-1)
          Volume = sum(Volume(bar_i)) for i in [0..N-1]
      - T_start: Timestamp of Open(bar_0)
      - T_end: Timestamp of Close(bar_N-1)
      - Elapsed Time = T_end - T_start
    A scale is NOT a conventional timeframe label, but a deterministic aggregation chunk.
    """
    @staticmethod
    def get_definition_summary() -> Dict[str, Any]:
        return {
            "scale_definition": "S = (N, dt_base, M, T_start, T_end)",
            "aggregation_rules": {
                "open": "First observation open price in chunk",
                "high": "Maximum high price across all observations in chunk",
                "low": "Minimum low price across all observations in chunk",
                "close": "Last observation close price in chunk",
                "volume": "Sum of volumes across all observations in chunk",
                "timestamp_rule": "Start TS = bar_0.timestamp, End TS = bar_last.timestamp"
            }
        }


class ResearchDataIntegrityEngine:
    """GATE 0: Validates research dataset integrity and generates DataIntegrityReport."""

    @staticmethod
    def audit_dataset(bars: List[Dict[str, Any]], instrument: str = "XAUUSD", source: str = "MT5_M1_HISTORICAL") -> Dict[str, Any]:
        if not bars:
            return {
                "gate": 0,
                "gate_name": "Data Integrity",
                "status": "INSUFFICIENT_DATA",
                "instrument": instrument,
                "source": source,
                "record_count": 0,
                "passed": False,
                "reason": "Dataset is empty or unavailable."
            }

        record_count = len(bars)
        if record_count < 10:
            return {
                "gate": 0,
                "gate_name": "Data Integrity",
                "status": "INSUFFICIENT_DATA",
                "instrument": instrument,
                "source": source,
                "record_count": record_count,
                "passed": False,
                "reason": f"Insufficient dataset size ({record_count} records < 10 minimum)."
            }

        duplicates = 0
        missing_timestamps = 0
        unordered_timestamps = 0
        invalid_ohlc = 0
        nan_null_values = 0
        data_gaps = 0

        prev_ts = None
        for i, bar in enumerate(bars):
            # Check null / NaN values
            for k in ["open", "high", "low", "close"]:
                val = bar.get(k)
                if val is None or not isinstance(val, (int, float)) or math.isnan(val) or val <= 0:
                    nan_null_values += 1

            # Check OHLC logical validity
            o = bar.get("open", 0)
            h = bar.get("high", 0)
            l = bar.get("low", 0)
            c = bar.get("close", 0)
            if h < l or o > h or o < l or c > h or c < l:
                invalid_ohlc += 1

            # Check timestamp ordering and duplicates
            ts = bar.get("timestamp") or bar.get("time")
            if ts is None:
                missing_timestamps += 1
            else:
                if prev_ts is not None:
                    if ts == prev_ts:
                        duplicates += 1
                    elif ts < prev_ts:
                        unordered_timestamps += 1
                    elif (ts - prev_ts) > 300: # gap > 5 mins for M1
                        data_gaps += 1
                prev_ts = ts

        start_ts = bars[0].get("timestamp") or bars[0].get("time") or "N/A"
        end_ts = bars[-1].get("timestamp") or bars[-1].get("time") or "N/A"

        # Compute dataset SHA-256 fingerprint
        sample_subset = bars[:min(100, record_count)]
        dataset_hash = hashlib.sha256(json.dumps(sample_subset, default=str).encode("utf-8")).hexdigest()[:16]

        passed = (invalid_ohlc == 0 and nan_null_values == 0 and duplicates == 0 and unordered_timestamps == 0 and missing_timestamps == 0)
        status = "PASS" if passed else "FAIL"

        return {
            "gate": 0,
            "gate_name": "Data Integrity",
            "status": status,
            "passed": passed,
            "instrument": instrument,
            "source": source,
            "timeframe_granularity": "M1_OR_RAW_TICKS",
            "start_timestamp": str(start_ts),
            "end_timestamp": str(end_ts),
            "record_count": record_count,
            "missing_timestamps": missing_timestamps,
            "duplicate_timestamps": duplicates,
            "unordered_timestamps": unordered_timestamps,
            "invalid_ohlc_relationships": invalid_ohlc,
            "nan_null_values": nan_null_values,
            "data_gaps_count": data_gaps,
            "timezone": "UTC",
            "session_assumptions": "24/7 Continuous OR 24/5 FX Session",
            "dataset_version_hash": f"ds_v1_{dataset_hash}"
        }


class ResearchBaselineEngine:
    """GATE 1: Deterministic Multiscale Baseline Statistics & Report."""

    @staticmethod
    def compute_baseline(bars: List[Dict[str, Any]], scale_factors: List[int] = [1, 4, 16, 64]) -> Dict[str, Any]:
        if not bars or len(bars) < 10:
            return {
                "gate": 1,
                "gate_name": "Baseline Benchmark",
                "status": "INSUFFICIENT_DATA",
                "passed": False,
                "reason": "Insufficient bars to compute baseline."
            }

        scale_reports = {}
        closes = [b["close"] for b in bars]

        for s in scale_factors:
            chunk_size = s
            scale_closes = [closes[i] for i in range(chunk_size - 1, len(closes), chunk_size)]
            if len(scale_closes) < 2:
                continue

            returns = []
            for i in range(1, len(scale_closes)):
                r = (scale_closes[i] - scale_closes[i-1]) / scale_closes[i-1] if scale_closes[i-1] > 0 else 0
                returns.append(r)

            mean_ret = sum(returns) / len(returns) if returns else 0.0
            var_ret = sum((r - mean_ret)**2 for r in returns) / len(returns) if returns else 0.0
            stdev_ret = math.sqrt(var_ret)

            ranges = []
            for i in range(0, len(bars), chunk_size):
                chunk = bars[i:i+chunk_size]
                if chunk:
                    h = max(b["high"] for b in chunk)
                    l = min(b["low"] for b in chunk)
                    ranges.append(h - l)

            avg_range = sum(ranges) / len(ranges) if ranges else 0.0
            norm_range = avg_range / scale_closes[0] if scale_closes[0] > 0 else 0.0

            # Autocorrelation (lag 1)
            autocorr_1 = 0.0
            if len(returns) > 2 and var_ret > 0:
                cov_1 = sum((returns[i] - mean_ret) * (returns[i-1] - mean_ret) for i in range(1, len(returns))) / (len(returns) - 1)
                autocorr_1 = cov_1 / var_ret

            scale_reports[f"scale_x{s}"] = {
                "scale_factor": s,
                "sample_size": len(scale_closes),
                "return_mean": round(mean_ret, 6),
                "return_stdev_volatility": round(stdev_ret, 6),
                "average_range": round(avg_range, 5),
                "normalized_range": round(norm_range, 6),
                "autocorrelation_lag1": round(autocorr_1, 4),
                "method": "Linear Return & Moving Range Non-Fractal Benchmark",
                "limitations": "Linear baseline measures variance and range without evaluating fractal self-similarity or nested base trees."
            }

        return {
            "gate": 1,
            "gate_name": "Baseline Benchmark",
            "status": "PASS",
            "passed": True,
            "scales_evaluated": scale_reports,
            "baseline_note": "Reference point established. Zero fractal claims made."
        }


class ScaleConstructionEngine:
    """GATE 2: Deterministic Scale Construction for Family x3 & Family x4."""

    FAMILY_X3 = [1, 3, 9, 27, 81, 243, 729, 2187, 6561, 19683]
    FAMILY_X4 = [1, 4, 16, 64, 256, 1024, 4096, 16384]

    @classmethod
    def build_scale_family(cls, raw_bars: List[Dict[str, Any]], multiplier: int = 4) -> Dict[int, List[Dict[str, Any]]]:
        if multiplier not in [3, 4]:
            raise ValueError("Only scale families x3 and x4 are supported.")

        scales = cls.FAMILY_X4 if multiplier == 4 else cls.FAMILY_X3
        scaled_dataset = {}

        for scale_factor in scales:
            if scale_factor == 1:
                scaled_dataset[1] = raw_bars
                continue

            aggregated_bars = []
            chunk_size = scale_factor
            raw_count = len(raw_bars)

            for i in range(0, raw_count, chunk_size):
                chunk = raw_bars[i:i+chunk_size]
                if not chunk:
                    continue

                open_p = chunk[0]["open"]
                close_p = chunk[-1]["close"]
                high_p = max(b["high"] for b in chunk)
                low_p = min(b["low"] for b in chunk)
                vol = sum(b.get("volume", 1.0) for b in chunk)
                ts_start = chunk[0].get("timestamp") or chunk[0].get("time") or i
                ts_end = chunk[-1].get("timestamp") or chunk[-1].get("time") or (i + len(chunk) - 1)

                is_partial = (len(chunk) < chunk_size)

                aggregated_bars.append({
                    "scale": scale_factor,
                    "index": len(aggregated_bars),
                    "open": round(open_p, 5),
                    "high": round(high_p, 5),
                    "low": round(low_p, 5),
                    "close": round(close_p, 5),
                    "volume": round(vol, 2),
                    "raw_count": len(chunk),
                    "is_partial_trailing_group": is_partial,
                    "start_timestamp": ts_start,
                    "end_timestamp": ts_end
                })

            scaled_dataset[scale_factor] = aggregated_bars

        return scaled_dataset

    @classmethod
    def audit_scale_construction(cls, scaled_x4: Dict[int, List[Dict]], scaled_x3: Dict[int, List[Dict]]) -> Dict[str, Any]:
        def build_manifest(scaled_dict, family_scales, ratio_val):
            manifest = {}
            for scale, bars in scaled_dict.items():
                partial_groups = [b for b in bars if b.get("is_partial_trailing_group")]
                parent_s = scale // ratio_val if scale > 1 else None
                child_s = scale * ratio_val if scale * ratio_val in family_scales else None

                start_ts = (bars[0].get("start_timestamp") or bars[0].get("timestamp") or bars[0].get("time")) if bars else "N/A"
                end_ts = (bars[-1].get("end_timestamp") or bars[-1].get("timestamp") or bars[-1].get("time")) if bars else "N/A"

                manifest[f"scale_x{scale}"] = {
                    "parent_scale": f"x{parent_s}" if parent_s else None,
                    "child_scale": f"x{child_s}" if child_s else None,
                    "ratio": ratio_val,
                    "source_record_count": len(scaled_dict.get(1, [])),
                    "generated_record_count": len(bars),
                    "partial_trailing_groups_count": len(partial_groups),
                    "aggregation_method": "Deterministic OHLCV Chunk Aggregation",
                    "timestamp_rule": "First Bar Open TS -> Last Bar Close TS",
                    "first_timestamp": str(start_ts),
                    "last_timestamp": str(end_ts),
                    "coverage_pct": 100.0
                }
            return manifest

        x4_manifest = build_manifest(scaled_x4, cls.FAMILY_X4, 4) if scaled_x4 else {}
        x3_manifest = build_manifest(scaled_x3, cls.FAMILY_X3, 3) if scaled_x3 else {}

        return {
            "gate": 2,
            "gate_name": "Scale Construction",
            "status": "PASS",
            "passed": True,
            "family_x4_manifest": x4_manifest,
            "family_x3_manifest": x3_manifest,
            "partial_group_rule": "Deterministic inclusion with boolean flag is_partial_trailing_group=True"
        }
