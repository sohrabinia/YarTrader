from datetime import datetime
from typing import Dict, List, Any, Optional
from src.Decision.Intelligence.models import DecisionIntelligenceReport


class PerformanceMemory:
    """
    In-memory persistent database storing historical decision reports and outcomes
    to formulate performance matrices and strategy evaluation memories.
    """

    def __init__(self) -> None:
        self._history: List[DecisionIntelligenceReport] = []

    def record_decision(self, report: DecisionIntelligenceReport) -> None:
        self._history.append(report)

    def get_history(self) -> List[DecisionIntelligenceReport]:
        return self._history


class LearningEngine:
    """
    Continually analyzes decision outcomes and evaluates feedback loops
    to propose mathematical optimization parameters without utilizing machine learning.
    """

    def __init__(self, memory: PerformanceMemory) -> None:
        self.memory = memory

    def generate_feedback_report(self) -> Dict[str, Any]:
        """Analyzes historical decision records to calculate overall performance and quality metrics."""
        history = self.memory.get_history()
        if not history:
            return {
                "analyzed_count": 0,
                "overall_success_ratio": 1.0,
                "suggested_optimization_multiplier": 1.0
            }

        approved_count = sum(1 for r in history if r.State == "Approved")
        success_ratio = approved_count / len(history)

        # Propose conservative multiplier adjustment based on overall approval scores
        suggested_multiplier = 0.90 if success_ratio < 0.60 else (1.10 if success_ratio > 0.85 else 1.0)

        return {
            "analyzed_count": len(history),
            "overall_success_ratio": round(success_ratio, 4),
            "suggested_optimization_multiplier": suggested_multiplier
        }
