from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionIntelligenceContext:
    """
    Immutable, framework-independent context for advanced Decision Intelligence reasoning.
    Synthesizes insights, patterns, assessments, market conditions, and evidence.
    Strictly audited to prevent any execution-related trading/broker details.
    """
    ResearchInsights: List[Any] = field(default_factory=list)
    PatternObservations: List[Any] = field(default_factory=list)
    StrategyEvaluations: List[Any] = field(default_factory=list)
    RiskAssessments: List[Any] = field(default_factory=list)
    MarketConditions: Dict[str, Any] = field(default_factory=dict)
    HistoricalEvidence: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)
    MarketDataPoints: Optional[List[Any]] = None

    def __post_init__(self) -> None:
        # Strict safety check for execution leaking parameters
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for keyword in forbidden_keywords:
                    if keyword in lower_str:
                        raise ValidationException(
                            f"Safety Violation: DecisionIntelligenceContext contains forbidden execution-related keyword '{keyword}' in data: '{obj}'."
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

        scan_object(self.ResearchInsights)
        scan_object(self.PatternObservations)
        scan_object(self.StrategyEvaluations)
        scan_object(self.RiskAssessments)
        scan_object(self.MarketConditions)
        scan_object(self.HistoricalEvidence)
        scan_object(self.Metadata)


@dataclass(frozen=True)
class DecisionAnalysis:
    """
    Represents structured outcomes of a decision analyzer assessment.
    """
    Summary: str
    SupportingEvidence: Dict[str, Any]
    Confidence: float
    ReasoningMetadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionQualityScore:
    """
    Standardized multi-dimensional quality scoring for decisions.
    """
    OverallScore: float  # e.g. 0.0 to 1.0
    EvidenceQuality: float
    Consistency: float
    Reliability: float
    Metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConflictResolutionResult:
    """
    Holds outcomes when conflicting indicators across layers are resolved.
    """
    ConflictDetected: bool
    ConflictType: str  # e.g. "Research_vs_Risk", "Research_vs_Strategy", "Strategy_vs_Risk", "None"
    ConflictingSources: List[str] = field(default_factory=list)
    ResolutionExplanation: str = ""
    ConfidenceImpact: float = 0.0


@dataclass(frozen=True)
class DecisionEvidenceTrail:
    """
    A comprehensive trace of evidence used to form the decision.
    """
    DecisionId: str
    ResearchEvidence: List[Any] = field(default_factory=list)
    FeatureEvidence: List[Any] = field(default_factory=list)
    PatternEvidence: List[Any] = field(default_factory=list)
    StrategyEvidence: List[Any] = field(default_factory=list)
    RiskEvidence: List[Any] = field(default_factory=list)
    SupportingEvidence: Dict[str, Any] = field(default_factory=dict)
    CollectedAt: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class DecisionIntelligenceReport:
    """
    Compiled, production-quality analytical report representing the complete decision trail.
    """
    ReportId: str
    Context: DecisionIntelligenceContext
    State: str  # valid DecisionState
    IntelligenceSummary: str
    EvidenceTrail: DecisionEvidenceTrail
    QualityScore: DecisionQualityScore
    ConflictAnalysis: ConflictResolutionResult
    Confidence: float
    GeneratedAt: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class DecisionHistoryRecord:
    """
    Stored footprint of a finalized decision report, useful for continuous reinforcement.
    """
    RecordId: str
    Timestamp: datetime
    ContextSummary: str
    DecisionState: str
    Confidence: float
    EvidenceReferences: List[str] = field(default_factory=list)
    Metadata: Dict[str, Any] = field(default_factory=dict)
