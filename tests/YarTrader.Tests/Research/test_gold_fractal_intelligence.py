import os
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.Research.Brain.gold_fractal_intelligence_engine import GoldFractalIntelligenceEngine, TIMEFRAMES
from src.Application.Services.web_dashboard import app

class TestGoldFractalIntelligenceEngine:

    @pytest.fixture
    def engine(self):
        return GoldFractalIntelligenceEngine(symbol="XAUUSD")

    @pytest.fixture
    def sample_candles(self):
        candles = []
        base_p = 2350.0
        for i in range(20):
            open_p = base_p + (i % 3 - 1) * 1.5
            close_p = open_p + (i % 2 - 0.5) * 2.0
            high_p = max(open_p, close_p) + 2.0
            low_p = min(open_p, close_p) - 2.0
            candles.append({
                "timestamp": f"2026-08-24T12:{i:02d}:00",
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": 1000
            })
        return candles

    def test_base_detection_engine(self, engine, sample_candles):
        bases = engine.detect_base_structures("H1", sample_candles)
        assert len(bases) > 0
        b = bases[0]
        assert "BASE_XAUUSD_H1_" in b["Base_ID"]
        assert b["Symbol"] == "XAUUSD"
        assert b["Timeframe"] == "H1"
        assert "High" in b and "Low" in b and "Range" in b and "Duration" in b
        assert b["Type"] in ["Bullish Base", "Bearish Base", "Neutral Base"]

    def test_internal_base_behavior_analysis(self, engine, sample_candles):
        behavior = engine.analyze_internal_base_behavior(sample_candles, base_range=20.0)
        assert "rotations" in behavior
        assert "higher_highs" in behavior
        assert "higher_lows" in behavior
        assert "lower_highs" in behavior
        assert "lower_lows" in behavior
        assert "compression_ratio" in behavior
        assert "state" in behavior
        assert behavior["state"] in ["Accumulation-like", "Distribution-like", "Balanced", "Expansion Preparation"]

    def test_expansion_and_leg_engine(self, engine, sample_candles):
        bases = engine.detect_base_structures("H1", sample_candles)
        assert len(bases) > 0
        base = bases[0]
        subsequent = sample_candles[:15]
        exp = engine.analyze_expansion_and_legs(base, subsequent)
        assert len(exp["legs"]) == 3
        assert len(exp["returns"]) >= 1
        assert "leg1_vs_leg2_ratio" in exp
        assert exp["expansion_dynamics"] in ["Strengthening Expansion", "Weakening Expansion", "Exhaustion"]

    def test_multi_timeframe_fractal_mapping(self, engine, sample_candles):
        tf_candles = {tf: sample_candles for tf in TIMEFRAMES}
        mtf_map = engine.map_multi_timeframe_fractals(tf_candles)
        assert mtf_map["symbol"] == "XAUUSD"
        assert "hierarchy_tree" in mtf_map
        assert "Monthly" in mtf_map["hierarchy_tree"]
        assert "M5" in mtf_map["hierarchy_tree"]
        assert mtf_map["dominant_scale"] in TIMEFRAMES

    def test_active_fractal_report_and_target_zone(self, engine, sample_candles):
        tf_candles = {tf: sample_candles for tf in TIMEFRAMES}
        report = engine.generate_active_fractal_report(tf_candles)
        assert report["Symbol"] == "XAUUSD"
        assert report["Dominant_Scale"] in TIMEFRAMES
        assert "Target_Zone" in report
        assert "Zone_Low" in report["Target_Zone"]
        assert "Zone_High" in report["Target_Zone"]
        assert "Chart_Markings" in report
        assert "BASE" in report["Chart_Markings"]
        assert "TARGET_ZONE" in report["Chart_Markings"]

    def test_historical_case_studies_and_failure_analysis(self, engine):
        cases, fails = engine.run_historical_case_studies(count=50)
        assert len(cases) == 50
        assert len(fails) > 0
        cs = cases[0]
        assert cs["Case_ID"] == "CS_XAUUSD_001"
        assert "Base_Structure" in cs
        assert "Internal_Behavior" in cs
        assert "Expansion" in cs
        assert "Explanation" in cs

        fail = fails[0]
        assert "Failure_ID" in fail
        assert "Possible_Cause" in fail

    def test_live_demo_validation(self, engine, sample_candles):
        tf_candles = {tf: sample_candles for tf in TIMEFRAMES}
        report = engine.generate_active_fractal_report(tf_candles)
        val = engine.record_demo_validation(
            fractal_report=report,
            entry_price=2350.0,
            stop_loss=2335.0,
            target_price=2385.0,
            result="VALIDATED"
        )
        assert val["Symbol"] == "XAUUSD"
        assert val["Result"] == "VALIDATED"
        assert val["Interpretation_Correct"] is True

    def test_fastapi_gold_fractal_endpoints(self):
        client = TestClient(app)

        # 1. Summary
        res1 = client.get("/api/fractal/gold/summary?symbol=XAUUSD")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "SUCCESS"
        assert data1["symbol"] == "XAUUSD"
        assert "active_fractal" in data1
        assert "chart_markings" in data1

        # 2. Structures with Filters
        res2 = client.get("/api/fractal/gold/structures?symbol=XAUUSD&timeframe=H1&direction=Bullish")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "SUCCESS"
        assert "structures" in data2

        # 3. Hierarchy
        res3 = client.get("/api/fractal/gold/hierarchy?symbol=XAUUSD")
        assert res3.status_code == 200
        data3 = res3.json()
        assert "hierarchy" in data3
        assert "Monthly" in data3["hierarchy"]

        # 4. Case Studies
        res4 = client.get("/api/fractal/gold/case-studies?symbol=XAUUSD")
        assert res4.status_code == 200
        data4 = res4.json()
        assert data4["total_cases"] == 50

        # 5. Demo Validation
        res5 = client.get("/api/fractal/gold/demo-validation?symbol=XAUUSD")
        assert res5.status_code == 200
        data5 = res5.json()
        assert data5["overall_accuracy_score"] == 86.0

    def test_live_trading_hard_isolation(self):
        # Strict SRE Safety Rule: Live trading must remain False / disabled repository-wide
        from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
        from src.Infrastructure.exceptions import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        assert "Real Live Trading is hard-disabled" in str(exc_info.value)
