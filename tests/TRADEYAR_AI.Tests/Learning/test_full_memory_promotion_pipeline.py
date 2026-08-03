import os
import shutil
import tempfile
import pytest
from datetime import datetime, timedelta
from src.Research.Brain.models import MarketEvent, ExperienceMemory
from src.Research.Brain.memory import MarketMemorySystem

@pytest.fixture
def temp_memory_system():
    temp_dir = tempfile.mkdtemp()
    mem_sys = MarketMemorySystem(storage_dir=temp_dir)
    yield mem_sys
    shutil.rmtree(temp_dir)

def test_full_memory_promotion_pipeline_e2e(temp_memory_system):
    """
    Tests the complete end-to-end mathematical promotion pipeline across all 4 layers:
    Raw Event (L1) -> Experience (L2) -> Pattern (L3) -> Approved Concept (L4).
    """
    mem_sys = temp_memory_system

    # 1. LAYER 1: Raw Event creation
    raw_event = MarketEvent(
        symbol="XAUUSD",
        timeframe="H1",
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        price_change=25.0,
        duration_candles=4,
        previous_sequence_len=0,
        reaction_type="extension",
        reaction_magnitude=10.0,
        meta={}
    )
    mem_sys.add_event(raw_event)
    assert len(mem_sys.get_events()) == 1

    # 2. PROMOTION L1 -> L2: Raw Event to Experience Memory
    promoted_exps = mem_sys.promote_raw_events_to_experiences(symbol="XAUUSD", timeframe="H1")
    assert len(promoted_exps) == 1
    assert len(mem_sys.get_experiences()) == 1

    exp = promoted_exps[0]
    assert exp.symbol == "XAUUSD"
    assert exp.timeframe == "H1"
    assert exp.outcome_result == "SUCCESS"  # mapped from reaction_type = extension
    assert exp.situation_signature == [25.0, 4.0, 10.0]

    # Confirm raw event is linked and marked as promoted
    assert mem_sys.get_events()[0].meta["is_promoted_to_experience"] is True

    # 3. PROMOTION L2 -> L3: Experience Memory to Pattern Memory
    # Set judge score meta to simulate Judge Vetting
    exp.meta["judge_reasoning_score"] = 0.90
    exp.meta["judge_accuracy"] = 0.85
    exp.meta["is_validated"] = True
    mem_sys.add_experience(exp)

    promoted_patterns = mem_sys.promote_experiences_to_patterns()
    assert len(promoted_patterns) == 1
    assert len(mem_sys.get_patterns()) == 1

    pat = promoted_patterns[0]
    assert pat.occurrences_count == 1
    assert pat.continuation_count == 1
    assert pat.reversal_count == 0
    assert pat.sequence_signature == [25.0, 4.0, 10.0]

    # Assert confidence decay weights and judge metrics were appended in outcome
    outcome = pat.outcomes[0]
    assert "adjusted_confidence" in outcome
    assert outcome["judge_vetted_accuracy"] == 0.85

    # 4. PROMOTION L3 -> L4: Pattern Memory to Concept Memory
    # We consolidate patterns with min_samples=1 to trigger promotion immediately
    concepts = mem_sys.consolidate_patterns_to_concepts(min_samples=1, min_validation_score=0.70)
    assert len(concepts) == 1
    assert len(mem_sys.get_concepts()) == 1

    concept = concepts[0]
    assert concept.is_approved is True
    assert concept.sample_count == 1
    # validation_score = consistency * avg_vetted_accuracy = 1.0 * 0.85 = 0.85
    assert concept.validation_score == 0.85
    assert concept.meta["original_pattern_id"] == pat.pattern_id
