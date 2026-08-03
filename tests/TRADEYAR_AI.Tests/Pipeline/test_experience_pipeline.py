import os
import shutil
import tempfile
import pytest
from src.Research.Brain.memory import MarketMemorySystem
from src.Intelligence.Pipeline.pipeline import ExperiencePipeline

@pytest.fixture
def temp_memory_system():
    temp_dir = tempfile.mkdtemp()
    mem_sys = MarketMemorySystem(storage_dir=temp_dir)
    yield mem_sys
    shutil.rmtree(temp_dir)

def test_experience_pipeline_cycle(temp_memory_system):
    """Verifies complete passive ExperiencePipeline transitions with assertion-backed validations."""
    pipeline = ExperiencePipeline(memory_system=temp_memory_system)

    # Define input payloads for standard transition
    task_id = "task-001"
    goal = "Evaluate similar patterns on XAUUSD breakout"

    action_plan = {
        "decision": "BUY",
        "signature": [1.5, -0.5, 0.8]
    }

    result_outcome = {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "success": False, # Simulate adverse failure to check improvement trigger
        "mfe": 5.0,
        "mae": -12.0
    }

    judge_evaluation = {
        "reasoning_quality_score": 0.75, # low score to check improvement suggestions
        "decision_quality_score": 0.70,
        "learning_feedback": "Adverse excursion hit stop limit due to aggressive breakout entry."
    }

    # Execute pipeline cycle
    record = pipeline.execute_pipeline_cycle(
        task_id=task_id,
        goal_description=goal,
        action_plan=action_plan,
        result_outcome=result_outcome,
        judge_evaluation=judge_evaluation
    )

    # Assert correct transitions and outputs
    assert record["task_id"] == task_id
    assert record["goal"] == goal
    assert record["action"]["decision"] == "BUY"
    assert record["result"]["success"] is False
    assert record["evaluation"]["reasoning_score"] == 0.75

    # Assert Memory Storage (Layer 2 Experience Memory updated)
    experiences = temp_memory_system.get_experiences()
    assert len(experiences) == 1
    stored_exp = experiences[0]
    assert stored_exp.experience_id == record["stored_experience_id"]
    assert stored_exp.outcome_result == "FAILURE"

    # Assert Improvement generation
    improvements = record["improvements"]
    assert len(improvements) == 2
    assert any("Enhance lookback" in i for i in improvements)
    assert any("Re-calibrate similarity" in i for i in improvements)
