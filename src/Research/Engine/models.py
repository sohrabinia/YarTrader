from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from src.Research.MarketAnalysis.Models.models import MarketObservation, MarketInsight

@dataclass(frozen=True)
class PatternObservation:
    """Represents a passive, detected historical behavioral pattern in market feature dynamics."""
    PatternName: str
    Description: str
    Confidence: float
    Timestamp: datetime
    MatchedFeatures: List[str] = field(default_factory=list)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_name(self) -> str:
        return self.PatternName

    @property
    def description(self) -> str:
        return self.Description

    @property
    def confidence(self) -> float:
        return self.Confidence

    @property
    def timestamp(self) -> datetime:
        return self.Timestamp

    @property
    def matched_features(self) -> List[str]:
        return self.MatchedFeatures

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.Metadata


@dataclass(frozen=True)
class ResearchReport:
    """Represents a finalized structural Research Report compiling observations, patterns, and insights."""
    ReportId: str
    AssetId: str
    StartTime: datetime
    EndTime: datetime
    Observations: List[MarketObservation] = field(default_factory=list)
    Patterns: List[PatternObservation] = field(default_factory=list)
    Insights: List[MarketInsight] = field(default_factory=list)
    Metadata: Dict[str, Any] = field(default_factory=dict)
    GeneratedAt: datetime = field(default_factory=datetime.now)

    @property
    def report_id(self) -> str:
        return self.ReportId

    @property
    def asset_id(self) -> str:
        return self.AssetId

    @property
    def start_time(self) -> datetime:
        return self.StartTime

    @property
    def end_time(self) -> datetime:
        return self.EndTime

    @property
    def observations(self) -> List[MarketObservation]:
        return self.Observations

    @property
    def patterns(self) -> List[PatternObservation]:
        return self.Patterns

    @property
    def insights(self) -> List[MarketInsight]:
        return self.Insights

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.Metadata

    @property
    def generated_at(self) -> datetime:
        return self.GeneratedAt
