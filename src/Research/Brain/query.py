from typing import Dict, List, Any, Optional
from src.Research.Brain.memory import MarketMemorySystem

class KnowledgeQueryInterface:
    """
    Exposes a strictly read-only interface querying the Market Discovery Brain's
    epistemic memory systems (Events, Patterns, Experiences, and Learning updates).
    Prepared for future conversational integration to prevent unauthorized write-bypass.
    """
    def __init__(self, memory_system: MarketMemorySystem) -> None:
        self._memory_system = memory_system

    def query_recent_events(self, limit: int = 10, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves read-only details of the most recently chronicled events."""
        events = self._memory_system.get_events(timeframe=timeframe)
        sorted_evts = sorted(events, key=lambda e: e.start_time, reverse=True)
        return [e.to_dict() for e in sorted_evts[:limit]]

    def query_patterns_by_similarity(self, target_signature: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Queries Patterns by similarity to a target close signature footprint."""
        patterns = self._memory_system.get_patterns()
        matches = []

        for p in patterns:
            sig = p.sequence_signature
            if len(sig) == len(target_signature):
                dot_product = sum(a * b for a, b in zip(sig, target_signature))
                norm_a = sum(a * a for a in sig) ** 0.5
                norm_b = sum(b * b for b in target_signature) ** 0.5
                sim = (dot_product / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0
                matches.append((p, sim))

        # Sort matches by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "pattern": m[0].to_dict(),
                "similarity_score": round(m[1], 4)
            }
            for m in matches[:limit]
        ]

    def query_learning_scorecard(self) -> Dict[str, Any]:
        """Queries overall memory health, pattern counts, and verified experience outcomes."""
        experiences = self._memory_system.get_experiences()
        patterns = self._memory_system.get_patterns()
        events = self._memory_system.get_events()

        total_exps = len(experiences)
        success_exps = sum(1 for e in experiences if e.outcome_result == "SUCCESS")
        failures_exps = sum(1 for e in experiences if e.outcome_result == "FAILURE")

        success_rate = (success_exps / total_exps * 100.0) if total_exps > 0 else 0.0

        return {
            "total_events_chronicled": len(events),
            "total_patterns_discovered": len(patterns),
            "total_episodes_evaluated": total_exps,
            "success_episodes": success_exps,
            "failure_episodes": failures_exps,
            "epistemic_success_rate": round(success_rate, 2),
            "status": "Healthy / Isolated"
        }
