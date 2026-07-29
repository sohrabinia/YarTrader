from typing import List, Dict, Any
from src.Research.Brain.models import PatternMemory

class LearningIntegrityService:
    """
    Protects the brain from cognitive issues during training:
    - Confidence inflation (artificial confidence spikes without support)
    - Ignoring failures (only cataloging successes while sweeping failures aside)
    - Overfitting (conclusions based on extremely narrow samples)
    - Self-confirmation bias
    """
    def __init__(self, min_sample_size: int = 4) -> None:
        self.min_sample_size = min_sample_size

    def inspect_patterns_integrity(self, patterns: List[PatternMemory]) -> Dict[str, Any]:
        """
        Inspects stored pattern metrics for cognitive issues.
        Returns a rich status report outlining issues discovered:
        - "confidence_inflation_detected": boolean
        - "failures_ignored_detected": boolean
        - "overfitting_detected": boolean
        - "rejection_recommendations": List of pattern IDs recommended to be rejected.
        """
        inflation_detected = False
        failures_ignored = False
        overfitting_detected = False
        rejected_pats: List[str] = []
        issues_summary: List[str] = []

        total_failures = 0
        total_successes = 0

        for pat in patterns:
            total = pat.occurrences_count
            conts = pat.continuation_count
            revs = pat.reversal_count

            # 1. Overfitting detection: High certainty on tiny samples
            if total < self.min_sample_size and (conts == total or revs == total):
                overfitting_detected = True
                rejected_pats.append(pat.pattern_id)
                issues_summary.append(
                    f"Overfitting warning on Pattern {pat.pattern_id[:6]}: 100% unidirectional "
                    f"likelihood calculated from only {total} occurrences."
                )

            # Accumulate totals for general skew metrics
            total_failures += min(conts, revs)
            total_successes += max(conts, revs)

        # 2. Sweep failures check: If the total logged successes are 15x greater than failures,
        # it is mathematically highly probable that failed trials are being deleted or ignored.
        if total_successes > 15 * total_failures and total_successes > 10:
            failures_ignored = True
            issues_summary.append(
                "Integrity Violation: Failure-sweeping/confirmation bias detected. "
                "Logged successes heavily dominate logged failures, signaling missing failure reporting."
            )

        # 3. Confidence Inflation: If the confidence average across small sample patterns exceeds 90%
        small_samples = [p for p in patterns if p.occurrences_count < self.min_sample_size]
        if small_samples:
            avg_small_confidence = sum(
                max(p.continuation_count, p.reversal_count) / p.occurrences_count
                for p in small_samples
            ) / len(small_samples)

            if avg_small_confidence > 0.90:
                inflation_detected = True
                issues_summary.append(
                    f"Confidence Inflation: Average certainty of {avg_small_confidence*100:.1f}% "
                    f"on small samples under-represents true market uncertainty."
                )

        return {
            "confidence_inflation_detected": inflation_detected,
            "failures_ignored_detected": failures_ignored,
            "overfitting_detected": overfitting_detected,
            "rejection_recommendations": rejected_pats,
            "integrity_score": max(0.0, 1.0 - (len(issues_summary) * 0.25)),
            "issues_summary": issues_summary
        }
