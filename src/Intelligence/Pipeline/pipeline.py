import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.Research.Brain.models import ExperienceMemory
from src.Research.Brain.memory import MarketMemorySystem

logger = logging.getLogger("ExperiencePipeline")

class ExperiencePipeline:
    """
    Implements the passive AI Experience Learning Pipeline loop:
    Task -> Action -> Result -> Evaluation -> Memory -> Improvement.

    Operates strictly as a passive advisory intelligence system with zero trading capability.
    """
    def __init__(self, memory_system: Optional[MarketMemorySystem] = None) -> None:
        self.memory_system = memory_system or MarketMemorySystem()
        self.pipeline_history: List[Dict[str, Any]] = []

    def execute_pipeline_cycle(
        self,
        task_id: str,
        goal_description: str,
        action_plan: Dict[str, Any],
        result_outcome: Dict[str, Any],
        judge_evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Coordinates a single passive experience learning cycle.
        """
        cycle_id = f"cycle-{uuid.uuid4().hex[:6]}"
        logger.info(f"Executing Experience Pipeline Cycle: {cycle_id} for task_id={task_id}")

        # 1. EVALUATION: Calculate quality metrics based on outcome and judge feedback
        success = result_outcome.get("success", True)
        reasoning_score = judge_evaluation.get("reasoning_quality_score", 0.85)
        decision_score = judge_evaluation.get("decision_quality_score", 0.80)

        # 2. MEMORY: Create and persist an ExperienceMemory record (Layer 2)
        exp_id = f"exp-{task_id}-{uuid.uuid4().hex[:4]}"
        exp = ExperienceMemory(
            experience_id=exp_id,
            symbol=result_outcome.get("symbol", "XAUUSD"),
            timeframe=result_outcome.get("timeframe", "H1"),
            timestamp=datetime.now(),
            situation_signature=action_plan.get("signature", [1.0, 0.0, 0.0]),
            decision_action=action_plan.get("decision", "WAIT"),
            outcome_result="SUCCESS" if success else "FAILURE",
            lesson_feedback=judge_evaluation.get("learning_feedback", "Performance matched expectations."),
            max_favorable_excursion=result_outcome.get("mfe", 0.0),
            max_adverse_excursion=result_outcome.get("mae", 0.0),
            meta={
                "task_id": task_id,
                "cycle_id": cycle_id,
                "judge_reasoning_score": reasoning_score,
                "judge_accuracy": decision_score
            }
        )

        self.memory_system.add_experience(exp)

        # 3. IMPROVEMENT: Generate passive cognitive improvement suggestions
        improvement_suggestions = []
        if not success:
            improvement_suggestions.append(f"Enhance lookback signature size for {exp.symbol} to capture adverse excursion of {exp.max_adverse_excursion}.")
        if reasoning_score < 0.80:
            improvement_suggestions.append("Re-calibrate similarity matching threshold to avoid biased historical pattern weights.")
        if not improvement_suggestions:
            improvement_suggestions.append("Maintain active pattern weights; consistency matches golden baseline.")

        pipeline_record = {
            "cycle_id": cycle_id,
            "task_id": task_id,
            "goal": goal_description,
            "action": action_plan,
            "result": result_outcome,
            "evaluation": {
                "reasoning_score": reasoning_score,
                "decision_score": decision_score,
                "feedback": exp.lesson_feedback
            },
            "stored_experience_id": exp_id,
            "improvements": improvement_suggestions,
            "timestamp": datetime.now().isoformat()
        }

        self.pipeline_history.append(pipeline_record)
        return pipeline_record

    def get_pipeline_history(self) -> List[Dict[str, Any]]:
        return self.pipeline_history
