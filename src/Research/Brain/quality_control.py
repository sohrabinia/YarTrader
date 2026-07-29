from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import PatternMemory

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
