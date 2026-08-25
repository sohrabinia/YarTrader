"""
YarTrader Research Unit Tests — MT5 Data Acquisition Pipeline & Integrity Tests
"""

import os
import json
import pytest
from datetime import datetime
from src.Research.Brain.mt_data_acquisition import MTDataAcquisitionEngine
from src.Research.Brain.gold_fractal_intelligence_engine import check_data_integrity, GoldFractalIntelligenceEngine

class TestMTDataAcquisitionPipeline:

    def test_manifest_creation_and_persistence(self, tmp_path):
        manifest_file = os.path.join(tmp_path, "xauusd_m1_manifest.json")
        MTDataAcquisitionEngine.MANIFEST_FILE = manifest_file

        manifest = MTDataAcquisitionEngine.load_or_create_manifest("XAUUSD", target_years=5)
        assert manifest["symbol"] == "XAUUSD"
        assert manifest["target_years"] == 5
        assert manifest["status"] == "IN_PROGRESS"
        assert manifest["system_identity"] == "YarTrader"
        assert os.path.exists(manifest_file)

        manifest["chunks_completed"] += 1
        MTDataAcquisitionEngine.save_manifest(manifest)

        reloaded = MTDataAcquisitionEngine.load_or_create_manifest("XAUUSD", target_years=5)
        assert reloaded["chunks_completed"] == 1

    def test_data_integrity_check(self):
        valid_candles = [
            {"timestamp": "2026-08-24T12:00:00", "open": 2350.0, "high": 2355.0, "low": 2348.0, "close": 2352.0, "volume": 100},
            {"timestamp": "2026-08-24T12:01:00", "open": 2352.0, "high": 2358.0, "low": 2350.0, "close": 2356.0, "volume": 120}
        ]
        res = check_data_integrity(valid_candles)
        assert res["status"] == "VERIFIED_VALID"
        assert res["issues_found"] == 0

    def test_data_integrity_ohlc_violation(self):
        invalid_candles = [
            {"timestamp": "2026-08-24T12:00:00", "open": 2350.0, "high": 2340.0, "low": 2348.0, "close": 2352.0, "volume": 100}  # High < Open
        ]
        res = check_data_integrity(invalid_candles)
        assert res["status"] == "DATACLEAN_WARNINGS"
        assert res["issues_found"] == 1

    def test_acquisition_returns_blocked_status_on_linux(self):
        res = MTDataAcquisitionEngine.acquire_multi_year_m1_history("XAUUSD", target_years=5)
        assert res["status"] in ["REAL_DATA_UNAVAILABLE", "BLOCKED"]
        assert res["records_acquired"] == 0

    def test_indicator_free_engine_purity(self):
        engine = GoldFractalIntelligenceEngine(symbol="XAUUSD")
        assert not hasattr(engine, "rsi")
        assert not hasattr(engine, "macd")
        assert not hasattr(engine, "ema")
        assert not hasattr(engine, "sma")
        assert not hasattr(engine, "atr")
        assert not hasattr(engine, "bollinger")
