from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import PatternMemory

class StatisticalValidationEngine:
    """
    Performs rigid Phase 5 statistical validation of MarketBehaviorMemory.
    Provides out-of-sample checks, overfitting penalties, and integrity acceptance tests.
    """
    def __init__(self, min_sample_size: int = 5, tolerance_pct: float = 15.0) -> None:
        self.min_sample_size = min_sample_size
        self.tolerance_pct = tolerance_pct

    def validate_pattern_sample_size(self, pattern: PatternMemory) -> str:
        """Enforces minimum sample size rules. Returns 'INSUFFICIENT_SAMPLE' if below threshold."""
        if pattern.occurrences_count < self.min_sample_size:
            return "INSUFFICIENT_SAMPLE"
        return "SUFFICIENT_SAMPLE"

    def perform_walk_forward_validation(
        self,
        historical_outcomes: List[Dict[str, Any]],
        out_of_sample_outcomes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Conducts walk-forward chronological out-of-sample validation to prevent double-dipping.
        Compares continuation ratios and checks for performance divergence.
        """
        if not historical_outcomes:
            return {"status": "INSUFFICIENT_DATA", "divergence": 0.0}

        # Calculate historical continuation ratio
        hist_cont = sum(1 for o in historical_outcomes if o.get("is_continuation", True) or o.get("outcome") == "SUCCESS")
        hist_ratio = hist_cont / len(historical_outcomes)

        if not out_of_sample_outcomes:
            return {
                "status": "NO_OUT_OF_SAMPLE_DATA",
                "historical_ratio": hist_ratio,
                "divergence": 0.0
            }

        # Calculate out-of-sample continuation ratio
        oos_cont = sum(1 for o in out_of_sample_outcomes if o.get("is_continuation", True) or o.get("outcome") == "SUCCESS")
        oos_ratio = oos_cont / len(out_of_sample_outcomes)

        # Compute divergence
        divergence = abs(hist_ratio - oos_ratio) * 100.0

        status = "PASSED"
        if divergence > self.tolerance_pct:
            status = "UNRELIABLE_CONFIDENCE"

        return {
            "status": status,
            "historical_ratio": round(hist_ratio, 4),
            "out_of_sample_ratio": round(oos_ratio, 4),
            "divergence_pct": round(divergence, 2)
        }

    def check_overfitting_sensitivity(self, pattern: PatternMemory) -> Dict[str, Any]:
        """
        Evaluates XAUUSD single-symbol overfitting.
        Flags narrow patterns with zero variance or overly unidirectional outcomes on tiny samples.
        """
        signature = pattern.sequence_signature
        if len(signature) < 2:
            return {"is_overfit": True, "reason": "Insufficient signature length"}

        # Check signature variance
        mean = sum(signature) / len(signature)
        variance = sum((x - mean) ** 2 for x in signature) / len(signature)

        is_overfit = False
        reasons = []

        if variance < 1e-4:
            is_overfit = True
            reasons.append("Zero variance/Static signature")

        # Unidirectional outcomes on small samples
        total = pattern.occurrences_count
        if total < 10:
            max_flow = max(pattern.continuation_count, pattern.reversal_count)
            ratio = max_flow / total if total > 0 else 0.0
            if ratio > 0.95:
                is_overfit = True
                reasons.append("Unidirectional outcomes on small sample")

        return {
            "is_overfit": is_overfit,
            "reasons": reasons,
            "variance": round(variance, 6)
        }


class QualityControlBrain:
    """
    Independent evaluator to grade reasoning quality.
    Ensures that hypotheses are based on reliable pattern sample sizes,
    high similarity matching, and checks for accidental overfitting.
    """
    def __init__(self, min_sample_size: int = 5, min_similarity: float = 0.85) -> None:
        self.min_sample_size = min_sample_size
        self.min_similarity = min_similarity

    def evaluate_reasoning_quality(
        self,
        matched_patterns: List[Tuple[PatternMemory, float]],
        historical_sample_size: int
    ) -> float:
        """
        Grades reasoning quality from 0.0 to 1.0.
        Factors:
        - Sample size (number of occurrences in history)
        - Similarity confidence scores
        - Overfitting check (too narrow patterns with very low occurrences are flagged)
        """
        if not matched_patterns:
            return 0.0

        # Max similarity matched
        best_sim = max(score for pat, score in matched_patterns)

        # Total historical sample size matched
        total_occurrences = sum(pat.occurrences_count for pat, score in matched_patterns)

        # 1. Similarity score factor
        sim_factor = min(1.0, best_sim)

        # 2. Sample size factor
        if total_occurrences >= self.min_sample_size:
            sample_factor = 1.0
        else:
            sample_factor = total_occurrences / self.min_sample_size

        # 3. Overfitting / Accidental bias check
        # If there are very few patterns but they have 100% similarity on tiny samples,
        # it might be overfit/accidental.
        overfit_penalty = 1.0
        if best_sim > 0.98 and total_occurrences < 3:
            overfit_penalty = 0.5  # High penalty for high similarity on tiny sample sizes

        # Compute weighted grade
        grade = (sim_factor * 0.4 + sample_factor * 0.4 + overfit_penalty * 0.2)
        return min(1.0, max(0.0, grade))
