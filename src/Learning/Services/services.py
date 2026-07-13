from datetime import datetime
from typing import List
from src.Learning.Interfaces.interfaces import ILearningEngine
from src.Learning.Models.models import LearningFeedback, ImprovementSuggestion

class OptimizationEngine:
    """
    Classical mathematical parameter optimization processor.
    Strictly contains no machine learning algorithms or neural networks.
    """
    def optimize_exposure(self, average_outcome: float) -> ImprovementSuggestion:
        # Classical rule-based tuning suggestion based on actual feedback outcomes
        if average_outcome < -0.05:  # severe tracking error or loss
            suggested = 0.15  # reduce single asset exposure limit (conservative)
            reason = "Recorded high negative outcomes; suggesting reduction of maximum exposure limits."
        else:
            suggested = 0.25  # standard exposure limit
            reason = "Performance outcomes are stable; maintaining standard exposure limit profile."

        return ImprovementSuggestion(
            TargetParameter="MaxSingleAssetExposure",
            SuggestedValue=suggested,
            Reasoning=reason,
            CalculatedAt=datetime.now()
        )


class LearningProcessor(ILearningEngine):
    """
    Aggregates learning feedback loops and computes parameter improvements.
    """
    def __init__(self) -> None:
        self._feedbacks: List[LearningFeedback] = []
        self._optimizer = OptimizationEngine()

    def process_feedback(self, feedback: LearningFeedback) -> None:
        """Stores a feedback package in memory."""
        self._feedbacks.append(feedback)

    def generate_suggestions(self) -> List[ImprovementSuggestion]:
        if not self._feedbacks:
            return []

        # Calculate mathematical average of outcomes
        avg_outcome = sum(fb.ActualOutcomeMetric for fb in self._feedbacks) / len(self._feedbacks)

        suggestion = self._optimizer.optimize_exposure(avg_outcome)
        return [suggestion]
