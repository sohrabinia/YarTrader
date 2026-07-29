import math
from datetime import datetime
from typing import Dict, List, Any, Tuple
from src.Research.Brain.models import SimulatedDecision, PatternMemory, MarketEvent

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
