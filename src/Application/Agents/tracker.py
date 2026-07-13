from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from src.Infrastructure.exceptions import ValidationException


@dataclass
class PerformanceScore:
    """Consolidated performance evaluation metrics for an agent."""
    completeness: float  # 0.0 to 1.0
    reliability: float   # 0.0 to 1.0
    data_quality: float  # 0.0 to 1.0
    consistency: float   # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)


class AgentPerformanceTracker:
    """
    Tracks and aggregates reliability, completeness, consistency,
    and quality metrics across Agent lifecycles to detect performance drift.
    """
    def __init__(self) -> None:
        self._scores: Dict[str, List[PerformanceScore]] = {}  # AgentID -> list of scores

    def record_performance(
        self,
        agent_id: str,
        completeness: float,
        reliability: float,
        data_quality: float,
        consistency: float
    ) -> PerformanceScore:
        """Records a new multi-factor performance evaluation for an agent."""
        if not agent_id:
            raise ValidationException("Tracker Error: Agent ID must not be empty.")

        for name, val in [
            ("completeness", completeness),
            ("reliability", reliability),
            ("data_quality", data_quality),
            ("consistency", consistency)
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValidationException(f"Tracker Error: Metric '{name}' value {val} must be between 0.0 and 1.0.")

        score = PerformanceScore(
            completeness=completeness,
            reliability=reliability,
            data_quality=data_quality,
            consistency=consistency,
            timestamp=datetime.now()
        )

        if agent_id not in self._scores:
            self._scores[agent_id] = []
        self._scores[agent_id].append(score)
        return score

    def get_average_scores(self, agent_id: str) -> Dict[str, float]:
        """Calculates average performance scores for an agent over their history."""
        if agent_id not in self._scores or not self._scores[agent_id]:
            return {
                "completeness": 1.0,
                "reliability": 1.0,
                "data_quality": 1.0,
                "consistency": 1.0
            }

        scores = self._scores[agent_id]
        count = len(scores)
        return {
            "completeness": sum(s.completeness for s in scores) / count,
            "reliability": sum(s.reliability for s in scores) / count,
            "data_quality": sum(s.data_quality for s in scores) / count,
            "consistency": sum(s.consistency for s in scores) / count,
        }

    def clear(self) -> None:
        """Clears performance track histories."""
        self._scores.clear()
