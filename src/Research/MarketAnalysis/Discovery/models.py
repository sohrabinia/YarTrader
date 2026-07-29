from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MarketObservation:
    """Represents a single raw price-action state snapshot at a specific point in time."""
    Asset: str
    Timestamp: datetime
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float
    Timeframe: str


@dataclass(frozen=True)
class MarketSequence:
    """A series of consecutive raw market observations within a specific timeframe."""
    Asset: str
    Timeframe: str
    Observations: List[MarketObservation] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.Observations)


@dataclass(frozen=True)
class MarketEvent:
    """
    A discrete price movement event parsed from price sequences.
    Behavior is observed purely in points, durations, and reactions.
    """
    EventId: str
    Asset: str
    Timeframe: str
    StartTime: datetime
    EndTime: datetime
    PriceMovementPoints: float
    DurationCandles: int
    ConsecutiveCandlesCount: int
    Direction: str  # "upward", "downward", "neutral"
    RetracementPoints: float = 0.0
    RetracementDuration: int = 0


@dataclass
class PatternMemory:
    """
    A generalized pattern repository entry containing historical frequency
    and chronological outcome distributions (continuations vs. reversals).
    """
    PatternId: str
    Signature: str  # String representation of sequence structure (e.g. "up_12_down_3")
    Occurrences: int = 0
    ContinuationCount: int = 0
    ReversalCount: int = 0

    @property
    def continuation_probability(self) -> float:
        if self.Occurrences == 0:
            return 0.5
        return self.ContinuationCount / self.Occurrences

    @property
    def reversal_probability(self) -> float:
        if self.Occurrences == 0:
            return 0.5
        return self.ReversalCount / self.Occurrences


@dataclass(frozen=True)
class ExperienceMemory:
    """
    Represents an episodic learning memory containing a situation,
    the decision made, the future outcome, and the generated lesson.
    """
    MemoryId: str
    Timestamp: datetime
    SituationSignature: str
    Decision: str  # "BUY", "SELL", "WAIT"
    MaxFavorableMovement: float
    MaxAdverseMovement: float
    FinalResult: str  # "WIN", "LOSS", "NEUTRAL"
    Lesson: str


@dataclass
class VirtualTrade:
    """An internal, virtual trade simulation with risk boundaries and scenarios."""
    TradeId: str
    Asset: str
    Timeframe: str
    Direction: str  # "BUY", "SELL"
    EntryPrice: float
    StopLoss: float
    TargetPrice: float
    EntryTime: datetime
    ExpectedScenario: str
    State: str = "OPEN"  # "OPEN", "CLOSED"
    ExitPrice: Optional[float] = None
    ExitTime: Optional[Optional[datetime]] = None
    MaxFavorablePrice: float = 0.0
    MaxAdversePrice: float = 0.0

    def __post_init__(self) -> None:
        if self.MaxFavorablePrice == 0.0:
            self.MaxFavorablePrice = self.EntryPrice
        if self.MaxAdversePrice == 0.0:
            self.MaxAdversePrice = self.EntryPrice


@dataclass(frozen=True)
class SimulationResult:
    """The outcome of a simulated trading replay execution."""
    TradeId: str
    IsSuccess: bool
    MaxFavorableMovementPoints: float
    MaxAdverseMovementPoints: float
    FinalResult: str  # "WIN", "LOSS"
    FailureReason: Optional[str] = None


@dataclass(frozen=True)
class LearningRecord:
    """Tracks updates to the Pattern and Experience memory libraries."""
    RecordId: str
    CreatedAt: datetime
    SourceTradeId: str
    UpdatedPatternId: str
    PriorContinuationProb: float
    NewContinuationProb: float
    LessonLearned: str


@dataclass(frozen=True)
class AnalysisReport:
    """A live analysis report containing live observations, hypotheses, and QC results."""
    ReportId: str
    Asset: str
    Timestamp: datetime
    CurrentObservation: MarketObservation
    ActiveHypothesis: str
    SimulatedTradeCount: int
    QCScore: float  # 0.0 to 1.0 rating reasoning strength
    QCExplanation: str
