"""
Unit Test Suite for Autonomous MT4/MT5 Historical Data Acquisition Engine
Verifies discovery, selection, dataset hashing, synthetic fallback rejection, and truthfulness gates.
"""

import os
import json
import pytest
import tempfile
from src.Research.Brain.mt_data_acquisition import MTDataAcquisitionEngine

def test_environment_discovery_linux():
    discovery = MTDataAcquisitionEngine.discover_environment()
    assert isinstance(discovery, dict)
    assert "os_platform" in discovery
    assert "mt4_installations" in discovery
    assert "mt5_installations" in discovery
    assert "available_export_files" in discovery
    assert "discovered_symbol_variants" in discovery

def test_select_data_source_empty():
    empty_discovery = {
        "os_platform": "Linux",
        "mt4_installations": [],
        "mt5_installations": [],
        "available_export_files": [],
        "discovered_symbol_variants": []
    }
    report = MTDataAcquisitionEngine.select_data_source(empty_discovery)
    assert report["quality_status"] == "REAL_DATA_UNAVAILABLE"
    assert "No authentic MT4/MT5" in report["selection_reason"]

def test_dataset_sha256_deterministic():
    records_1 = [{"timestamp": 100, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5, "volume": 10}]
    records_2 = [{"timestamp": 100, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5, "volume": 10}]

    hash1 = MTDataAcquisitionEngine.compute_dataset_sha256(records_1)
    hash2 = MTDataAcquisitionEngine.compute_dataset_sha256(records_2)
    assert hash1 == hash2
    assert len(hash1) == 64

def test_synthetic_fallback_rejection():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        synthetic_payload = {
            "dataset_metadata": {
                "instrument": "XAUUSD",
                "is_synthetic": True,
                "DATA_CLASSIFICATION": "SYNTHETIC"
            },
            "records": [
                {"timestamp": 100, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5, "volume": 10}
            ]
        }
        json.dump(synthetic_payload, f)
        temp_path = f.name

    try:
        records, metadata = MTDataAcquisitionEngine.load_authentic_dataset(temp_path)
        assert records is None
        assert metadata is None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_load_authentic_valid_dataset():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        real_payload = {
            "dataset_metadata": {
                "instrument": "XAUUSD",
                "source_platform": "MT5",
                "broker": "Alpari-Demo",
                "is_synthetic": False,
                "DATA_CLASSIFICATION": "REAL_HISTORICAL"
            },
            "records": [
                {"timestamp": 1700000000, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5, "volume": 100},
                {"timestamp": 1700000060, "open": 2000.5, "high": 2002.0, "low": 2000.0, "close": 2001.5, "volume": 120}
            ]
        }
        json.dump(real_payload, f)
        temp_path = f.name

    try:
        records, metadata = MTDataAcquisitionEngine.load_authentic_dataset(temp_path)
        assert records is not None
        assert len(records) == 2
        assert metadata["DATA_CLASSIFICATION"] == "REAL_HISTORICAL"
        assert "sha256_hash" in metadata
        assert len(metadata["sha256_hash"]) == 64
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
