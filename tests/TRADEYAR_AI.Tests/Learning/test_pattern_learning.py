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


def test_experience_to_pattern_to_concept_pipeline(temp_memory_system):
    """Verifies that validated experiences promote to patterns and consolidate to concepts."""
    mem_sys = temp_memory_system

    # Create 5 identical experiences to satisfy the pattern and concept threshold criteria
    for i in range(5):
        exp = ExperienceMemory(
            experience_id=f"exp-prom-{i}",
            symbol="XAUUSD",
            timeframe="H1",
            timestamp=datetime.now(),
            situation_signature=[0.5, 0.5, 0.5, 0.5],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Strong bullish consolidation",
            max_favorable_excursion=20.0,
            max_adverse_excursion=-2.0,
            meta={"is_validated": True}
        )
        mem_sys.add_experience(exp)

    # Run the promotion pipeline
    patterns = mem_sys.promote_experiences_to_patterns()
    assert len(patterns) > 0

    # Confirm pattern count and outcomes are stored
    pats_list = mem_sys.get_patterns()
    assert len(pats_list) > 0
    best_pat = pats_list[0]
    assert best_pat.occurrences_count >= 5
    assert best_pat.continuation_count >= 5

    # Run consolidation to concepts
    concepts = mem_sys.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70)
    assert len(concepts) > 0
    assert concepts[0].is_approved is True
    assert concepts[0].sample_count >= 5
