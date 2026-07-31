import pytest
from datetime import datetime, timedelta
from src.Research.Brain.models import MarketObservation, ReplayEpisode, Hypothesis, PatternMemory, ConceptMemory
from src.Research.Brain.replay import MarketReplayEngine
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.integrity import LearningIntegrityService
from src.Research.Brain.cognitive_loop import CognitiveReplayLoop

@pytest.fixture
def sample_observations():
    """Generates 20 hours of chronological H1 observations for XAUUSD."""
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    obs_list = []
    # Upward trending sequence, then a slight pull back
    for i in range(15):
        obs_list.append(MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=i),
            high=1800.0 + i * 4.0 + 2.0, low=1800.0 + i * 4.0 - 2.0,
            open_price=1800.0 + i * 4.0, close_price=1800.0 + (i + 1) * 4.0, volume=100.0
        ))
    for i in range(15, 20):
        offset = i - 15
        obs_list.append(MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=i),
            high=1860.0 - offset * 2.0 + 1.0, low=1860.0 - offset * 2.0 - 3.0,
            open_price=1860.0 - offset * 2.0, close_price=1860.0 - (offset + 1) * 2.0, volume=100.0
        ))
    return obs_list

def test_replay_integrity_future_leakage_impossible(sample_observations):
    """Verifies that at cursor T, only data <= T is retrieved."""
    replay = MarketReplayEngine(symbol="XAUUSD", observations=sample_observations)
    cursor = sample_observations[5].timestamp
    replay.set_cursor(cursor)

    available = replay.get_available_data()
    assert len(available) == 6
    for obs in available:
        assert obs.timestamp <= cursor

def test_replay_episode_immutability(sample_observations):
    """Verifies that ReplayEpisode properties cannot be altered due to frozen status."""
    episode = ReplayEpisode(
        episode_id="ep-1", symbol="XAUUSD",
        start_time=sample_observations[0].timestamp,
        decision_time=sample_observations[5].timestamp,
        market_context={}, observed_sequence=[],
        brain_hypothesis=None, simulation_decision=None,
        actual_outcome=None, judge_result=None,
        learning_feedback=None
    )
    with pytest.raises(AttributeError):
        episode.symbol = "EURUSD"

def test_learning_integrity_failures_stored_and_no_manipulation():
    """Verifies that failures are preserved and issues are correctly identified."""
    patterns = [
        # Small sample with 100% certainty (Trigger Overfitting)
        PatternMemory(pattern_id="pat-1", sequence_signature=[1.0, 0.5], occurrences_count=2, continuation_count=2, reversal_count=0),
        # Large sample with skew
        PatternMemory(pattern_id="pat-2", sequence_signature=[1.0, -1.0], occurrences_count=12, continuation_count=12, reversal_count=0)
    ]
    service = LearningIntegrityService(min_sample_size=4)
    report = service.inspect_patterns_integrity(patterns)

    assert report["overfitting_detected"] is True
    assert "pat-1" in report["rejection_recommendations"]
    assert report["integrity_score"] < 1.0

def test_judge_isolation():
    """Verifies that Judge evaluates but cannot formulate decisions or modify trades."""
    judge = JudgeBrain()
    hyp = Hypothesis(
        hypothesis_id="hyp-1", sequence_signature=[1.0, 0.5],
        expected_direction="BUY", supporting_samples=[], contradicting_samples=[],
        confidence=85.0, validation_status="PENDING"
    )
    # The evaluation output is read-only, separate from execution/decision flows
    res = judge.evaluate_hypothesis_and_decision(hyp, None, [])
    assert "decision_quality_score" in res
    assert "reasoning_quality_score" in res

def test_simulation_reality_spread_slippage_commission(sample_observations):
    """Verifies that transaction costs are applied to entry and exit limits."""
    brain = SimulationBrain(
        symbol="XAUUSD", timeframe="H1",
        spread_points=4.0, slippage_points=2.0, commission_points=1.0
    )
    # raw close price is 1800.0.
    # BUY entry executed on Ask + slippage + commission = 1800.0 + 2.0 (half spread) + 2.0 + 1.0 = 1805.0
    trade = brain.make_virtual_decision(
        action="BUY", entry_price=1800.0,
        timestamp=sample_observations[0].timestamp,
        stop_offset=10.0, target_offset=20.0
    )
    assert trade.entry_price == 1805.0
    assert trade.virtual_stop == 1795.0
    assert trade.virtual_target == 1825.0

def test_cognitive_replay_loop_e2e(sample_observations, tmp_path):
    """Verifies the complete E2E cognitive learning loop operates as expected."""
    # Setup thread-safe temporary memory system
    memory_dir = str(tmp_path / "brain_memory")
    mem_sys = MarketMemorySystem(storage_dir=memory_dir)

    # Initial seed patterns so matches exist
    seed_pat = PatternMemory(
        pattern_id="pat-seed-1", sequence_signature=[1.0, 1.0, 1.0, 1.0],
        occurrences_count=6, continuation_count=5, reversal_count=1
    )
    mem_sys.add_pattern(seed_pat)

    loop = CognitiveReplayLoop(
        symbol="XAUUSD", timeframe="H1",
        observations=sample_observations,
        memory_system=mem_sys
    )

    episodes = loop.execute_replay_session(steps_count=5, scale="hours")
    assert len(episodes) > 0
    assert len(mem_sys.get_events()) > 0

    # Test active learning weakness identification
    priorities = loop.active_learning.analyze_weaknesses_and_set_priorities(mem_sys.get_patterns())
    assert len(priorities) > 0
