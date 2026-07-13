from datetime import datetime
from typing import List, Dict
from src.Learning.Interfaces.interfaces import ILearningEngine
from src.Learning.Models.models import LearningFeedback, ImprovementSuggestion, PerformanceRecord

class OptimizationEngine:
    """
    Classical mathematical parameter optimization processor.
    Strictly contains no machine learning algorithms or neural networks.
    """
    def optimize_exposure(self, average_outcome: float) -> ImprovementSuggestion:
        if average_outcome < -0.05:
            suggested = 0.15
            reason = "Recorded high negative outcomes; suggesting reduction of maximum exposure limits."
        else:
            suggested = 0.25
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
        self._feedbacks.append(feedback)

    def generate_suggestions(self) -> List[ImprovementSuggestion]:
        if not self._feedbacks:
            return []

        avg_outcome = sum(fb.ActualOutcomeMetric for fb in self._feedbacks) / len(self._feedbacks)
        suggestion = self._optimizer.optimize_exposure(avg_outcome)
        return [suggestion]


class FeedbackCollector:
    """Registers and audits feedback traces on completed decisions."""
    def __init__(self) -> None:
        self._collector: List[LearningFeedback] = []

    def record_feedback(self, feedback: LearningFeedback) -> None:
        self._collector.append(feedback)

    def get_all_feedback(self) -> List[LearningFeedback]:
        return self._collector


class PerformanceTracker:
    """Tracks historical performance records over time."""
    def __init__(self) -> None:
        self._records: Dict[str, PerformanceRecord] = {}

    def log_performance_point(self, metric_name: str, value: float) -> None:
        if metric_name not in self._records:
            self._records[metric_name] = PerformanceRecord(metric_name, {})
        self._records[metric_name].HistoricalValues[datetime.now()] = value

    def get_performance_record(self, metric_name: str) -> PerformanceRecord | None:
        return self._records.get(metric_name)


class LearningFramework:
    """
    Comprehensive Learning framework integrating feedback collectors,
    trackers, and suggestions to prepare the platform for future AI tuning models.
    """
    def __init__(self) -> None:
        self.Collector = FeedbackCollector()
        self.Tracker = PerformanceTracker()
        self.Processor = LearningProcessor()

    def feed_decision_outcome(self, decision_id: str, outcome_metric: float) -> None:
        """Helper to collect feedback, track performance points, and trigger processor logs."""
        feedback = LearningFeedback(decision_id, outcome_metric, datetime.now())
        self.Collector.record_feedback(feedback)
        self.Tracker.log_performance_point("DecisionOutcome", outcome_metric)
        self.Processor.process_feedback(feedback)

    def retrieve_optimization_improvements(self) -> List[ImprovementSuggestion]:
        """Orchestrates suggestions from the processor."""
        return self.Processor.generate_suggestions()
