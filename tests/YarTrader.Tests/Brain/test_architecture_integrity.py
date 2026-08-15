import os
import shutil
import pytest
from datetime import datetime, timedelta
from src.Research.Brain.models import (
    SimulatedDecision, MarketObservation, MarketEvent, PatternMemory, ExperienceMemory
)
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.integrity import IntelligenceIntegrityService
from src.Research.Brain.query import KnowledgeQueryInterface
from src.Research.Brain.memory import MarketMemorySystem

TEST_STORAGE_DIR = os.path.join("runtime_logs", "test_integrity_memory")

@pytest.fixture(autouse=True)
def clean_test_storage():
    """Ensures test storage is cleared before and after each test."""
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)
    yield
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)


def test_decision_immutability():
    """Verify that SimulatedDecision is strictly immutable and cannot be modified after creation."""
    decision = SimulatedDecision(
        timestamp=datetime(2026, 1, 1, 12, 0),
        symbol="XAUUSD",
        price=1800.0,
        decision_action="BUY",
        context={"confidence_score": 0.85},
        evidence={},
        reason="Test reason"
    )

    # Attempting to mutate any field must raise an AttributeError because frozen=True
    with pytest.raises(AttributeError):
        decision.price = 1810.0  # type: ignore

    with pytest.raises(AttributeError):
        decision.symbol = "EURUSD"  # type: ignore


def test_judge_brain_isolation_and_lucky_win_diagnosis():
    """Verify Judge Brain evaluates decision outcomes independently, detects lucky wins, and does not alter history."""
    judge = JudgeBrain()

    decision = SimulatedDecision(
        timestamp=datetime(2026, 1, 1, 12, 0),
        symbol="XAUUSD",
        price=1800.0,
        decision_action="BUY"
    )

    # Case A: Structural Earned Success
    outcome_earned = {
        "final_result": "SUCCESS",
        "max_favorable_excursion": 30.0,
        "max_adverse_excursion": -2.0
    }
    res_earned = judge.evaluate_decision_outcome(decision, {}, outcome_earned)
    assert res_earned["is_lucky_win"] is False
    assert res_earned["confidence_adjustment"] == 10.0
    assert "Earned Success" in res_earned["evaluation"]

    # Case B: Lucky Win (Extreme adverse excursion compared to favorable excursion)
    outcome_lucky = {
        "final_result": "SUCCESS",
        "max_favorable_excursion": 15.0,
        "max_adverse_excursion": -14.0  # Trailed close to stop loss boundary
    }
    res_lucky = judge.evaluate_decision_outcome(decision, {}, outcome_lucky)
    assert res_lucky["is_lucky_win"] is True
    assert res_lucky["confidence_adjustment"] == -15.0
    assert "Lucky Win" in res_lucky["evaluation"]

    # Verify original decision is completely untouched
    assert decision.price == 1800.0
    assert decision.symbol == "XAUUSD"


def test_intelligence_integrity_layer_future_leakage_and_missing_evidence():
    """Verify that IntelligenceIntegrityService flags and invalidates future look-ahead leaks and missing evidence."""
    service = IntelligenceIntegrityService()

    base_time = datetime(2026, 1, 1, 12, 0)
    decision = SimulatedDecision(
        timestamp=base_time,
        symbol="XAUUSD",
        price=1800.0,
        decision_action="BUY",
        context={"confidence_score": 0.80}
    )

    # Case A: Future Leakage (Evidence timestamp is ahead of decision time)
    future_pattern = PatternMemory(
        pattern_id="pat-future-1",
        sequence_signature=[1.0, 1.0],
        occurrences_count=5,
        continuation_count=4,
        reversal_count=1,
        created_at=base_time + timedelta(minutes=10)  # Future!
    )

    res_leak = service.check_decision_integrity(decision, [(future_pattern, 0.95)], [])
    assert res_leak["is_valid"] is False
    assert any("Future Leakage" in w for w in res_leak["warnings"])

    # Case B: Missing Evidence (Active decision without any matched patterns)
    res_missing = service.check_decision_integrity(decision, [], [])
    assert res_missing["is_valid"] is False
    assert any("Missing Evidence" in w for w in res_missing["warnings"])


