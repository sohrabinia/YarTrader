"""
Tests for YarTrader Forensic Fractal Research Engine — Gates 0, 1, & 2
========================================================================
Covering:
 1. Data integrity audit
 2. Duplicate timestamps handling
 3. Missing timestamps detection
 4. Invalid OHLC relationships
 5. OHLC aggregation rules
 6. Family x3 scale construction
 7. Family x4 scale construction
 8. Timestamp preservation
 9. Partial trailing group handling
 10. Deterministic repeatability
 11. Empty dataset handling
 12. Insufficient data handling
"""

import pytest
from src.Research.Brain.fractal_data_scale_engine import (
    MathematicalScaleDefinition,
    ResearchDataIntegrityEngine,
    ResearchBaselineEngine,
    ScaleConstructionEngine
)

def make_sample_bars(count=100, start_ts=1700000000):
    bars = []
    p = 2000.0
    for i in range(count):
        h = p + 2.0
        l = p - 1.0
        c = p + 0.5
        o = p
        bars.append({
            "timestamp": start_ts + i * 60,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 10
        })
        p = c
    return bars


def test_1_data_integrity_pass():
    bars = make_sample_bars(100)
    report = ResearchDataIntegrityEngine.audit_dataset(bars, "XAUUSD")
    assert report["gate"] == 0
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert report["record_count"] == 100


def test_2_duplicate_timestamps():
    bars = make_sample_bars(20)
    bars[5]["timestamp"] = bars[4]["timestamp"] # Inject duplicate
    report = ResearchDataIntegrityEngine.audit_dataset(bars, "XAUUSD")
    assert report["status"] == "FAIL"
    assert report["duplicate_timestamps"] == 1


def test_3_missing_timestamps():
    bars = make_sample_bars(20)
    bars[8]["timestamp"] = None # Inject missing
    report = ResearchDataIntegrityEngine.audit_dataset(bars, "XAUUSD")
    assert report["status"] == "FAIL"
    assert report["missing_timestamps"] == 1


def test_4_invalid_ohlc():
    bars = make_sample_bars(20)
    bars[3]["high"] = 1000.0 # High < Low
    bars[3]["low"] = 2000.0
    report = ResearchDataIntegrityEngine.audit_dataset(bars, "XAUUSD")
    assert report["status"] == "FAIL"
    assert report["invalid_ohlc_relationships"] == 1


def test_5_ohlc_aggregation_rules():
    raw_chunk = [
        {"timestamp": 100, "open": 10.0, "high": 15.0, "low": 9.0, "close": 12.0, "volume": 5},
        {"timestamp": 160, "open": 12.0, "high": 18.0, "low": 11.0, "close": 16.0, "volume": 8},
        {"timestamp": 220, "open": 16.0, "high": 17.0, "low": 14.0, "close": 15.0, "volume": 7},
        {"timestamp": 280, "open": 15.0, "high": 20.0, "low": 13.0, "close": 19.0, "volume": 10}
    ]
    scaled_x4 = ScaleConstructionEngine.build_scale_family(raw_chunk, multiplier=4)
    bar_x4 = scaled_x4[4][0]

    assert bar_x4["open"] == 10.0      # First open
    assert bar_x4["high"] == 20.0      # Max high across 4 bars
    assert bar_x4["low"] == 9.0        # Min low across 4 bars
    assert bar_x4["close"] == 19.0     # Last close
    assert bar_x4["volume"] == 30.0    # Sum volume (5+8+7+10)
    assert bar_x4["start_timestamp"] == 100
    assert bar_x4["end_timestamp"] == 280


def test_6_family_x3_construction():
    bars = make_sample_bars(81)
    scaled_x3 = ScaleConstructionEngine.build_scale_family(bars, multiplier=3)
    assert 1 in scaled_x3 and 3 in scaled_x3 and 9 in scaled_x3 and 27 in scaled_x3 and 81 in scaled_x3
    assert len(scaled_x3[3]) == 27
    assert len(scaled_x3[9]) == 9
    assert len(scaled_x3[27]) == 3
    assert len(scaled_x3[81]) == 1


def test_7_family_x4_construction():
    bars = make_sample_bars(256)
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    assert 1 in scaled_x4 and 4 in scaled_x4 and 16 in scaled_x4 and 64 in scaled_x4 and 256 in scaled_x4
    assert len(scaled_x4[4]) == 64
    assert len(scaled_x4[16]) == 16
    assert len(scaled_x4[64]) == 4
    assert len(scaled_x4[256]) == 1


def test_8_timestamp_preservation():
    bars = make_sample_bars(16, start_ts=1700000000)
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    bar_x16 = scaled_x4[16][0]
    assert bar_x16["start_timestamp"] == 1700000000
    assert bar_x16["end_timestamp"] == 1700000000 + (15 * 60)


def test_9_partial_trailing_group():
    bars = make_sample_bars(10) # 10 bars on scale x4 => 2 full chunks (4, 4) + 1 trailing partial chunk (2)
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    x4_bars = scaled_x4[4]
    assert len(x4_bars) == 3
    assert x4_bars[0]["is_partial_trailing_group"] is False
    assert x4_bars[1]["is_partial_trailing_group"] is False
    assert x4_bars[2]["is_partial_trailing_group"] is True
    assert x4_bars[2]["raw_count"] == 2


def test_10_deterministic_repeatability():
    bars = make_sample_bars(100)
    run_1 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    run_2 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    assert run_1 == run_2


def test_11_empty_dataset():
    report_0 = ResearchDataIntegrityEngine.audit_dataset([], "XAUUSD")
    assert report_0["status"] == "INSUFFICIENT_DATA"

    report_1 = ResearchBaselineEngine.compute_baseline([])
    assert report_1["status"] == "INSUFFICIENT_DATA"


def test_12_insufficient_data():
    bars = make_sample_bars(5) # Less than 10 minimum
    report = ResearchDataIntegrityEngine.audit_dataset(bars, "XAUUSD")
    assert report["status"] == "INSUFFICIENT_DATA"
    assert report["passed"] is False
