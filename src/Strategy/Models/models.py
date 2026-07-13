from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

@dataclass(frozen=True)
class StrategyDefinition:
    """
    Represents a strategy concept definition.
    Note: Contains only metadata definitions; strictly no trading execution rules.
    """
    Id: str
    Name: str
    Description: str
    CreatedAt: datetime
    Version: str
    Status: str  # e.g., "Draft", "Approved", "Deprecated"

    @property
    def id(self) -> str:
        return self.Id

    @property
    def name(self) -> str:
        return self.Name

    @property
    def description(self) -> str:
        return self.Description

    @property
    def created_at(self) -> datetime:
        return self.CreatedAt

    @property
    def version(self) -> str:
        return self.Version

    @property
    def status(self) -> str:
        return self.Status


@dataclass(frozen=True)
class StrategyCandidate:
    """Represents a candidate strategy concept under study."""
    Id: str
    Name: str
    Description: str
    ResearchContext: Dict[str, Any]
    CreatedAt: datetime
    EvaluationStatus: str  # e.g., "Pending", "Evaluating", "Accepted"

    @property
    def id(self) -> str:
        return self.Id

    @property
    def name(self) -> str:
        return self.Name

    @property
    def description(self) -> str:
        return self.Description

    @property
    def research_context(self) -> Dict[str, Any]:
        return self.ResearchContext

    @property
    def created_at(self) -> datetime:
        return self.CreatedAt

    @property
    def evaluation_status(self) -> str:
        return self.EvaluationStatus


@dataclass(frozen=True)
class StrategyScore:
    """Represents strategy assessment score breakdown across criteria."""
    OverallScore: float  # e.g., 0.0 to 1.0
    Confidence: float     # e.g., 0.0 to 1.0
    Criteria: Dict[str, float]  # mapping of criteria (Stability, Complexity, etc.) to rating

    @property
    def overall_score(self) -> float:
        return self.OverallScore

    @property
    def confidence(self) -> float:
        return self.Confidence

    @property
    def criteria(self) -> Dict[str, float]:
        return self.Criteria


@dataclass(frozen=True)
class StrategyEvaluation:
    """Represents strategy evaluation feedback information."""
    StrategyId: str
    Score: StrategyScore
    EvaluationNotes: str
    EvaluatedAt: datetime

    @property
    def strategy_id(self) -> str:
        return self.StrategyId

    @property
    def score(self) -> StrategyScore:
        return self.Score

    @property
    def evaluation_notes(self) -> str:
        return self.EvaluationNotes

    @property
    def evaluated_at(self) -> datetime:
        return self.EvaluatedAt