def test_intelligence_integrity_layer_confidence_inflation_and_sample_size():
    """Verify that IntelligenceIntegrityService flags confidence inflation and unsupported sample-size conclusions."""
    service = IntelligenceIntegrityService()

    base_time = datetime(2026, 1, 1, 12, 0)

    # Case A: Confidence Inflation (> 95%)
    decision_inflated = SimulatedDecision(
        timestamp=base_time,
        symbol="XAUUSD",
        price=1800.0,
        decision_action="BUY",
        context={"confidence_score": 0.98}  # Artificially inflated
    )
    pat = PatternMemory(
        pattern_id="pat-ok",
        sequence_signature=[1.0, 1.0],
        occurrences_count=5,
        continuation_count=4,
        reversal_count=1,
        created_at=base_time - timedelta(minutes=10)
    )

    res_inflated = service.check_decision_integrity(decision_inflated, [(pat, 0.95)], [])
    assert res_inflated["integrity_score"] < 1.0
    assert any("Confidence Inflation" in w for w in res_inflated["warnings"])

    # Case B: Unsupported Conclusion (High confidence score on extremely tiny matched sample occurrences)
    decision_weak_sample = SimulatedDecision(
        timestamp=base_time,
        symbol="XAUUSD",
        price=1800.0,
        decision_action="BUY",
        context={"confidence_score": 0.90}  # High confidence
    )
    pat_weak = PatternMemory(
        pattern_id="pat-weak",
        sequence_signature=[1.0, 1.0],
        occurrences_count=1,  # Only seen once!
        continuation_count=1,
        reversal_count=0,
        created_at=base_time - timedelta(minutes=10)
    )

    res_weak = service.check_decision_integrity(decision_weak_sample, [(pat_weak, 0.95)], [])
    assert res_weak["integrity_score"] < 1.0
    assert any("Unsupported Conclusion" in w for w in res_weak["warnings"])


def test_knowledge_query_interface_strict_read_only_isolation():
    """Verify that KnowledgeQueryInterface provides comprehensive read-only views and cannot mutate memory states."""
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    query_interface = KnowledgeQueryInterface(memory_system)

    # Seed initial test data
    evt = MarketEvent(
        symbol="XAUUSD", timeframe="H1", start_time=datetime(2026, 1, 1, 12, 0), end_time=datetime(2026, 1, 1, 13, 0),
        price_change=10.0, duration_candles=1, previous_sequence_len=0, reaction_type="retracement", reaction_magnitude=-2.0
    )
    memory_system.add_event(evt)

    pat = PatternMemory(
        pattern_id="pat-query-1", sequence_signature=[1.0, 0.5], occurrences_count=4,
        continuation_count=3, reversal_count=1, outcomes=[], created_at=datetime.now()
    )
    memory_system.add_pattern(pat)

    # Query recent events
    recent = query_interface.query_recent_events(limit=5)
    assert len(recent) == 1
    assert recent[0]["price_change"] == 10.0

    # Query patterns by similarity
    similar = query_interface.query_patterns_by_similarity(target_signature=[1.0, 0.5])
    assert len(similar) == 1
    assert similar[0]["similarity_score"] == 1.0
    assert similar[0]["pattern"]["pattern_id"] == "pat-query-1"

    # Query scorecard
    scorecard = query_interface.query_learning_scorecard()
    assert scorecard["total_events_chronicled"] == 1
    assert scorecard["total_patterns_discovered"] == 1
    assert scorecard["status"] == "Healthy / Isolated"

    # Confirm query interface exposes no write methods
    for attr_name in dir(query_interface):
        assert not attr_name.startswith("add_")
        assert not attr_name.startswith("save_")
        assert not attr_name.startswith("delete_")
        assert not attr_name.startswith("update_")


def test_memory_snapshot_and_emergency_recovery():
    """Verify memory snapshotting, restore snapshot, latest tag detection, and emergency recovery."""
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)

    # Seed initial test data
    evt = MarketEvent(
        symbol="XAUUSD", timeframe="H1", start_time=datetime(2026, 1, 1, 12, 0), end_time=datetime(2026, 1, 1, 13, 0),
        price_change=15.0, duration_candles=1, previous_sequence_len=0, reaction_type="reversal", reaction_magnitude=-5.0
    )
    memory_system.add_event(evt)
    assert len(memory_system.get_events()) == 1

    # 1. Create a Snapshot
    tag = "v2-backup-test"
    snapshot_meta = memory_system.create_snapshot(tag)
    assert snapshot_meta["backup_tag"] == tag
    assert "events" in snapshot_meta["files"]

    # 2. Check latest snapshot detection
    latest_tag = memory_system.get_latest_snapshot_tag()
    assert latest_tag == tag

    # 3. Add more events, then restore and confirm rollback
    evt2 = MarketEvent(
        symbol="XAUUSD", timeframe="H1", start_time=datetime(2026, 1, 1, 14, 0), end_time=datetime(2026, 1, 1, 15, 0),
        price_change=25.0, duration_candles=1, previous_sequence_len=1, reaction_type="reversal", reaction_magnitude=-2.0
    )
    memory_system.add_event(evt2)
    assert len(memory_system.get_events()) == 2

    # Restore snapshot
    restored = memory_system.restore_snapshot(tag)
    assert restored is True
    # Confirm rolled back to 1 event
    assert len(memory_system.get_events()) == 1

    # 4. Trigger Automatic Emergency Recovery
    # Corrupt the events JSON file
    events_file = memory_system._get_path("events")
    with open(events_file, "w", encoding="utf-8") as f:
        f.write("{invalid_json: true, ...}")  # Corrupted data!

    # Calling load_all should detect corruption and recover from the latest snapshot
    memory_system.load_all()
    # Confirm loaded 1 event successfully recovered from snapshot!
    assert len(memory_system.get_events()) == 1


