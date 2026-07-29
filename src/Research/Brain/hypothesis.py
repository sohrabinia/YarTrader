import uuid
from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import Hypothesis, PatternMemory
from src.Research.Brain.discovery import PatternDiscoveryEngine

class HypothesisEngine:
    """
    Creates hypotheses about current market events based on historical pattern matching.
    Calculates supporting/contradicting patterns, confidence level, and initial validation status.
    """
    def __init__(self, discovery_engine: PatternDiscoveryEngine) -> None:
        self.discovery_engine = discovery_engine

    def formulate_hypothesis(
        self,
        current_signature: List[float],
        historical_patterns: List[PatternMemory]
    ) -> Hypothesis:
        """
        Formulates a hypothesis by finding matches in historical patterns.
        Groups them into supporting (aligned with expected outcome) and
        contradicting samples, and calculates a confidence percentage.
        """
        matches = self.discovery_engine.find_matches(current_signature, historical_patterns)

        if not matches:
            return Hypothesis(
                hypothesis_id=f"hyp-{uuid.uuid4().hex[:8]}",
                sequence_signature=current_signature,
                expected_direction="WAIT",
                supporting_samples=[],
                contradicting_samples=[],
                confidence=0.0,
                validation_status="PENDING",
                meta={"reason": "No historical pattern matches found."}
            )

        # Decide expected direction from outcomes
        outcome_agg = self.discovery_engine.aggregate_outcomes(matches)
        continuation_pct = outcome_agg["continuation_pct"]
        reversal_pct = outcome_agg["reversal_pct"]

        if continuation_pct > 55.0:
            expected_direction = "BUY"
            confidence = continuation_pct
        elif reversal_pct > 55.0:
            expected_direction = "SELL"
            confidence = reversal_pct
        else:
            expected_direction = "WAIT"
            confidence = max(continuation_pct, reversal_pct)

        supporting: List[Dict[str, Any]] = []
        contradicting: List[Dict[str, Any]] = []

        for pat, score in matches:
            pat_dict = pat.to_dict()
            # If our hypothesis is BUY (continuation of current movement structure),
            # any pattern with continuation_count > reversal_count is supporting,
            # otherwise it is contradicting.
            is_supporting_pat = False
            if expected_direction == "BUY":
                is_supporting_pat = pat.continuation_count >= pat.reversal_count
            elif expected_direction == "SELL":
                is_supporting_pat = pat.reversal_count >= pat.continuation_count

            item = {"pattern_id": pat.pattern_id, "similarity_score": score, "pattern_details": pat_dict}
            if is_supporting_pat:
                supporting.append(item)
            else:
                contradicting.append(item)

        hypothesis_id = f"hyp-{uuid.uuid4().hex[:8]}"

        return Hypothesis(
            hypothesis_id=hypothesis_id,
            sequence_signature=current_signature,
            expected_direction=expected_direction,
            supporting_samples=supporting,
            contradicting_samples=contradicting,
            confidence=confidence,
            validation_status="PENDING",
            meta={
                "total_matches_count": len(matches),
                "outcome_agg": outcome_agg
            }
        )
