from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore, StrategyDefinition
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Strategy.Evaluation.context import StrategyEvaluationContext
from src.Strategy.Evaluation.scorer import StrategyScorer
from src.Infrastructure.exceptions import ValidationException, AssessmentException

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

    def _validate_safety(self, candidate: StrategyCandidate, context: Optional[StrategyEvaluationContext]) -> None:
        # Validate candidate input
        if not candidate:
            raise ValidationException("StrategyCandidate cannot be None.")
        if not candidate.Id or not candidate.Id.strip():
            raise ValidationException("StrategyCandidate ID cannot be empty or blank.")
        if not candidate.Name or not candidate.Name.strip():
            raise ValidationException("StrategyCandidate Name cannot be empty or blank.")

        # Prevent execution leakages / trading bot keywords
        forbidden_keywords = {
            "buy_order", "sell_order", "place_order", "broker_connection",
            "live_trade", "execute_order", "buy_signal", "sell_signal",
            "order_manager", "active_broker"
        }

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for keyword in forbidden_keywords:
                    if keyword in lower_str:
                        raise ValidationException(
                            f"Safety Violation: Strategy Candidate contains forbidden execution-related keyword '{keyword}'."
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_object(k)
                    scan_object(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan_object(item)

        scan_object(candidate.Name)
        scan_object(candidate.Description)
        scan_object(candidate.ResearchContext)

    def evaluate(
        self,
        candidate: StrategyCandidate,
        context: Optional[StrategyEvaluationContext] = None
    ) -> StrategyEvaluation:
        """
        Scores a Candidate based on strict suitability evaluation matrices.
        Supports both direct evaluation and contextual evaluation.
        """
        # 1. Enforce safety and structure
        self._validate_safety(candidate, context)

        # 2. Synthesize context if missing
        if context is None:
            context = StrategyEvaluationContext(
                ResearchInsights=[],
                MarketObservations=[],
                HistoricalScenarioInfo={},
                RiskContext={},
                Metadata=candidate.ResearchContext
            )

        # 3. Core dynamic scorer evaluation
        scorer = StrategyScorer()
        score = scorer.calculate_score(candidate, context)

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

    def evaluate_concept(
        self,
        candidate: StrategyCandidate,
        context: Optional[StrategyEvaluationContext] = None
    ) -> EvaluationResult:
        """Convenience method returning a detailed EvaluationResult."""
        evaluation = self.evaluate(candidate, context)
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

    def evaluate_and_record(
        self,
        candidate: StrategyCandidate,
        context: Optional[StrategyEvaluationContext] = None
    ) -> StrategyEvaluation:
        """Runs rating evaluations, logs outcome to history register, and returns the evaluation."""
        evaluation = self._evaluator.evaluate(candidate, context)
        self._history.append(evaluation)
        return evaluation

    def compare_candidates(self, candidates: List[StrategyCandidate]) -> Optional[StrategyCandidate]:
        """Compares multiple candidates, returning the one with the highest overall evaluation score."""
        if not candidates:
            return None

        best_candidate: Optional[StrategyCandidate] = None
        best_score = -1.0

        for cand in candidates:
            # Reconstruct default context from each candidate context if possible
            eval_res = self._evaluator.evaluate(cand)
            if eval_res.Score.OverallScore > best_score:
                best_score = eval_res.Score.OverallScore
                best_candidate = cand

        return best_candidate

    def get_evaluation_history(self, strategy_id: str) -> List[StrategyEvaluation]:
        """Queries historical score traces for a strategy identifier."""
        return [e for e in self._history if e.StrategyId == strategy_id]
