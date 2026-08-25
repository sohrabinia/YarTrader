"""
YarTrader Research Unit Tests — Gold Fractal Intelligence Engine & API Contract Tests
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Research.Brain.gold_fractal_intelligence_engine import (
    GoldFractalIntelligenceEngine,
    TIMEFRAMES,
    STANDARD_MT5_TIMEFRAMES,
    POWER_OF_2_SCALES,
    POWER_OF_3_SCALES,
    aggregate_m1_candles,
    check_data_integrity
)

class TestGoldFractalIntelligenceEngine:

    @pytest.fixture
    def engine(self):
        return GoldFractalIntelligenceEngine(symbol="XAUUSD")

    @pytest.fixture
    def sample_candles(self):
        return [
            {"timestamp": "2026-08-24T12:00:00", "open": 2348.5, "high": 2350.5, "low": 2345.5, "close": 2349.0, "volume": 100},
            {"timestamp": "2026-08-24T12:01:00", "open": 2349.0, "high": 2351.0, "low": 2347.0, "close": 2350.5, "volume": 110},
            {"timestamp": "2026-08-24T12:02:00", "open": 2350.5, "high": 2352.0, "low": 2348.0, "close": 2349.5, "volume": 95},
            {"timestamp": "2026-08-24T12:03:00", "open": 2349.5, "high": 2353.0, "low": 2348.5, "close": 2352.0, "volume": 130},
            {"timestamp": "2026-08-24T12:04:00", "open": 2352.0, "high": 2354.0, "low": 2350.0, "close": 2351.5, "volume": 105},
            {"timestamp": "2026-08-24T12:05:00", "open": 2351.5, "high": 2354.5, "low": 2349.5, "close": 2353.5, "volume": 115},
            {"timestamp": "2026-08-24T12:06:00", "open": 2353.5, "high": 2355.0, "low": 2351.0, "close": 2352.5, "volume": 90},
            {"timestamp": "2026-08-24T12:07:00", "open": 2352.5, "high": 2356.0, "low": 2352.0, "close": 2355.0, "volume": 140},
            {"timestamp": "2026-08-24T12:08:00", "open": 2355.0, "high": 2357.0, "low": 2353.0, "close": 2354.0, "volume": 100},
            {"timestamp": "2026-08-24T12:09:00", "open": 2354.0, "high": 2358.0, "low": 2353.5, "close": 2357.0, "volume": 150}
        ]

    def test_base_structure_detection(self, engine, sample_candles):
        bases = engine.detect_base_structures("H1", sample_candles)
        assert len(bases) > 0
        b = bases[0]
        assert b["Symbol"] == "XAUUSD"
        assert b["Timeframe"] == "H1"
        assert b["High"] >= b["Low"]
        assert "Type" in b
        assert "Internal_Behavior" in b

    def test_internal_base_behavior_analysis(self, engine, sample_candles):
        behavior = engine.analyze_internal_base_behavior(sample_candles, base_range=12.5)
        assert "rotations" in behavior
        assert "compression_ratio" in behavior
        assert "directional_pressure" in behavior
        assert "state" in behavior
        assert behavior["state"] in ["Accumulation-like", "Distribution-like", "Balanced", "Expansion Preparation"]

    def test_expansion_and_leg_analysis(self, engine, sample_candles):
        base_record = {"High": 2358.0, "Low": 2345.5, "Range": 12.5}
        exp = engine.analyze_expansion_and_legs(base_record, sample_candles)
        assert "legs" in exp
        assert "returns" in exp
        assert "expansion_dynamics" in exp
        assert exp["expansion_dynamics"] in ["Strengthening Expansion", "Weakening Expansion", "Exhaustion"]

    def test_multi_timeframe_fractal_mapping(self, engine, sample_candles):
        tf_candles = {tf: sample_candles for tf in TIMEFRAMES}
        mtf_map = engine.map_multi_timeframe_fractals(tf_candles)
        assert mtf_map["symbol"] == "XAUUSD"
        assert "hierarchy_tree" in mtf_map
        assert "MN1" in mtf_map["hierarchy_tree"] or "Monthly" in mtf_map["hierarchy_tree"]
        assert mtf_map["dominant_scale"] in TIMEFRAMES

    def test_active_fractal_report_and_target_zone(self, engine, sample_candles):
        tf_candles = {tf: sample_candles for tf in TIMEFRAMES}
        report = engine.generate_active_fractal_report(tf_candles)
        assert report["Symbol"] == "XAUUSD"
        assert report["Dominant_Scale"] in TIMEFRAMES
        assert "Target_Zone" in report
        assert "Chart_Markings" in report
        assert report["Target_Zone"]["Status"] == "ACTIVE_UNTOUCHED"

    def test_historical_case_studies(self, engine):
        cases, fails = engine.run_historical_case_studies(count=50)
        assert len(cases) == 50
        assert len(fails) > 0
        assert cases[0]["Case_ID"].startswith("CS_XAUUSD_")
        assert fails[0]["Failure_ID"].startswith("FAIL_XAUUSD_")

    def test_demo_validation_recording(self, engine):
        fractal_report = {
            "Current_Structure": "H1 Bullish Base",
            "Dominant_Scale": "H1",
            "Phase": "Expansion Preparation",
            "Chart_Markings": {"FRACTAL_DETECTED": "FRACTAL_H1_ACTIVE"}
        }
        rec = engine.record_demo_validation(
            fractal_report=fractal_report,
            entry_price=2350.0,
            stop_loss=2335.0,
            target_price=2385.0,
            result="VALIDATED"
        )
        assert rec["Validation_ID"].startswith("DEMO_VAL_")
        assert rec["Symbol"] == "XAUUSD"
        assert rec["Interpretation_Correct"] is True

    def test_m1_aggregation(self, sample_candles):
        p2_4m = aggregate_m1_candles(sample_candles, 4)
        assert len(p2_4m) == 3  # 10 bars / 4 = 3 chunk bars
        assert p2_4m[0]["open"] == sample_candles[0]["open"]
        assert p2_4m[0]["high"] == max(c["high"] for c in sample_candles[:4])

    def test_live_trading_hard_isolation(self):
        from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
        assert os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("false", "0")

    def test_fastapi_gold_fractal_endpoints(self):
        client = TestClient(app)

        res1 = client.get("/api/fractal/gold/summary?symbol=XAUUSD")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "SUCCESS"
        assert data1["symbol"] == "XAUUSD"

        res2 = client.get("/api/fractal/gold/structures?symbol=XAUUSD&timeframe=H1&direction=Bullish")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "SUCCESS"

        res3 = client.get("/api/fractal/gold/hierarchy?symbol=XAUUSD")
        assert res3.status_code == 200
        data3 = res3.json()
        assert "hierarchy" in data3
