import pytest
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.Research.Brain.models import MarketObservation, ReplayEpisode, Hypothesis, PatternMemory, ExperienceMemory, ConceptMemory, VirtualTrade
from src.Research.Brain.replay import MarketReplayEngine
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.integrity import LearningIntegrityService

TEST_STORAGE_DIR = os.path.join("runtime_logs", "test_cognitive_challenges_memory")

@pytest.fixture(autouse=True)
def clean_test_storage():
    """Ensures test storage is cleared before and after each test."""
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)
    yield
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)


class BrainSelfCriticism:
    """
    Self-Criticism Query Interface.
    Answers the four test questions purely from actual memory data
    (ExperienceMemory, PatternMemory, Judge results). No generic AI text.
    """
    def __init__(self, memory_system: MarketMemorySystem) -> None:
        self.memory_system = memory_system

    def get_biggest_repeated_mistakes(self) -> List[Dict[str, Any]]:
        """Question 1: What are your biggest repeated mistakes?"""
        experiences = self.memory_system.get_experiences()
        failures = [e for e in experiences if e.outcome_result == "FAILURE"]

        mistakes = []
        for f in failures:
            mistakes.append({
                "experience_id": f.experience_id,
                "lesson_learned": f.lesson_feedback,
                "max_adverse_excursion": f.max_adverse_excursion,
                "situation_signature": f.situation_signature
            })
        return mistakes

    def get_uncertain_concepts(self) -> List[Dict[str, Any]]:
        """Question 2: Which concepts are still uncertain?"""
        patterns = self.memory_system.get_patterns()
        uncertain = []
        for p in patterns:
            total = p.occurrences_count
            if total >= 3:  # Only count well-vetted patterns to avoid small-sample confusion
                cont_pct = (p.continuation_count / total) * 100.0
                # Split near 50/50 indicates high uncertainty
                if 40.0 <= cont_pct <= 60.0:
                    uncertain.append({
                        "pattern_id": p.pattern_id,
                        "occurrences": total,
                        "continuation_pct": cont_pct,
                        "signature": p.sequence_signature
                    })
        return uncertain

    def get_failed_hypotheses_reasons(self) -> List[Dict[str, Any]]:
        """Question 3: Which hypotheses failed and why?"""
        experiences = self.memory_system.get_experiences()
        failures = [e for e in experiences if e.outcome_result == "FAILURE"]

        failed_reasons = []
        for f in failures:
            failed_reasons.append({
                "experience_id": f.experience_id,
                "expected_direction": f.decision_action,
                "lesson": f.lesson_feedback,
                "timestamp": f.timestamp.isoformat()
            })
        return failed_reasons

    def get_needed_observation_areas(self) -> List[Dict[str, Any]]:
        """Question 4: Where do you need more observation?"""
        # Patterns with very low samples are areas that need more observation
        patterns = self.memory_system.get_patterns()
        needed = []
        for p in patterns:
            if p.occurrences_count < 3:
                needed.append({
                    "pattern_id": p.pattern_id,
                    "occurrences": p.occurrences_count,
                    "signature": p.sequence_signature
                })
        return needed


# -----------------------------------------------------------------------------
# 1. Blind Replay Challenge Test
# -----------------------------------------------------------------------------
def test_blind_replay_challenge_leakage_prevention():
    """
    Goal: Prove that the Market Discovery Brain cannot access future information during replay decisions.
    """
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    observations = [
        MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=i),
            high=1800.0 + i * 2.0, low=1795.0 + i * 2.0, open_price=1798.0 + i * 2.0,
            close_price=1800.0 + i * 2.0, volume=100.0
        )
        for i in range(20)
    ]

    replay = MarketReplayEngine(symbol="XAUUSD", observations=observations)

    # Freeze the decision point at step 5
    decision_step = 5
    decision_time = observations[decision_step].timestamp
    replay.set_cursor(decision_time)

    # Verify that only historical data up to decision timestamp is available
    available = replay.get_available_data()
    assert len(available) == decision_step + 1

    for obs in available:
        assert obs.timestamp <= decision_time

    # Verify that any timestamps after decision_time are strictly inaccessible
    post_decision_data = [o for o in observations if o.timestamp > decision_time]
    assert len(post_decision_data) > 0

    for post_obs in post_decision_data:
        assert post_obs not in available


