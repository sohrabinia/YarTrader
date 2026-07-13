from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

@dataclass(frozen=True)
class MarketObservation:
    """Represents an observed market state block."""
    Asset: str
    Timestamp: datetime
    Observations: Dict[str, Any]
    Source: str

    @property
    def asset(self) -> str:
        return self.Asset

    @property
    def timestamp(self) -> datetime:
        return self.Timestamp

    @property
    def observations(self) -> Dict[str, Any]:
        return self.Observations

    @property
    def source(self) -> str:
        return self.Source


@dataclass(frozen=True)
class ResearchRequest:
    """Defines a research task/request structure."""
    Asset: str
    StartTime: datetime
    EndTime: datetime
    Context: Dict[str, Any] = field(default_factory=dict)

    @property
    def asset(self) -> str:
        return self.Asset

    @property
    def start_time(self) -> datetime:
        return self.StartTime

    @property
    def end_time(self) -> datetime:
        return self.EndTime

    @property
    def context(self) -> Dict[str, Any]:
        return self.Context


@dataclass(frozen=True)
class ResearchResult:
    """Represents the output findings from a research task."""
    Request: ResearchRequest
    Findings: Dict[str, Any]
    ConfidenceScore: float
    CreatedAt: datetime

    @property
    def request(self) -> ResearchRequest:
        return self.Request

    @property
    def findings(self) -> Dict[str, Any]:
        return self.Findings

    @property
    def confidence_score(self) -> float:
        return self.ConfidenceScore

    @property
    def created_at(self) -> datetime:
        return self.CreatedAt


@dataclass(frozen=True)
class MarketInsight:
    """Represents a structured analytical market insight."""
    Category: str  # e.g., "Trend", "Volatility", "Liquidity"
    Description: str
    Confidence: float
    CreatedAt: datetime

    @property
    def category(self) -> str:
        return self.Category

    @property
    def description(self) -> str:
        return self.Description

    @property
    def confidence(self) -> float:
        return self.Confidence

    @property
    def created_at(self) -> datetime:
        return self.CreatedAt
