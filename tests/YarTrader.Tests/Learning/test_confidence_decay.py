import os
import shutil
import tempfile
import pytest
from datetime import datetime, timedelta
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


def test_experience_forgetting_and_confidence_decay(temp_memory_system):
    """Verifies that older, unsuccessful, or less similar experiences yield lower weights."""
    mem_sys = temp_memory_system
    now = datetime.now()

    # 1. Base success experience
    exp_success = ExperienceMemory(
        experience_id="exp-success",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now,
        situation_signature=[1.0, 1.0, 1.0],
        decision_action="BUY",
        outcome_result="SUCCESS",
        lesson_feedback="N/A",
        max_favorable_excursion=10,
        max_adverse_excursion=-1,
        meta={}
    )

    # 2. Older experience (e.g. 10 days ago)
    exp_old = ExperienceMemory(
        experience_id="exp-old",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now - timedelta(days=10),
        situation_signature=[1.0, 1.0, 1.0],
        decision_action="BUY",
        outcome_result="SUCCESS",
        lesson_feedback="N/A",
        max_favorable_excursion=10,
        max_adverse_excursion=-1,
        meta={}
    )

    # 3. Failed experience
    exp_failure = ExperienceMemory(
        experience_id="exp-fail",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=now,
        situation_signature=[1.0, 1.0, 1.0],
        decision_action="BUY",
        outcome_result="FAILURE",
        lesson_feedback="N/A",
        max_favorable_excursion=1,
        max_adverse_excursion=-10,
        meta={}
    )

    mem_sys.add_experience(exp_success)
    mem_sys.add_experience(exp_old)
    mem_sys.add_experience(exp_failure)

    # Weight of fresh success experience should be higher than old experience
    w_success = mem_sys.calculate_experience_weight("exp-success", now, reference_signature=[1.0, 1.0, 1.0])
    w_old = mem_sys.calculate_experience_weight("exp-old", now, reference_signature=[1.0, 1.0, 1.0])
    assert w_success > w_old

    # Weight of fresh success should be higher than fresh failure
    w_fail = mem_sys.calculate_experience_weight("exp-fail", now, reference_signature=[1.0, 1.0, 1.0])
    assert w_success > w_fail

    # Weight with perfect matching signature should be higher than non-matching signature
    w_no_match = mem_sys.calculate_experience_weight("exp-success", now, reference_signature=[-1.0, -1.0, -1.0])
    assert w_success > w_no_match
