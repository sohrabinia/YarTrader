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
