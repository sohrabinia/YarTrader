"""
Unit Test Suite for Gate 3 Ratio-Agnostic Gate3BaseDetectorEngine
Verifies multi-scale Base discovery, ratio independence, parameters, and audit outputs.
"""

import pytest
from src.Research.Brain.fractal_base_detection_engine import Gate3BaseDetectorEngine

@pytest.fixture
def sample_bars():
    bars = []
    # 20 consolidation bars followed by a breakout bar
    for i in range(20):
        bars.append({
            "timestamp": 1700000000 + i * 60,
            "open": 2000.0,
            "high": 2001.0,
            "low": 1999.0,
            "close": 2000.5,
            "volume": 100
        })
    # Breakout bar
    bars.append({
        "timestamp": 1700000000 + 20 * 60,
        "open": 2000.5,
        "high": 2010.0,
        "low": 2000.0,
        "close": 2009.0,
        "volume": 500
    })
    return bars

def test_base_detector_version():
    assert Gate3BaseDetectorEngine.ALGORITHM_VERSION == "base_detector_v1.0.0"

def test_detect_bases_at_scale(sample_bars):
    detector = Gate3BaseDetectorEngine(min_duration_bars=4, max_compression_threshold=1.5)
    bases = detector.detect_bases_at_scale(sample_bars, scale_label="x4")
    assert isinstance(bases, list)
    assert len(bases) > 0

    b = bases[0]
    assert b["scale"] == "x4"
    assert "base_id" in b
    assert "start_timestamp" in b
    assert "end_timestamp" in b
    assert "duration_bars" in b
    assert "high" in b
    assert "low" in b
    assert "range" in b
    assert "normalized_range" in b
    assert "return_pct" in b
    assert "volatility" in b
    assert "compression_ratio" in b
    assert "detection_score" in b
    assert b["detector_version"] == "base_detector_v1.0.0"

def test_detect_multiscale_bases(sample_bars):
    detector = Gate3BaseDetectorEngine(min_duration_bars=4)
    scale_map = {
        "x1": sample_bars,
        "x3": sample_bars[:10],
        "x4": sample_bars[:8]
    }
    report = detector.detect_multiscale_bases(scale_map)
    assert report["gate"] == 3
    assert report["ratio_agnostic"] is True
    assert "results_by_scale" in report
    assert "x1" in report["results_by_scale"]
    assert "x3" in report["results_by_scale"]
    assert "x4" in report["results_by_scale"]

def test_empty_bars_handling():
    detector = Gate3BaseDetectorEngine()
    bases = detector.detect_bases_at_scale([], scale_label="x1")
    assert bases == []

def test_insufficient_bars_handling():
    detector = Gate3BaseDetectorEngine(min_duration_bars=10)
    short_bars = [
        {"timestamp": 100, "open": 2000, "high": 2001, "low": 1999, "close": 2000.5, "volume": 10}
    ]
    bases = detector.detect_bases_at_scale(short_bars, scale_label="x1")
    assert bases == []
