import os
import shutil
import tempfile
import pytest
from datetime import datetime
from src.Research.Brain.models import ExperienceMemory
from src.Research.Brain.memory import MarketMemorySystem


@pytest.fixture
def temp_memory_system():
    # Setup temporary directory for test storage
    temp_dir = tempfile.mkdtemp()
    mem_sys = MarketMemorySystem(storage_dir=temp_dir)
    yield mem_sys
    # Teardown
    shutil.rmtree(temp_dir)


def test_experience_validation_lifecycle(temp_memory_system):
    """Verifies raw experience is added as pending and successfully validated."""
    mem_sys = temp_memory_system

    # Create mock experience memory record
    exp = ExperienceMemory(
        experience_id="exp-001",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=datetime.now(),
        situation_signature=[1.0, 0.5, -0.5, 0.2, 0.1],
        decision_action="BUY",
        outcome_result="SUCCESS",
        lesson_feedback="Pattern matched London Open continuation",
        max_favorable_excursion=15.0,
        max_adverse_excursion=-5.0,
        meta={}
    )

    mem_sys.add_experience(exp)

    # Initial state should not be validated
    retrieved = mem_sys.experiences["exp-001"]
    assert "is_validated" not in retrieved.meta

    # Validate the experience
    success = mem_sys.validate_experience("exp-001")
    assert success is True

    # Validate result persistence
    assert retrieved.meta["is_validated"] is True

    # Try validating non-existent experience
    assert mem_sys.validate_experience("invalid-id") is False


def test_experience_deduplication_and_governance(temp_memory_system):
    """Verifies that duplicate experiences are ignored to prevent learning weight inflation and pruning works."""
    mem_sys = temp_memory_system
    now = datetime(2026, 1, 1, 12, 0, 0)

    exp1 = ExperienceMemory(
        experience_id="exp-unique-1",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now,
        situation_signature=[1.0, 0.5, -0.5, 0.2, 0.1],
        decision_action="BUY",
        outcome_result="SUCCESS",
        lesson_feedback="Valid London Open",
        max_favorable_excursion=15.0,
        max_adverse_excursion=-5.0,
        meta={}
    )

    # Identical business attributes but different ID (the "duplicate")
    exp2 = ExperienceMemory(
        experience_id="exp-duplicate-2",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now,
        situation_signature=[1.0, 0.5, -0.5, 0.2, 0.1],
        decision_action="BUY",
        outcome_result="SUCCESS",
        lesson_feedback="Duplicate London Open",
        max_favorable_excursion=15.0,
        max_adverse_excursion=-5.0,
        meta={}
    )

    mem_sys.add_experience(exp1)
    mem_sys.add_experience(exp2)

    # Assert that only exp1 resides in the memory system (exp2 ignored/deduplicated)
    assert len(mem_sys.get_experiences()) == 1
    assert "exp-unique-1" in mem_sys.experiences
    assert "exp-duplicate-2" not in mem_sys.experiences

    # Verify memory weight is not inflated
    weight = mem_sys.calculate_experience_weight("exp-unique-1", now)
    assert weight > 0.0

    # Verify memory pruning (Prune experiences or patterns with bad parameters)
    # 1. Seed a bad pattern
    from src.Research.Brain.models import PatternMemory
    bad_pat = PatternMemory(
        pattern_id="pat-bad",
        sequence_signature=[0.1, -0.1],
        occurrences_count=10,
        continuation_count=1, # 1/10 = 10% accuracy!
        reversal_count=9
    )
    mem_sys.add_pattern(bad_pat)
    assert len(mem_sys.get_patterns()) == 1

    # Seed an experience representing a failure to prune
    exp_fail = ExperienceMemory(
        experience_id="exp-fail-1",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now,
        situation_signature=[0.1, -0.1],
        decision_action="SELL",
        outcome_result="FAILURE",
        lesson_feedback="Mistake lesson",
        max_favorable_excursion=0.0,
        max_adverse_excursion=-20.0,
        meta={}
    )
    mem_sys.add_experience(exp_fail)
    assert len(mem_sys.get_experiences()) == 2

    # Prune! Patterns with accuracy < 50% will be pruned
    pruning_stats = mem_sys.prune_unreliable_memories(min_accuracy=0.50)
    assert pruning_stats["pruned_patterns"] == 1
    assert pruning_stats["pruned_experiences"] == 1
    assert len(mem_sys.get_patterns()) == 0
    assert len(mem_sys.get_experiences()) == 1 # only exp1 remains!
