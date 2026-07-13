from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class StrategyComparisonResult:
    """
    Represents the comparative ranking and breakdown of evaluated Strategy Candidates.
    Provides ranking intelligence only, with no execution or strategy selection for trading.
    """
    RankedStrategyIds: List[str]
    BestStrategyId: Optional[str]
    Evaluations: Dict[str, StrategyEvaluation]
    ComparisonDetails: Dict[str, Any] = field(default_factory=dict)


class StrategyComparator:
    """
    Compares multiple Strategy Candidates, ranks their evaluation quality, and produces comparison analysis.
    This is analytical only; it does not select strategies for active trading execution.
    """

    def compare(
        self,
        candidates: List[StrategyCandidate],
        evaluations: List[StrategyEvaluation]
    ) -> StrategyComparisonResult:
        """
        Compares multiple candidates using their pre-computed evaluations.
        Ranks them by OverallScore descending.
        """
        if not candidates:
            raise ValidationException("Candidates list cannot be empty for comparison.")
        if not evaluations:
            raise ValidationException("Evaluations list cannot be empty for comparison.")

        # Map evaluations by StrategyId for fast lookup
        eval_map = {ev.StrategyId: ev for ev in evaluations}

        # Match candidates with evaluations
        valid_candidates = []
        for cand in candidates:
            if cand.Id in eval_map:
                valid_candidates.append(cand)
            else:
                raise ValidationException(
                    f"Validation Error: Candidate with ID '{cand.Id}' does not have a corresponding evaluation."
                )

        # Sort candidates by overall score descending, using candidate ID as secondary tiebreaker for deterministic stability
        sorted_candidates = sorted(
            valid_candidates,
            key=lambda c: (eval_map[c.Id].Score.OverallScore, c.Id),
            reverse=True
        )

        ranked_ids = [c.Id for c in sorted_candidates]
        best_id = ranked_ids[0] if ranked_ids else None

        # Build comparison details
        details = {
            "total_compared": len(valid_candidates),
            "score_differential": 0.0,
            "rankings": []
        }

        for idx, cand in enumerate(sorted_candidates):
            ev = eval_map[cand.Id]
            details["rankings"].append({
                "rank": idx + 1,
                "strategy_id": cand.Id,
                "name": cand.Name,
                "overall_score": ev.Score.OverallScore,
                "confidence": ev.Score.Confidence
            })

        if len(sorted_candidates) > 1:
            best_score = eval_map[ranked_ids[0]].Score.OverallScore
            worst_score = eval_map[ranked_ids[-1]].Score.OverallScore
            details["score_differential"] = round(best_score - worst_score, 4)

        return StrategyComparisonResult(
            RankedStrategyIds=ranked_ids,
            BestStrategyId=best_id,
            Evaluations=eval_map,
            ComparisonDetails=details
        )
