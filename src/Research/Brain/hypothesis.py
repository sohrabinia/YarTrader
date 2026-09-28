import uuid
from typing import List, Dict, Any, Tuple, Optional
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
        historical_patterns: List[PatternMemory],
        current_behavior_profile: Optional[Dict[str, float]] = None,
        multi_timeframe_context: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Hypothesis:
        """Formulates a hypothesis from historical pattern evidence only."""
        matches = self.discovery_engine.find_matches(
            current_signature,
            historical_patterns,
            current_behavior_profile=current_behavior_profile,
        )

        if not matches:
            return Hypothesis(
                hypothesis_id=f"hyp-{uuid.uuid4().hex[:8]}",
                sequence_signature=current_signature,
                expected_direction="WAIT",
                supporting_samples=[],
                contradicting_samples=[],
                confidence=0.0,
                validation_status="PENDING",
                meta={
                    "reason": "No historical pattern matches found.",
                    "behavior_profile": current_behavior_profile or {},
                    "multi_timeframe_context": multi_timeframe_context or {},
                    "move_expectation": {
                        "learning_samples": 0,
                        "target_reached_pct": 0.0,
                        "average_mfe": 0.0,
                        "average_mae": 0.0,
                        "average_observed_bars": 0.0,
                    },
                    "anticipation": {
                        "state": "NO_EDGE",
                        "direction": "WAIT",
                        "confidence_pct": 0.0,
                        "similar_situations_found": 0,
                        "continuation_pct": 0.0,
                        "reversal_pct": 0.0,
                        "future_data_visible_at_decision": False,
                        "execution_trigger": "NEXT_VALID_MARKET_TRIGGER",
                    },
                }
            )

        outcome_agg = self.discovery_engine.aggregate_outcomes(matches)
        continuation_pct = outcome_agg["continuation_pct"]
        reversal_pct = outcome_agg["reversal_pct"]
        buy_pct = float(outcome_agg.get("buy_pct", 0.0))
        sell_pct = float(outcome_agg.get("sell_pct", 0.0))
        directional_samples = int(outcome_agg.get("directional_samples", 0))

        if directional_samples >= 3 and buy_pct > 60.0 and buy_pct > sell_pct:
            expected_direction = "BUY"
            confidence = buy_pct
        elif directional_samples >= 3 and sell_pct > 60.0 and sell_pct > buy_pct:
            expected_direction = "SELL"
            confidence = sell_pct
        else:
            expected_direction = "WAIT"
            confidence = max(buy_pct, sell_pct)

        supporting: List[Dict[str, Any]] = []
        contradicting: List[Dict[str, Any]] = []
        for pat, score in matches:
            pat_dict = pat.to_dict()
            is_supporting_pat = (
                (expected_direction == "BUY" and getattr(pat, "buy_count", 0) >= getattr(pat, "sell_count", 0))
                or (expected_direction == "SELL" and getattr(pat, "sell_count", 0) >= getattr(pat, "buy_count", 0))
            )
            item = {"pattern_id": pat.pattern_id, "similarity_score": score, "pattern_details": pat_dict}
            if is_supporting_pat:
                supporting.append(item)
            else:
                contradicting.append(item)

        return Hypothesis(
            hypothesis_id=f"hyp-{uuid.uuid4().hex[:8]}",
            sequence_signature=current_signature,
            expected_direction=expected_direction,
            supporting_samples=supporting,
            contradicting_samples=contradicting,
            confidence=confidence,
            validation_status="PENDING",
            meta={
                "total_matches_count": len(matches),
                "directional_evidence_required": 3,
                "outcome_agg": outcome_agg,
                "behavior_profile": current_behavior_profile or {},
                "multi_timeframe_context": multi_timeframe_context or {},
                "move_expectation": {
                    "learning_samples": outcome_agg.get("learning_samples", 0),
                    "target_reached_pct": outcome_agg.get("target_reached_pct", 0.0),
                    "average_mfe": outcome_agg.get("average_mfe", 0.0),
                    "average_mae": outcome_agg.get("average_mae", 0.0),
                    "average_observed_bars": outcome_agg.get("average_observed_bars", 0.0),
                },
                "anticipation": {
                    "state": "PRE_MOVE" if expected_direction != "WAIT" else "NO_EDGE",
                    "direction": expected_direction,
                    "confidence_pct": float(confidence),
                    "similar_situations_found": len(matches),
                    "continuation_pct": float(continuation_pct),
                    "reversal_pct": float(reversal_pct),
                    "future_data_visible_at_decision": False,
                    "execution_trigger": "NEXT_VALID_MARKET_TRIGGER",
                },
            }
        )
