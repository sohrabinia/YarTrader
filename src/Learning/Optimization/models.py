from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class LearningFeedbackRecord:
    """
    Immutable representation of a decision outcome feedback record.
    Captures target attributes, expected metrics, and observed results without broker/execution bindings.
    """
    DecisionReference: str
    AnalysisContext: Dict[str, Any]
    ExpectedQuality: float  # Expected overall score/confidence (e.g. 0.0 to 1.0)
    ObservedResult: float   # Observed outcome/metric (e.g. -1.0 to 1.0)
    ConfidenceInformation: Any  # confidence score or metadata
    Timestamp: datetime = field(default_factory=datetime.now)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Prevent live execution leakages inside context/metadata
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for keyword in forbidden_keywords:
                    if keyword in lower_str:
                        raise ValidationException(
                            f"Safety Violation: LearningFeedbackRecord contains forbidden execution-related keyword '{keyword}' in data: '{obj}'."
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_object(k)
                    scan_object(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan_object(item)
            elif hasattr(obj, "__dict__"):
                scan_object(obj.__dict__)

        scan_object(self.AnalysisContext)
        scan_object(self.Metadata)


@dataclass(frozen=True)
class FeedbackAnalysis:
    """
    Contains descriptive outcomes of a single feedback log assessment.
    """
    Strengths: List[str]
    Weaknesses: List[str]
    ImprovementAreas: List[str]
    ConfidenceEvaluation: str


@dataclass(frozen=True)
class LearningPerformanceRecord:
    """
    Performance log capturing multi-dimensional intelligence accuracy points over time.
    Supports historical comparison and trend analysis.
    """
    MetricName: str  # e.g., "DecisionConsistency", "ResearchReliability", etc.
    HistoricalValues: Dict[datetime, float] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningQualityMetrics:
    """
    Synthesized metrics tracking the global health and stability of the platform's layers.
    """
    DecisionConsistencyScore: float
    EvidenceQualityTrend: float
    ResearchStabilityScore: float
    RiskEvaluationStability: float
    OverallIntelligenceQuality: float


@dataclass(frozen=True)
class OptimizationReport:
    """
    Compiled feedback report containing performance trends, recurring issues,
    and parameter suggestions.
    """
    ReportId: str
    FeedbackSummary: str
    PerformanceTrends: Dict[str, List[float]]
    DetectedIssues: List[str]
    ImprovementSuggestions: List[Any]  # list of ImprovementSuggestion
    IntelligenceQualityMetrics: LearningQualityMetrics
    GeneratedAt: datetime = field(default_factory=datetime.now)
