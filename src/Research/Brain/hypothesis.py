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
        buy_pct = float(outcome_agg.get("buy_pct", 0.0))
        sell_pct = float(outcome_agg.get("sell_pct", 0.0))
        directional_samples = int(outcome_agg.get("directional_samples", 0))

        # Direction is learned from actual historical decision outcomes, not
        # inferred from the generic continuation/reversal labels.
        # Until enough directional evidence exists, the Brain stays in WAIT.
        if directional_samples >= 3 and buy_pct > 60.0 and buy_pct > sell_pct:
            expected_direction = "BUY"
            confidence = buy_pct
        elif directional_samples >= 3 and sell_pct > 60.0 and sell_pct > buy_pct:
            expected_direction = "SELL"
            confidence = sell_pct
        else:
            # Backward-compatible structural direction for legacy patterns:
            # continuation follows the direction of the latest normalized move;
            # reversal points against it. This avoids treating every continuation
            # as BUY and every reversal as SELL.
            current_move = current_signature[-1] if current_signature else 0.0
            continuation_direction = "BUY" if current_move > 0 else ("SELL" if current_move < 0 else "WAIT")
            reversal_direction = (
                "SELL" if continuation_direction == "BUY"
                else ("BUY" if continuation_direction == "SELL" else "WAIT")
            )
            if directional_samples == 0 and continuation_pct > 60.0 and continuation_direction != "WAIT":
                expected_direction = continuation_direction
                confidence = continuation_pct
            elif directional_samples == 0 and reversal_pct > 60.0 and reversal_direction != "WAIT":
                expected_direction = reversal_direction
                confidence = reversal_pct
            else:
                expected_direction = "WAIT"
                confidence = max(buy_pct, sell_pct, continuation_pct, reversal_pct)

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
                "directional_evidence_required": 3,
                "outcome_agg": outcome_agg
            }
        )
