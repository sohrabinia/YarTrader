import math
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
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
        historical_patterns: List[PatternMemory],
        current_behavior_profile: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[PatternMemory, float]]:
        """
        Scans historical pattern memory and returns list of matching patterns and their
        respective similarity scores exceeding the threshold.
        """
        if not current_sig:
            return []

        matches: List[Tuple[PatternMemory, float]] = []
        for pat in historical_patterns:
            sequence_score = self.calculate_similarity(current_sig, pat.sequence_signature)
            score = sequence_score
            if current_behavior_profile:
                historical_profile = {}
                for outcome in reversed(getattr(pat, "outcomes", [])):
                    if isinstance(outcome, dict) and outcome.get("behavior_profile"):
                        historical_profile = outcome["behavior_profile"]
                        break
                if historical_profile:
                    profile_score = 1.0 - self.profile_distance(current_behavior_profile, historical_profile)
                    score = (sequence_score * 0.70) + (profile_score * 0.30)
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
        total_buy = 0.0
        total_sell = 0.0
        learning_samples = 0
        target_reached_samples = 0
        total_mfe = 0.0
        total_mae = 0.0
        total_observed_bars = 0

        for pat, score in matches:
            weight = score  # Give higher weight to closer similarity
            total_occurrences += pat.occurrences_count
            total_continuation += int(pat.continuation_count * weight)
            total_reversal += int(pat.reversal_count * weight)
            total_buy += float(getattr(pat, "buy_count", 0)) * weight
            total_sell += float(getattr(pat, "sell_count", 0)) * weight
            for outcome in getattr(pat, "outcomes", []):
                learning = outcome.get("learning_outcome", {}) if isinstance(outcome, dict) else {}
                if learning:
                    learning_samples += 1
                    if learning.get("target_reached"):
                        target_reached_samples += 1
                    total_mfe += float(learning.get("max_favorable_movement", 0.0))
                    total_mae += abs(float(learning.get("max_adverse_movement", 0.0)))
                    total_observed_bars += int(learning.get("observations_tracked", 0))

        sum_outcomes = total_continuation + total_reversal
        continuation_pct = (total_continuation / sum_outcomes * 100.0) if sum_outcomes > 0 else 50.0
        reversal_pct = (total_reversal / sum_outcomes * 100.0) if sum_outcomes > 0 else 50.0

        directional_total = total_buy + total_sell
        buy_pct = (total_buy / directional_total * 100.0) if directional_total > 0 else 0.0
        sell_pct = (total_sell / directional_total * 100.0) if directional_total > 0 else 0.0

        return {
            "similar_situations_found": len(matches),
            "total_occurrences_cataloged": total_occurrences,
            "continuation_pct": round(continuation_pct, 2),
            "reversal_pct": round(reversal_pct, 2),
            "directional_samples": int(directional_total),
            "buy_pct": round(buy_pct, 2),
            "sell_pct": round(sell_pct, 2),
            "learning_samples": learning_samples,
            "target_reached_pct": round((target_reached_samples / learning_samples * 100.0) if learning_samples else 0.0, 2),
            "average_mfe": round(total_mfe / learning_samples, 4) if learning_samples else 0.0,
            "average_mae": round(total_mae / learning_samples, 4) if learning_samples else 0.0,
            "average_observed_bars": round(total_observed_bars / learning_samples, 2) if learning_samples else 0.0,
            "outcome_summary": (
                f"Found {len(matches)} similar patterns with "
                f"{continuation_pct:.1f}% continuation vs {reversal_pct:.1f}% reversal; "
                f"directional evidence is {buy_pct:.1f}% BUY vs {sell_pct:.1f}% SELL."
            )
        }

    def extract_behavior_profile(self, observations: List[MarketObservation], window_size: int = 12) -> Dict[str, float]:
        """Extracts raw price-action behavior without assigning a trading regime label."""
        if len(observations) < 3:
            return {}
        recent = observations[-window_size:]
        closes = [o.close_price for o in recent]
        ranges = [max(0.0, o.high - o.low) for o in recent]
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        abs_total = sum(abs(x) for x in changes)
        net = closes[-1] - closes[0]
        sign_changes = sum(
            1 for a, b in zip(changes, changes[1:]) if a != 0 and b != 0 and (a > 0) != (b > 0)
        )
        prior_avg_range = sum(ranges[:-1]) / max(1, len(ranges) - 1)
        return {
            "directional_efficiency": abs(net) / abs_total if abs_total else 0.0,
            "net_change_normalized": net / max(ranges) if max(ranges) else 0.0,
            "range_expansion": ranges[-1] / prior_avg_range if prior_avg_range else 0.0,
            "reversal_frequency": sign_changes / max(1, len(changes) - 1),
            "average_range": sum(ranges) / len(ranges),
        }

    def profile_distance(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        """Returns a bounded distance between raw behavioral profiles."""
        if not a or not b:
            return 1.0
        keys = sorted(set(a).intersection(b))
        if not keys:
            return 1.0
        diffs = []
        for key in keys:
            scale = max(abs(float(a[key])), abs(float(b[key])), 1.0)
            diffs.append(abs(float(a[key]) - float(b[key])) / scale)
        return min(1.0, sum(diffs) / len(diffs))

    def create_new_pattern(
        self,
        sig: List[float],
        is_continuation: bool = True,
        direction: str = "WAIT",
        behavior_profile: Dict[str, float] = None,
    ) -> PatternMemory:
        """Constructs a brand-new PatternMemory record representing a discovered sequence fingerprint."""
        return PatternMemory(
            pattern_id=f"pat-{uuid.uuid4().hex[:8]}",
            sequence_signature=sig,
            occurrences_count=1,
            continuation_count=1 if is_continuation else 0,
            reversal_count=0 if is_continuation else 1,
            buy_count=1 if direction == "BUY" else 0,
            sell_count=1 if direction == "SELL" else 0,
            outcomes=[{
                "timestamp": datetime.now().isoformat(),
                "is_continuation": is_continuation,
                "direction": direction,
                "behavior_profile": behavior_profile or {},
            }],
            created_at=datetime.now()
        )
