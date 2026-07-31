import math
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import SimulatedDecision, PatternMemory, MarketEvent

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


class IntelligenceIntegrityService:
    """
    Implements a rigorous, mathematical Intelligence Integrity Layer.
    Detects and flags unsupported conclusions, confidence inflation, missing evidence,
    ignored failure traces, and potential future look-ahead leakage.
    """
    def __init__(self, max_allowed_confidence: float = 0.95) -> None:
        self.max_allowed_confidence = max_allowed_confidence

    def check_decision_integrity(
        self,
        decision: SimulatedDecision,
        matched_patterns: List[Tuple[PatternMemory, float]],
        all_events: List[MarketEvent]
    ) -> Dict[str, Any]:
        """
        Runs comprehensive integrity checks on a proposed simulated decision before general logging.
        Returns a dictionary with status, integrity score, and warnings if any rules were violated.
        """
        is_valid = True
        warnings: List[str] = []
        integrity_score = 1.0

        # 1. Detect Future Leakage
        # The decision timestamp must be strictly newer than or equal to the timestamp of all processed evidence
        decision_time = decision.timestamp
        for p, score in matched_patterns:
            if p.created_at > decision_time:
                is_valid = False
                integrity_score = 0.0
                warnings.append(
                    f"CRITICAL: Future Leakage Detected! Pattern {p.pattern_id} was created "
                    f"at {p.created_at.isoformat()} which is in the future of the decision time {decision_time.isoformat()}."
                )

        # 2. Detect Missing Evidence
        # Making a decision action (BUY/SELL) without matching any pattern or any raw events is invalid.
        if decision.decision_action in ["BUY", "SELL"] and not matched_patterns:
            is_valid = False
            integrity_score = max(0.0, integrity_score - 0.5)
            warnings.append(
                "INTEGRITY ERROR: Missing Evidence! Proposed active action without any matching pattern footprints."
            )

        # 3. Detect Confidence Inflation
        # Check if confidence score exceeds the maximum allowed or is artificially inflated relative to matching sample sizes
        confidence = decision.context.get("confidence_score", 0.50)
        if confidence > self.max_allowed_confidence:
            integrity_score = max(0.0, integrity_score - 0.2)
            warnings.append(
                f"INTEGRITY WARNING: Confidence Inflation! Proposed confidence of {confidence:.2f} "
                f"exceeds strict architectural limit of {self.max_allowed_confidence:.2f}."
            )

        # 4. Detect Unsupported Conclusions
        # Extremely high confidence with very small matched sample size occurrences is unsupported
        if matched_patterns:
            total_occurrences = sum(p.occurrences_count for p, score in matched_patterns)
            if confidence > 0.85 and total_occurrences < 3:
                integrity_score = max(0.0, integrity_score - 0.3)
                warnings.append(
                    f"INTEGRITY WARNING: Unsupported Conclusion! High confidence of {confidence:.2f} "
                    f"proposed with weak historical sample size of only {total_occurrences} occurrences."
                )

        # 5. Detect Ignored Failures
        # Check if the proposed pattern has a high historical reversal rate (reversals > continuations)
        # but the decision still predicts a successful continuation
        if matched_patterns and decision.decision_action in ["BUY", "SELL"]:
            for p, score in matched_patterns:
                if p.reversal_count > p.continuation_count and decision.context.get("expected_scenario") == "Continuation":
                    integrity_score = max(0.0, integrity_score - 0.25)
                    warnings.append(
                        f"INTEGRITY WARNING: Ignored Failures! Proposed continuation on Pattern {p.pattern_id} "
                        f"despite it having higher historical reversal rate (Reversals: {p.reversal_count}, Continuations: {p.continuation_count})."
                    )

        return {
            "is_valid": is_valid,
            "integrity_score": round(integrity_score, 2),
            "warnings": warnings,
            "checked_at": datetime.now().isoformat()
        }
