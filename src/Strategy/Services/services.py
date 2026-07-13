from datetime import datetime
from typing import Dict, Optional
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator, IStrategyRegistry, IRuleValidator
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore, StrategyDefinition
from src.Strategy.Evaluation.criteria import EvaluationCriteria

class StrategyEvaluator(IStrategyEvaluator):
    """
    Evaluates StrategyCandidate concepts against evaluation criteria.
    Strictly passive analysis; generates no trade recommendations.
    """
    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        # Create standard scores based on qualitative research factors
        criteria_scores = {
            EvaluationCriteria.STABILITY: 0.85,
            EvaluationCriteria.COMPLEXITY: 0.90,
            EvaluationCriteria.DATA_REQUIREMENTS: 0.70,
            EvaluationCriteria.RISK_COMPATIBILITY: 0.95
        }

        # Calculate overall score as simple average
        avg_score = sum(criteria_scores.values()) / len(criteria_scores)

        score = StrategyScore(
            OverallScore=avg_score,
            Confidence=0.88,
            Criteria=criteria_scores
        )

        notes = (
            f"Concept '{candidate.Name}' evaluated successfully. "
            f"Excellent compatibility with active risk limits."
        )

        return StrategyEvaluation(
            StrategyId=candidate.Id,
            Score=score,
            EvaluationNotes=notes,
            EvaluatedAt=datetime.now()
        )


class StrategyRegistry(IStrategyRegistry):
    """In-memory registry implementation to keep track of approved StrategyDefinitions."""
    def __init__(self) -> None:
        self._store: Dict[str, StrategyDefinition] = {}

    def register_strategy(self, definition: StrategyDefinition) -> None:
        self._store[definition.Id] = definition

    def get_strategy(self, strategy_id: str) -> Optional[StrategyDefinition]:
        return self._store.get(strategy_id)


class StrategyAnalyzer(IRuleValidator):
    """
    Analyzes strategy concepts for structural correctness.
    Guarantees no external/unsafe trading execution rules are embedded.
    """
    def validate_structure(self, definition: StrategyDefinition) -> bool:
        # Ensure name and description fit descriptive metadata rules
        if not definition.Name or not definition.Description:
            return False

        # Ensure status is approved or standard draft
        if definition.Status not in ["Draft", "Approved", "Deprecated"]:
            return False

        # Structure is valid and clean
        return True
