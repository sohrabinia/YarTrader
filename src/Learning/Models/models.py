from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class LearningFeedback:
    """Represents a feedback trace packet on a past decision."""
    DecisionId: str
    ActualOutcomeMetric: float  # e.g., returns or tracking deviation
    RecordedAt: datetime


@dataclass(frozen=True)
class PerformanceRecord:
    """Represents historical performance metrics (such as Sharpe or Sortino ratios)."""
    MetricName: str
    HistoricalValues: Dict[datetime, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ImprovementSuggestion:
    """Represents calculated optimization recommendations for model parameters (no ML used)."""
    TargetParameter: str  # e.g., "MaxExposure"
    SuggestedValue: Any
    Reasoning: str
    CalculatedAt: datetime
