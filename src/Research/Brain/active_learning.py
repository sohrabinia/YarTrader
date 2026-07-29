from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import PatternMemory

class ActiveLearningEngine:
    """
    Directs focus toward areas of high weakness/uncertainty rather than repeating easy success.
    Flags patterns as research priorities:
    - High failure rate pattern
    - High uncertainty (contradictory outcomes / close to 50/50 split)
    - New or small sample patterns (under-represented)
    - High variance in excursion results
    """
    def __init__(self, target_uncertainty_lower: float = 40.0, target_uncertainty_upper: float = 60.0) -> None:
        self.target_uncertainty_lower = target_uncertainty_lower
        self.target_uncertainty_upper = target_uncertainty_upper

    def analyze_weaknesses_and_set_priorities(self, patterns: List[PatternMemory]) -> List[Dict[str, Any]]:
        """
        Scans Pattern Memory and returns prioritized pattern signatures to research.
        Higher priority score (0.0 to 10.0) indicates a greater need for training.
        """
        priorities: List[Dict[str, Any]] = []

        for pat in patterns:
            total = pat.occurrences_count
            if total == 0:
                continue

            # Calculate continuation vs reversal split
            cont_ratio = (pat.continuation_count / total) * 100.0
            rev_ratio = (pat.reversal_count / total) * 100.0

            priority_score = 1.0  # Base priority
            reason = "Standard baseline monitoring."

            # Scenario A: High Uncertainty (Close to 50/50 split)
            if self.target_uncertainty_lower <= cont_ratio <= self.target_uncertainty_upper:
                priority_score = 8.5
                reason = "High uncertainty pattern with highly contradictory historical outcomes (close to 50/50 split)."

            # Scenario B: High Failure Rate Pattern
            # Suppose continuation is our default hypothesis. If continuation count is extremely low
            # but occurrences are high, it has high failure/reversal rate.
            elif cont_ratio < 30.0 and total >= 3:
                priority_score = 9.0
                reason = "High failure/reversal pattern with consistent losses."

            # Scenario C: Under-represented Small Sample
            elif total < 3:
                priority_score = 7.0
                reason = "Under-represented sequence structure with insufficient sample occurrences."

            # Round priority score
            priority_score = min(10.0, max(0.0, round(priority_score, 2)))

            priorities.append({
                "pattern_id": pat.pattern_id,
                "sequence_signature": pat.sequence_signature,
                "priority_score": priority_score,
                "reason": reason,
                "occurrences": total,
                "continuation_pct": round(cont_ratio, 2),
                "reversal_pct": round(rev_ratio, 2)
            })

        # Sort descending by priority score
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)
        return priorities
