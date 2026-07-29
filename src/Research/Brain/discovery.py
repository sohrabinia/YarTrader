import math
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.Research.Brain.models import MarketObservation, PatternMemory

class PatternDiscoveryEngine:
    """
    Implements mathematical similarity discovery.
    Identifies if a current raw close price action signature resembles historical patterns,
    answering: 'Have I seen something similar before?' without subjective concepts.
    """
    def __init__(self, similarity_threshold: float = 0.80) -> None:
        self.similarity_threshold = similarity_threshold

    def extract_signature(self, observations: List[MarketObservation], window_size: int = 5) -> List[float]:
        """
        Extracts a normalized percentage change price action signature from a window of observations.
        Normalizes by peak absolute change to create a scale-invariant footprint.
        """
        if len(observations) < window_size:
            return []

        recent = observations[-window_size:]
        closes = [o.close_price for o in recent]

        # Calculate sequential price changes
        changes: List[float] = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            changes.append(diff)

        # Normalize changes by max absolute change to be scale invariant
        max_abs = max(abs(c) for c in changes) if changes else 0.0
        if max_abs == 0.0:
            return [0.0] * len(changes)

        return [c / max_abs for c in changes]

    def calculate_similarity(self, sig1: List[float], sig2: List[float]) -> float:
        """Calculates cosine similarity between two sequence signatures."""
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
        historical_patterns: List[PatternMemory]
    ) -> List[Tuple[PatternMemory, float]]:
        """
        Scans historical pattern memory and returns list of matching patterns and their
        respective similarity scores exceeding the threshold.
        """
        if not current_sig:
            return []

        matches: List[Tuple[PatternMemory, float]] = []
        for pat in historical_patterns:
            score = self.calculate_similarity(current_sig, pat.sequence_signature)
            if score >= self.similarity_threshold:
                matches.append((pat, score))

        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def aggregate_outcomes(self, matches: List[Tuple[PatternMemory, float]]) -> Dict[str, Any]:
        """Aggregates previous outcomes (continuation vs reversal) across all similar matches."""
        if not matches:
            return {
                "similar_situations_found": 0,
                "continuation_pct": 0.0,
                "reversal_pct": 0.0,
                "outcome_summary": "No historical matches found."
            }

        total_occurrences = 0
        total_continuation = 0
        total_reversal = 0

        for pat, score in matches:
            weight = score  # Give higher weight to closer similarity
            total_occurrences += pat.occurrences_count
            total_continuation += int(pat.continuation_count * weight)
            total_reversal += int(pat.reversal_count * weight)

        sum_outcomes = total_continuation + total_reversal
        continuation_pct = (total_continuation / sum_outcomes * 100.0) if sum_outcomes > 0 else 50.0
        reversal_pct = (total_reversal / sum_outcomes * 100.0) if sum_outcomes > 0 else 50.0

        return {
            "similar_situations_found": len(matches),
            "total_occurrences_cataloged": total_occurrences,
            "continuation_pct": round(continuation_pct, 2),
            "reversal_pct": round(reversal_pct, 2),
            "outcome_summary": (
                f"Found {len(matches)} similar patterns with "
                f"{continuation_pct:.1f}% continuation vs {reversal_pct:.1f}% reversal likelihood."
            )
        }

    def create_new_pattern(self, sig: List[float], is_continuation: bool = True) -> PatternMemory:
        """Constructs a brand-new PatternMemory record representing a discovered sequence fingerprint."""
        return PatternMemory(
            pattern_id=f"pat-{uuid.uuid4().hex[:8]}",
            sequence_signature=sig,
            occurrences_count=1,
            continuation_count=1 if is_continuation else 0,
            reversal_count=0 if is_continuation else 1,
            outcomes=[{"timestamp": datetime.now().isoformat(), "is_continuation": is_continuation}],
            created_at=datetime.now()
        )
