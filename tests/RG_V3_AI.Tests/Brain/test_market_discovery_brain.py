import os
import shutil
from datetime import datetime, timedelta
import pytest
from src.Research.Brain.models import (
    MarketObservation, MarketEvent, PatternMemory, ExperienceMemory, VirtualTrade
)
from src.Research.Brain.data_reality import DataRealityLayer
from src.Research.Brain.observation import ObservationBrain
from src.Research.Brain.multi_timeframe import MultiTimeframePerception
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.evaluation import OutcomeEvaluationEngine
from src.Research.Brain.quality_control import QualityControlBrain
from src.Research.Brain.live_brain import LiveAnalysisBrain

TEST_STORAGE_DIR = os.path.join("runtime_logs", "test_brain_memory")

@pytest.fixture(autouse=True)
def clean_test_storage():
    """Ensures test storage is cleared before and after each test."""
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)
    yield
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)


def test_data_reality_layer_ingestion_and_missing_candles():
    """Tests that Data Reality Layer ingests data, supports multi-timeframe, and detects missing candles."""
    layer = DataRealityLayer(symbol="XAUUSD")

    # Create consecutive 1-hour candles
    now = datetime(2026, 1, 1, 12, 0, 0)
    raw_candles = [
        {"timestamp": now + timedelta(hours=i), "open": 1800.0 + i, "high": 1805.0 + i, "low": 1795.0 + i, "close": 1802.0 + i, "volume": 100.0}
        for i in range(5)
    ]

    # Ingest H1 candles
    ingested = layer.ingest_raw_candles("H1", raw_candles)
    assert len(ingested) == 5
    assert len(layer.get_raw_state("H1")) == 5

    # Introduce a missing candle gap (skip hour 5, ingest hour 6)
    gap_candle = {"timestamp": now + timedelta(hours=6), "open": 1806.0, "high": 1810.0, "low": 1800.0, "close": 1805.0, "volume": 100.0}
    layer.ingest_raw_candles("H1", [gap_candle])

    missing = layer.detect_missing_candles("H1")
    assert len(missing) == 1
    assert missing[0] == now + timedelta(hours=5)


def test_observation_brain_event_extraction_without_subjective_naming():
    """Tests that the Observation Brain extracts raw mathematical events with no subjective nomenclature."""
    brain = ObservationBrain(symbol="XAUUSD", timeframe="H1")

    # Construct consecutive candles to simulate a specific sequence movement
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    observations = [
        # 5 consecutive bullish candles (price moves upward)
        MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=i),
            high=1800 + i * 5 + 2, low=1800 + i * 5 - 2, open_price=1800 + i * 5, close_price=1800 + (i + 1) * 5, volume=100.0
        )
        for i in range(5)
    ]

    # Add reaction candles (retracement of 2 bearish candles)
    observations.extend([
        MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=5),
            high=1826.0, low=1820.0, open_price=1825.0, close_price=1822.0, volume=100.0
        ),
        MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=6),
            high=1823.0, low=1815.0, open_price=1822.0, close_price=1818.0, volume=100.0
        )
    ])

    sequence = brain.process_observations(observations)
    assert len(sequence.events) > 0

    first_event = sequence.events[0]
    desc = brain.generate_raw_description(first_event)

    # Confirm no subjective words are used in the raw description
    for forbidden in ["breakout", "trend", "resistance", "support", "bullish", "bearish"]:
        assert forbidden not in desc.lower()


def test_multi_timeframe_fractal_containment_mapping():
    """Tests mapping structural containment relationships between larger and smaller timeframe candles."""
    perception = MultiTimeframePerception(symbol="XAUUSD")

    # Generate H1 and H4 overlapping observations
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    h1_obs = [
        MarketObservation(
            symbol="XAUUSD", timeframe="H1", timestamp=base_time + timedelta(hours=i),
            high=1805.0, low=1795.0, open_price=1800.0, close_price=1802.0, volume=50.0
        )
        for i in range(4)
    ]
    h4_obs = [
        MarketObservation(
            symbol="XAUUSD", timeframe="H4", timestamp=base_time,
            high=1810.0, low=1790.0, open_price=1800.0, close_price=1804.0, volume=200.0
        )
    ]

    timeframe_data = {
        "H1": h1_obs,
        "H4": h4_obs
    }

    mappings = perception.map_fractal_relationships(timeframe_data)
    assert "H4_contains_H1" in mappings
    assert mappings["H4_contains_H1"]["mappings_count"] == 1


