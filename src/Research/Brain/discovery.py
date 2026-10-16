import math
import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import MarketObservation, PatternMemory


class PatternDiscoveryEngine:
    """
    Implements mathematical similarity discovery.
    Identifies whether current raw close-price action resembles historical patterns.
    """
    def __init__(self, similarity_threshold: float = 0.80) -> None:
        self.similarity_threshold = similarity_threshold

    def extract_signature(
        self, observations: List[MarketObservation], window_size: int = 5
    ) -> List[float]:
        """Extract a normalized, scale-invariant price-action signature."""
        if len(observations) < window_size:
            return []
        recent = observations[-window_size:]
        closes = [o.close_price for o in recent]
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        max_abs = max(abs(c) for c in changes) if changes else 0.0
        if max_abs == 0.0:
            return [0.0] * len(changes)
        return [c / max_abs for c in changes]

    def calculate_similarity(
        self, sig1: List[float], sig2: List[float]
    ) -> float:
        """Calculate cosine similarity between two sequence signatures."""
        if not sig1 or not sig2 or len(sig1) != len(sig2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(sig1, sig2))
        norm_a = math.sqrt(sum(a * a for a in sig1))
        norm_b = math.sqrt(sum(b * b for b in sig2))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def find_matches(
        self,
        current_sig: List[float],
        historical_patterns: List[PatternMemory],
        symbol: str = "",
        timeframe: str = "",
        timeframe_signature: List[str] = None,
        context_id: str = "",
    ) -> List[Tuple[PatternMemory, float]]:
        """
        Return reusable historical patterns matching the current signature.

        Symbol and timeframe applicability are hard filters. context_id is retained
        as evidence lineage, but is not an exact timestamp-level matching gate.
        """
        if not current_sig:
            return []

        matches: List[Tuple[PatternMemory, float]] = []
        wanted_tfs = sorted(
            {
                str(tf).upper()
                for tf in (timeframe_signature or ([timeframe] if timeframe else []))
            }
        )
        for pat in historical_patterns:
            if symbol and pat.symbol.upper() != symbol.upper():
                continue
            if timeframe and pat.timeframe.upper() != timeframe.upper():
                continue
            if (
                wanted_tfs
                and pat.timeframe_signature
                and sorted(pat.timeframe_signature) != wanted_tfs
            ):
                continue
            # context_id identifies the historical evidence lineage. It must not
            # prevent reuse across later timestamps with the same symbol/timeframe.
            if pat.status == "RETIRED":
                continue
            score = self.calculate_similarity(current_sig, pat.sequence_signature)
            if score >= self.similarity_threshold:
                matches.append((pat, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    def aggregate_outcomes(
        self,
        matches: List[Tuple[PatternMemory, float]],
        current_signature: List[float] = None,
    ) -> Dict[str, Any]:
        """Aggregate previous continuation/reversal outcomes."""
        if not matches:
            return {
                "similar_situations_found": 0,
                "continuation_pct": 0.0,
                "reversal_pct": 0.0,
                "successful_outcomes": 0,
                "failed_outcomes": 0,
                "unlabeled_outcomes": 0,
                "outcome_success_rate_pct": None,
                "evidence_status": "NO_MATCHES",
                "raw_directional_action": "WAIT",
                "raw_directional_confidence": 0.0,
                "outcome_summary": "No historical matches found.",
            }

        total_occurrences = 0
        total_continuation = 0.0
        total_reversal = 0.0
        successful_outcomes = 0
        failed_outcomes = 0
        unlabeled_outcomes = 0
        current_action = (
            "BUY"
            if (current_signature and current_signature[-1] >= 0)
            else "SELL"
        )

        for pat, score in matches:
            weight = max(0.0, score)
            total_occurrences += pat.occurrences_count
            detailed = [o for o in pat.outcomes if o.get("predicted_action")]
            for outcome in detailed:
                predicted_action = str(outcome.get("predicted_action", "")).upper()
                result = str(outcome.get("outcome", "")).upper()
                if result in {"SUCCESS", "FAILURE"}:
                    if result == "SUCCESS":
                        successful_outcomes += 1
                    else:
                        failed_outcomes += 1
                    prediction_correct = result == "SUCCESS"
                    prediction_matches_current = predicted_action == current_action
                    # A successful prediction supports its action; a failed prediction supports the opposite.
                    supports_continuation = prediction_matches_current == prediction_correct
                    if supports_continuation:
                        total_continuation += weight
                    else:
                        total_reversal += weight
                else:
                    unlabeled_outcomes += 1
                    if predicted_action == current_action:
                        total_continuation += weight
                    else:
                        total_reversal += weight
            if not detailed:
                total_continuation += pat.continuation_count * weight
                total_reversal += pat.reversal_count * weight

        sum_outcomes = total_continuation + total_reversal
        continuation_pct = (
            total_continuation / sum_outcomes * 100.0
            if sum_outcomes > 0
            else 50.0
        )
        reversal_pct = (
            total_reversal / sum_outcomes * 100.0
            if sum_outcomes > 0
            else 50.0
        )
        labeled_total = successful_outcomes + failed_outcomes
        success_rate_pct = round(successful_outcomes / labeled_total * 100.0, 2) if labeled_total else None
        if labeled_total == 0:
            evidence_status = "NO_OUTCOME_LABELS"
        elif successful_outcomes == 0:
            evidence_status = "FAILURE_ONLY"
        elif success_rate_pct < 50.0:
            evidence_status = "LOW_SUCCESS_RATE"
        else:
            evidence_status = "VALIDATED_OUTCOMES"
        raw_direction = current_action if continuation_pct > reversal_pct else ("SELL" if current_action == "BUY" else "BUY") if reversal_pct > continuation_pct else "WAIT"
        raw_direction_confidence = round(max(continuation_pct, reversal_pct), 2)
        return {
            "similar_situations_found": len(matches),
            "total_occurrences_cataloged": total_occurrences,
            "current_structure_action": current_action,
            "continuation_pct": round(continuation_pct, 2),
            "reversal_pct": round(reversal_pct, 2),
            "successful_outcomes": successful_outcomes,
            "failed_outcomes": failed_outcomes,
            "unlabeled_outcomes": unlabeled_outcomes,
            "outcome_success_rate_pct": success_rate_pct,
            "evidence_status": evidence_status,
            "raw_directional_action": raw_direction,
            "raw_directional_confidence": raw_direction_confidence,
            "outcome_summary": (
                f"Found {len(matches)} similar patterns: {continuation_pct:.1f}% continuation vs "
                f"{reversal_pct:.1f}% reversal; labeled outcomes {successful_outcomes} success / {failed_outcomes} failure."
            ),
        }

    def create_new_pattern(
        self,
        sig: List[float],
        is_continuation: bool = True,
        symbol: str = "",
        timeframe: str = "",
        timeframe_signature: List[str] = None,
        context_id: str = "",
        context_signature: Dict[str, Any] = None,
    ) -> PatternMemory:
        """Construct a deterministic pattern identity for a scoped sequence."""
        scope_tfs = sorted(
            {
                str(tf).upper()
                for tf in (timeframe_signature or ([timeframe] if timeframe else []))
            }
        )
        identity = json.dumps(
            {
                "symbol": symbol.upper(),
                "timeframe": timeframe.upper(),
                "timeframe_signature": scope_tfs,
                "signature": [round(float(v), 8) for v in sig],
                "context_id": context_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        pattern_id = (
            f"pat-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
        )
        return PatternMemory(
            pattern_id=pattern_id,
            sequence_signature=sig,
            occurrences_count=1,
            continuation_count=1 if is_continuation else 0,
            reversal_count=0 if is_continuation else 1,
            outcomes=[
                {
                    "timestamp": datetime.now().isoformat(),
                    "is_continuation": is_continuation,
                }
            ],
            created_at=datetime.now(),
            symbol=symbol.upper(),
            timeframe=timeframe.upper(),
            timeframe_signature=scope_tfs,
            context_id=context_id,
            context_signature=context_signature or {},
            family_id=pattern_id,
        )