# -----------------------------------------------------------------------------
# 2. Wrong Hypothesis Challenge Test
# -----------------------------------------------------------------------------
def test_wrong_hypothesis_challenge_rejection():
    """
    Goal: Verify that the system can reject incorrect understanding.
    """
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    discovery = PatternDiscoveryEngine()
    hyp_engine = HypothesisEngine(discovery)
    judge = JudgeBrain()

    # Create an intentionally incorrect/weak pattern with highly contradictory historical outcomes (50/50 split)
    wrong_pattern = PatternMemory(
        pattern_id="pat-wrong-1",
        sequence_signature=[1.0, -1.0, 1.0],
        occurrences_count=10,
        continuation_count=5,  # 50% split -> Highly uncertain / unreliable
        reversal_count=5
    )
    memory_system.add_pattern(wrong_pattern)

    # Formulate hypothesis on this weak/incorrect pattern
    sig = [1.0, -1.0, 1.0]
    hypothesis = hyp_engine.formulate_hypothesis(sig, memory_system.get_patterns())

    # Create a virtual trade that results in failure (Stop Loss hit)
    virtual_trade = VirtualTrade(
        trade_id="vtrade-wrong-1",
        symbol="XAUUSD",
        timeframe="H1",
        entry_time=datetime.now(),
        entry_price=1800.0,
        decision_action="BUY",
        virtual_stop=1790.0,
        virtual_target=1820.0,
        expected_scenario="Continuation",
        status="CLOSED",
        exit_time=datetime.now() + timedelta(hours=1),
        exit_price=1790.0,
        max_favorable_movement=2.0,
        max_adverse_movement=-10.0,
        final_result="FAILURE",
        reason_of_failure="Stop loss breach."
    )

    # Evaluate via Judge Brain
    judge_evaluation = judge.evaluate_hypothesis_and_decision(hypothesis, virtual_trade, [])

    # The judge must recognize this low decision and reasoning quality
    assert judge_evaluation["decision_quality_score"] <= 0.4
    assert "Hypothesis failed" in judge_evaluation["learning_feedback"]

    # Save as a completed Experience Memory to keep as a learning lesson
    exp = ExperienceMemory(
        experience_id=f"exp-{uuid.uuid4().hex[:8]}",
        symbol="XAUUSD",
        timeframe="H1",
        timestamp=datetime.now(),
        situation_signature=sig,
        decision_action="BUY",
        outcome_result="FAILURE",
        lesson_feedback=judge_evaluation["learning_feedback"],
        max_favorable_excursion=2.0,
        max_adverse_excursion=-10.0
    )
    memory_system.add_experience(exp)

    # Attempt memory consolidation. Enforce a minimum validation score of 0.75 and sample occurrences >= 4.
    # The contradictory wrong pattern has continuation=5, reversal=5 (ratio = 0.50), which fails the 0.75 threshold.
    consolidated = memory_system.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.75)

    # Verify that the wrong concept is rejected and NOT promoted to Concept Memory
    assert len(consolidated) == 0
    assert len(memory_system.get_concepts()) == 0

    # But verify that the failed hypothesis remains stored in Experience Memory for self-criticism lessons
    assert len(memory_system.get_experiences()) == 1
    assert memory_system.get_experiences()[0].outcome_result == "FAILURE"


# -----------------------------------------------------------------------------
# 3. Self-Criticism Intelligence Test
# -----------------------------------------------------------------------------
def test_self_criticism_intelligence_and_limitations():
    """
    Goal: Verify that the brain can identify its own limitations.
    """
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)

    # Seed failure experiences
    exp_fail = ExperienceMemory(
        experience_id="exp-fail-1", symbol="XAUUSD", timeframe="H1", timestamp=datetime.now(),
        situation_signature=[1.0, -1.0, 1.0], decision_action="BUY", outcome_result="FAILURE",
        lesson_feedback="Failed because of wide spread and low-volume consolidation.",
        max_favorable_excursion=2.0, max_adverse_excursion=-12.0
    )
    memory_system.add_experience(exp_fail)

    # Seed uncertain patterns (50/50 split)
    pat_uncertain = PatternMemory(
        pattern_id="pat-unc-1", sequence_signature=[1.0, 0.0, -1.0], occurrences_count=8,
        continuation_count=4, reversal_count=4
    )
    memory_system.add_pattern(pat_uncertain)

    # Seed under-represented patterns (low sample count < 3)
    pat_low_sample = PatternMemory(
        pattern_id="pat-low-1", sequence_signature=[-1.0, -1.0, 1.0], occurrences_count=2,
        continuation_count=1, reversal_count=1
    )
    memory_system.add_pattern(pat_low_sample)

    critic = BrainSelfCriticism(memory_system)

    # Question 1: What are your biggest repeated mistakes?
    mistakes = critic.get_biggest_repeated_mistakes()
    assert len(mistakes) == 1
    assert mistakes[0]["experience_id"] == "exp-fail-1"
    assert "wide spread" in mistakes[0]["lesson_learned"]

    # Question 2: Which concepts are still uncertain?
    uncertain = critic.get_uncertain_concepts()
    assert len(uncertain) == 1
    assert uncertain[0]["pattern_id"] == "pat-unc-1"
    assert uncertain[0]["continuation_pct"] == 50.0

    # Question 3: Which hypotheses failed and why?
    failed = critic.get_failed_hypotheses_reasons()
    assert len(failed) == 1
    assert failed[0]["experience_id"] == "exp-fail-1"
    assert failed[0]["expected_direction"] == "BUY"
    assert "low-volume" in failed[0]["lesson"]

    # Question 4: Where do you need more observation?
    needed = critic.get_needed_observation_areas()
    assert len(needed) == 1
    assert needed[0]["pattern_id"] == "pat-low-1"
    assert needed[0]["occurrences"] == 2


# -----------------------------------------------------------------------------
# Additional verifications
# -----------------------------------------------------------------------------
def test_additional_isolation_and_safety_checks():
    """
    Verifies isolation, read-only guarantees, and safety metrics.
    """
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    sim = SimulationBrain(symbol="XAUUSD", timeframe="H1")
    judge = JudgeBrain()

    # Confirm Judge Brain remains independent from Simulation Brain (no references or ability to create decisions)
    assert not hasattr(judge, "make_virtual_decision")
    assert not hasattr(judge, "active_trades")

    # Verify Learning Engine cannot modify knowledge without validation
    # promoting requires a minimum occurrence sample size of 5 and min score of 0.75
    pat_unv = PatternMemory(
        pattern_id="pat-unv-1", sequence_signature=[1.0, 1.0], occurrences_count=2,
        continuation_count=2, reversal_count=0
    )
    memory_system.add_pattern(pat_unv)

    consolidated = memory_system.consolidate_patterns_to_concepts(min_samples=5, min_validation_score=0.75)
    assert len(consolidated) == 0  # Ignored due to insufficient samples
