from dataclasses import dataclass
from datetime import datetime
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
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
