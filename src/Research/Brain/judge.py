from datetime import datetime
from typing import Dict, Any, List, Optional
from src.Research.Brain.models import VirtualTrade, Hypothesis, PatternMemory

class JudgeBrain:
    """
    An independent evaluator separated from simulated decisions.
    Assesses the scientific validity and reasoning behind hypotheses and virtual trades.
    Grades:
    - Was the observation based on sufficient historical evidence?
    - Was the timing reasonable, or did it catch luck?
    - Output Decision Quality Score and Reasoning Quality Score.
    """
    def __init__(self, min_supporting_samples: int = 3) -> None:
        self.min_supporting_samples = min_supporting_samples

    def evaluate_hypothesis_and_decision(
        self,
        hypothesis: Hypothesis,
        virtual_trade: Optional[VirtualTrade],
        actual_outcome_ticks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates a formulated hypothesis and virtual trade independently.
        Returns a rich dict with:
        - decision_quality_score (0.0 to 1.0)
        - reasoning_quality_score (0.0 to 1.0)
        - pattern_accuracy (0.0 to 1.0)
        - learning_feedback (qualitative feedback)
        """
        # 1. Reasoning Quality Evaluation
        # High reasoning quality requires adequate supporting historical samples and high confidence
        supporting_count = len(hypothesis.supporting_samples)
        sample_ratio = min(1.0, supporting_count / self.min_supporting_samples)

        contradicting_count = len(hypothesis.contradicting_samples)
        total_samples = supporting_count + contradicting_count

        bias_penalty = 0.0
        if total_samples > 0:
            contradicting_ratio = contradicting_count / total_samples
            if contradicting_ratio > 0.4:
                # High contradiction ratio flags weak evidence bias
                bias_penalty = 0.3

        base_confidence_score = hypothesis.confidence / 100.0
        reasoning_score = max(0.0, (base_confidence_score * 0.6 + sample_ratio * 0.4) - bias_penalty)

        # 2. Decision Quality Evaluation (Timing and risk management)
        decision_score = 0.5  # Neutral default for WAIT action
        pattern_accuracy = 0.0
        was_luck = False
        feedback = "Decision was based on reasonable evidence."

        if virtual_trade:
            # We look at the actual outcomes: did it succeed?
            success = virtual_trade.final_result == "SUCCESS"
            max_fav = virtual_trade.max_favorable_movement
            max_adv = abs(virtual_trade.max_adverse_movement)

            # Accuracy of expected direction
            if success:
                pattern_accuracy = 1.0
                decision_score = 0.8
                # Check for "luck": if the trade was heavily in draw-down before succeeding,
                # it was high risk / low accuracy timing.
                if max_adv > (max_fav * 1.5) and max_adv > 0.0:
                    was_luck = True
                    decision_score -= 0.3
                    feedback = "Success appears to be heavily influenced by luck. High adverse excursion observed."
                else:
                    feedback = "Accurate timing and strong movement in the hypothesized direction."
            else:
                pattern_accuracy = 0.0
                decision_score = 0.2
                feedback = f"Hypothesis failed. Adverse excursion exceeded limits. Cause: {virtual_trade.reason_of_failure or 'unknown'}."

            # Factor in execution parameters
            if virtual_trade.entry_price <= 0.0:
                decision_score = 0.0
                feedback = "Invalid entry execution price."
        else:
            feedback = "No virtual decision made (WAIT state). Saved execution capital."

        # Return comprehensive evaluation dictionary
        return {
            "decision_quality_score": round(decision_score, 4),
            "reasoning_quality_score": round(reasoning_score, 4),
            "pattern_accuracy": pattern_accuracy,
            "was_influenced_by_luck": was_luck,
            "learning_feedback": feedback,
            "evaluation_timestamp": hypothesis.meta.get("decision_time", datetime.now().isoformat())
        }
