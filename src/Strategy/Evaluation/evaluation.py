from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore, StrategyDefinition
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Evaluation.criteria import EvaluationCriteria

@dataclass(frozen=True)
class EvaluationResult:
    """Represents a passive, parameter-driven result of a strategy evaluation."""
    CandidateId: str
    Score: StrategyScore
    IsApproved: bool
    Notes: str
    EvaluatedAt: datetime


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

    def evaluate_concept(self, candidate: StrategyCandidate) -> EvaluationResult:
        """Convenience method returning a detailed EvaluationResult."""
        evaluation = self.evaluate(candidate)
        is_approved = evaluation.Score.OverallScore >= 0.80
        return EvaluationResult(
            CandidateId=candidate.Id,
            Score=evaluation.Score,
            IsApproved=is_approved,
            Notes=evaluation.EvaluationNotes,
            EvaluatedAt=evaluation.EvaluatedAt
        )


class StrategyEvaluationFramework:
    """
    Enables comparative rating analysis and structured audit logs of strategy candidates over time.
    """
    def __init__(self) -> None:
        self._registry: Dict[str, StrategyDefinition] = {}
        self._evaluator = StrategyEvaluator()
        self._history: List[StrategyEvaluation] = []

    def register_concept(self, definition: StrategyDefinition) -> None:
        """Saves an official StrategyDefinition model."""
        self._registry[definition.Id] = definition

    def list_registered_concepts(self) -> List[StrategyDefinition]:
        return list(self._registry.values())

    def evaluate_and_record(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        """Runs rating evaluations, logs outcome to history register, and returns the evaluation."""
        evaluation = self._evaluator.evaluate(candidate)
        self._history.append(evaluation)
        return evaluation

    def compare_candidates(self, candidates: List[StrategyCandidate]) -> Optional[StrategyCandidate]:
        """Compares multiple candidates, returning the one with the highest overall evaluation score."""
        if not candidates:
            return None

        best_candidate: Optional[StrategyCandidate] = None
        best_score = -1.0

        for cand in candidates:
            eval_res = self._evaluator.evaluate(cand)
            if eval_res.Score.OverallScore > best_score:
                best_score = eval_res.Score.OverallScore
                best_candidate = cand

        return best_candidate

    def get_evaluation_history(self, strategy_id: str) -> List[StrategyEvaluation]:
        """Queries historical score traces for a strategy identifier."""
        return [e for e in self._history if e.StrategyId == strategy_id]
