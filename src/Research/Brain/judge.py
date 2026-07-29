from typing import Dict, Any
from src.Research.Brain.models import SimulatedDecision

class JudgeBrain:
    """
    An independent, isolated Judge Brain.
    Receives an immutable SimulatedDecision, the evidence context, and the simulated outcome.
    Returns evaluations, confidence adjustments, and learning feedback suggestions.
    Crucially isolated: cannot create decisions, cannot modify existing history, and cannot erase failures.
    """
    def __init__(self, min_confidence_threshold: float = 0.60) -> None:
        self.min_confidence_threshold = min_confidence_threshold

    def evaluate_decision_outcome(
        self,
        decision: SimulatedDecision,
        evidence: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Independently assesses a simulated trade result to diagnose whether success
        was structurally earned or accidental, and adjusts future learning paths.
        """
        # Ensure strict read-only parameters validation (guarantees Judge does not modify incoming decision)
        symbol = decision.symbol
        decision_action = decision.decision_action
        entry_price = decision.price

        final_result = outcome.get("final_result", "NEUTRAL")  # SUCCESS or FAILURE
        max_favorable_excursion = outcome.get("max_favorable_excursion", 0.0)
        max_adverse_excursion = outcome.get("max_adverse_excursion", 0.0)

        # Diagnose Lucky Win (Accidental success)
        is_lucky_win = False
        evaluation_lbl = "Earned Success"
        confidence_adjustment = 0.0

        if final_result == "SUCCESS":
            # If the trade survived extreme adverse movement close to stop limit before hitting target, it's lucky
            if abs(max_adverse_excursion) > abs(max_favorable_excursion) * 0.8:
                is_lucky_win = True
                evaluation_lbl = "Lucky Win (Accidental Success with Extreme Adverse Excursion)"
                confidence_adjustment = -15.0  # Decelerate future similarity weight
            else:
                confidence_adjustment = 10.0  # Increment confidence weight
        elif final_result == "FAILURE":
            evaluation_lbl = "Structural Error (Failure analyzed)"
            confidence_adjustment = -20.0  # Substantial downward adjustment

        learning_feedback = (
            f"Decision on {symbol} to {decision_action} at {entry_price} evaluated as {evaluation_lbl}. "
            f"MAM: {max_adverse_excursion:.2f}, MFM: {max_favorable_excursion:.2f}."
        )

        return {
            "evaluation": evaluation_lbl,
            "confidence_adjustment": confidence_adjustment,
            "learning_feedback": learning_feedback,
            "is_lucky_win": is_lucky_win,
            "is_structural_failure": final_result == "FAILURE"
        }