def test_statistical_validation_engine():
    """Verify Phase 5 statistical validation rules, including sample size, walk-forward, and overfitting."""
    from src.Research.Brain.quality_control import StatisticalValidationEngine

    engine = StatisticalValidationEngine(min_sample_size=5, tolerance_pct=15.0)

    # 1. Minimum Sample Size Rules
    pat_insufficient = PatternMemory(
        pattern_id="pat-1", sequence_signature=[1.0, -1.0], occurrences_count=3,
        continuation_count=2, reversal_count=1, outcomes=[], created_at=datetime.now()
    )
    assert engine.validate_pattern_sample_size(pat_insufficient) == "INSUFFICIENT_SAMPLE"

    pat_sufficient = PatternMemory(
        pattern_id="pat-2", sequence_signature=[1.0, -1.0], occurrences_count=8,
        continuation_count=5, reversal_count=3, outcomes=[], created_at=datetime.now()
    )
    assert engine.validate_pattern_sample_size(pat_sufficient) == "SUFFICIENT_SAMPLE"

    # 2. Walk-forward Chronological Out-of-sample validation
    hist_outcomes = [{"is_continuation": True}, {"is_continuation": True}, {"is_continuation": False}] # 2/3 = 66.6%
    oos_outcomes_passed = [{"is_continuation": True}, {"is_continuation": True}] # 100% (divergence = 33.3% > 15% -> UNRELIABLE)
    oos_outcomes_failed = [{"is_continuation": False}, {"is_continuation": False}] # 0% (divergence = 66.6% > 15% -> UNRELIABLE)

    # Test passed with low divergence
    oos_passed_close = [{"is_continuation": True}, {"is_continuation": False}] # 50% (divergence = 16.6% > 15% -> UNRELIABLE)
    oos_passed_ideal = [{"is_continuation": True}, {"is_continuation": True}, {"is_continuation": False}] # 66.6% (divergence = 0.0% -> PASSED)

    res_passed = engine.perform_walk_forward_validation(hist_outcomes, oos_passed_ideal)
    assert res_passed["status"] == "PASSED"
    assert res_passed["divergence_pct"] == 0.0

    res_failed = engine.perform_walk_forward_validation(hist_outcomes, oos_outcomes_failed)
    assert res_failed["status"] == "UNRELIABLE_CONFIDENCE"
    assert res_failed["divergence_pct"] > 15.0

    # 3. Single-symbol Overfitting / Sensitivity check on XAUUSD
    # Overfit pattern with zero variance
    pat_overfit_static = PatternMemory(
        pattern_id="pat-static", sequence_signature=[1.0, 1.0, 1.0], occurrences_count=5,
        continuation_count=4, reversal_count=1, outcomes=[], created_at=datetime.now()
    )
    res_static = engine.check_overfitting_sensitivity(pat_overfit_static)
    assert res_static["is_overfit"] is True
    assert "Zero variance/Static signature" in res_static["reasons"]

    # Overfit pattern with high unidirectional outcomes on tiny sample size
    pat_overfit_unidir = PatternMemory(
        pattern_id="pat-unidir", sequence_signature=[1.0, -0.5, 0.2], occurrences_count=4,
        continuation_count=4, reversal_count=0, outcomes=[], created_at=datetime.now()
    )
    res_unidir = engine.check_overfitting_sensitivity(pat_overfit_unidir)
    assert res_unidir["is_overfit"] is True
    assert "Unidirectional outcomes on small sample" in res_unidir["reasons"]