def test_market_memory_layer_serialization_and_persistence():
    """Tests that the Market Memory System cleanly serializes and reloads all three memory layers."""
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)

    # 1. Add Event
    evt = MarketEvent(
        symbol="XAUUSD", timeframe="H1", start_time=datetime(2026, 1, 1, 12, 0), end_time=datetime(2026, 1, 1, 13, 0),
        price_change=12.5, duration_candles=2, previous_sequence_len=0, reaction_type="retracement", reaction_magnitude=-4.0
    )
    memory_system.add_event(evt)

    # 2. Add Pattern
    pat = PatternMemory(
        pattern_id="pat-test-1", sequence_signature=[1.0, 0.5, -0.2], occurrences_count=10,
        continuation_count=7, reversal_count=3, outcomes=[], created_at=datetime.now()
    )
    memory_system.add_pattern(pat)

    # 3. Add Experience
    exp = ExperienceMemory(
        experience_id="exp-test-1", symbol="XAUUSD", timeframe="H1", timestamp=datetime.now(),
        situation_signature=[1.0, 0.5], decision_action="BUY", outcome_result="SUCCESS",
        lesson_feedback="Pattern worked well", max_favorable_excursion=20.0, max_adverse_excursion=-2.0
    )
    memory_system.add_experience(exp)

    # Re-instantiate memory system and load from disk
    new_memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    assert len(new_memory_system.get_events()) == 1
    assert len(new_memory_system.get_patterns()) == 1
    assert len(new_memory_system.get_experiences()) == 1

    assert new_memory_system.get_events()[0].price_change == 12.5
    assert new_memory_system.get_patterns()[0].pattern_id == "pat-test-1"
    assert new_memory_system.get_experiences()[0].decision_action == "BUY"


def test_pattern_discovery_engine_similarity_matching():
    """Tests pattern signature extraction and cosine similarity matching logic."""
    engine = PatternDiscoveryEngine()

    # Mock some observations
    obs = [
        MarketObservation(symbol="XAUUSD", timeframe="H1", timestamp=datetime.now(), high=100, low=90, open_price=95, close_price=95 + i * 2, volume=10)
        for i in range(6)
    ]

    sig = engine.extract_signature(obs, window_size=5)
    assert len(sig) == 4

    # Calculate perfect similarity with itself
    score = engine.calculate_similarity(sig, sig)
    assert pytest.approx(score, 0.01) == 1.0

    # Opposite sequence should yield negative cosine similarity
    opposite_sig = [-s for s in sig]
    score_opposite = engine.calculate_similarity(sig, opposite_sig)
    assert pytest.approx(score_opposite, 0.01) == -1.0


def test_simulation_brain_and_outcome_evaluation_engine():
    """Tests simulated trade creation, excursion tracking, and feedback learning updates."""
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    sim_brain = SimulationBrain(symbol="XAUUSD", timeframe="H1")
    eval_engine = OutcomeEvaluationEngine(memory_system)

    # Seed an initial Pattern in Pattern Memory
    pat = PatternMemory(
        pattern_id="pat-trend", sequence_signature=[1.0, 1.0], occurrences_count=2,
        continuation_count=1, reversal_count=1, outcomes=[], created_at=datetime.now()
    )
    memory_system.add_pattern(pat)

    # 1. Place a Virtual Simulation BUY Trade
    trade = sim_brain.make_virtual_decision(
        action="BUY", entry_price=1800.0, timestamp=datetime(2026, 1, 1, 12, 0),
        stop_offset=10.0, target_offset=20.0
    )
    assert trade is not None
    assert trade.virtual_stop == 1790.0
    assert trade.virtual_target == 1820.0

    # 2. Feed positive price update candle to close the trade as SUCCESS
    update_candle = MarketObservation(
        symbol="XAUUSD", timeframe="H1", timestamp=datetime(2026, 1, 1, 13, 0),
        high=1825.0, low=1798.0, open_price=1800.0, close_price=1822.0, volume=100.0
    )
    closed = sim_brain.update_active_trades(update_candle)
    assert len(closed) == 1
    assert closed[0].final_result == "SUCCESS"
    assert closed[0].max_favorable_movement == 25.0
    assert closed[0].max_adverse_movement == -2.0

    # 3. Evaluate completed trade in Outcome Evaluation Engine
    situation_sig = [1.0, 1.0]
    exp = eval_engine.evaluate_completed_trade(closed[0], situation_sig)
    assert exp.outcome_result == "SUCCESS"
    assert len(memory_system.get_experiences()) == 1

    # 4. Perform Learning Update to update pattern occurrences
    lr = eval_engine.perform_learning_update(symbol="XAUUSD")
    assert lr.learned_patterns_count == 1
    assert "pat-trend" in lr.successful_patterns


def test_live_analysis_brain_and_strict_read_only_safety():
    """Tests the combined live analysis pipeline and verifies that no trading execution pathways exist."""
    memory_system = MarketMemorySystem(storage_dir=TEST_STORAGE_DIR)
    brain = LiveAnalysisBrain(symbol="XAUUSD", timeframe="H1", memory_system=memory_system)

    # Process a sequence of 5 candles to initialize history and extract signature
    for i in range(5):
        raw_candle = {
            "timestamp": (datetime(2026, 1, 1, 12, 0) + timedelta(hours=i)).isoformat(),
            "high": 1800.0 + i * 2 + 1,
            "low": 1800.0 + i * 2 - 1,
            "open": 1800.0 + i * 2,
            "close": 1800.0 + i * 2 + 1,
            "volume": 100.0
        }
        report = brain.process_live_candle(raw_candle)

        # Confirm reports indicate complete compliance and zero active live trades
        assert report.is_read_only_compliant is True

    # Verify no execution-related function definitions or imports exist in brain files
    for filename in ["live_brain.py", "simulation.py", "models.py", "data_reality.py"]:
        filepath = os.path.join("src", "Research", "Brain", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Must not contain active ordering words or trade requests
            for forbidden_execution in ["place_order", "send_order", "OrderSend", "modify_account"]:
                assert forbidden_execution not in content
