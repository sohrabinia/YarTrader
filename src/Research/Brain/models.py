from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class MarketObservation:
    """Represents a raw data observation of the market."""
    symbol: str
    timeframe: str
    timestamp: datetime
    high: float
    low: float
    open_price: float
    close_price: float
    volume: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketObservation":
        return cls(
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            high=float(data["high"]),
            low=float(data["low"]),
            open_price=float(data["open_price"]),
            close_price=float(data["close_price"]),
            volume=float(data["volume"]),
            meta=data.get("meta", {})
        )


@dataclass
class MarketEvent:
    """Represents an objective price action event detected in the market sequence without subjective naming."""
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    price_change: float       # Points or absolute price change
    duration_candles: int     # Number of candles
    previous_sequence_len: int
    reaction_type: str        # e.g., "retracement", "extension", "stability"
    reaction_magnitude: float  # Absolute change in reaction
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["start_time"] = self.start_time.isoformat()
        d["end_time"] = self.end_time.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketEvent":
        return cls(
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            price_change=float(data["price_change"]),
            duration_candles=int(data["duration_candles"]),
            previous_sequence_len=int(data["previous_sequence_len"]),
            reaction_type=data["reaction_type"],
            reaction_magnitude=float(data["reaction_magnitude"]),
            meta=data.get("meta", {})
        )


@dataclass
class MarketSequence:
    """Represents an ordered chronological chain of market observations and events."""
    symbol: str
    timeframe: str
    observations: List[MarketObservation] = field(default_factory=list)
    events: List[MarketEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "observations": [obs.to_dict() for obs in self.observations],
            "events": [evt.to_dict() for evt in self.events]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketSequence":
        return cls(
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            observations=[MarketObservation.from_dict(obs) for obs in data.get("observations", [])],
            events=[MarketEvent.from_dict(evt) for evt in data.get("events", [])]
        )


@dataclass
class PatternMemory:
    """Stores repeating market structure structures and similar historical sequences with their outcomes."""
    pattern_id: str
    sequence_signature: List[float]  # Normalized price change sequence signature
    occurrences_count: int
    continuation_count: int
    reversal_count: int
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternMemory":
        return cls(
            pattern_id=data["pattern_id"],
            sequence_signature=data["sequence_signature"],
            occurrences_count=int(data["occurrences_count"]),
            continuation_count=int(data["continuation_count"]),
            reversal_count=int(data["reversal_count"]),
            outcomes=data.get("outcomes", []),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class ExperienceMemory:
    """Stores situational learning context: Situation, Decision, Outcome, and Lesson."""
    experience_id: str
    symbol: str
    timeframe: str
    timestamp: datetime
    situation_signature: List[float]
    decision_action: str            # BUY, SELL, WAIT
    outcome_result: str              # SUCCESS, FAILURE, NEUTRAL
    lesson_feedback: str             # Contextual lesson learned from simulated execution
    max_favorable_excursion: float   # Max positive movement
    max_adverse_excursion: float     # Max negative movement
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceMemory":
        return cls(
            experience_id=data["experience_id"],
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            situation_signature=data["situation_signature"],
            decision_action=data["decision_action"],
            outcome_result=data["outcome_result"],
            lesson_feedback=data["lesson_feedback"],
            max_favorable_excursion=float(data["max_favorable_excursion"]),
            max_adverse_excursion=float(data["max_adverse_excursion"]),
            meta=data.get("meta", {})
        )


@dataclass
class VirtualTrade:
    """Represents a virtual execution simulation trade record."""
    trade_id: str
    symbol: str
    timeframe: str
    entry_time: datetime
    entry_price: float
    decision_action: str  # BUY, SELL, WAIT
    virtual_stop: float
    virtual_target: float
    expected_scenario: str
    status: str = "OPEN"  # OPEN, CLOSED
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    max_favorable_movement: float = 0.0
    max_adverse_movement: float = 0.0
    final_result: Optional[str] = None  # SUCCESS, FAILURE
    reason_of_failure: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["entry_time"] = self.entry_time.isoformat()
        if self.exit_time:
            d["exit_time"] = self.exit_time.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualTrade":
        return cls(
            trade_id=data["trade_id"],
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            entry_time=datetime.fromisoformat(data["entry_time"]),
            entry_price=float(data["entry_price"]),
            decision_action=data["decision_action"],
            virtual_stop=float(data["virtual_stop"]),
            virtual_target=float(data["virtual_target"]),
            expected_scenario=data["expected_scenario"],
            status=data["status"],
            exit_time=datetime.fromisoformat(data["exit_time"]) if data.get("exit_time") else None,
            exit_price=float(data["exit_price"]) if data.get("exit_price") is not None else None,
            max_favorable_movement=float(data["max_favorable_movement"]),
            max_adverse_movement=float(data["max_adverse_movement"]),
            final_result=data.get("final_result"),
            reason_of_failure=data.get("reason_of_failure")
        )


@dataclass
class SimulationResult:
    """Groups results compiled over a backtest/simulation replay loop."""
    simulation_id: str
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    net_points: float
    average_favorable_excursion: float
    average_adverse_excursion: float
    trades: List[VirtualTrade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["start_time"] = self.start_time.isoformat()
        d["end_time"] = self.end_time.isoformat()
        d["trades"] = [t.to_dict() for t in self.trades]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationResult":
        return cls(
            simulation_id=data["simulation_id"],
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            total_trades=int(data["total_trades"]),
            winning_trades=int(data["winning_trades"]),
            losing_trades=int(data["losing_trades"]),
            net_points=float(data["net_points"]),
            average_favorable_excursion=float(data["average_favorable_excursion"]),
            average_adverse_excursion=float(data["average_adverse_excursion"]),
            trades=[VirtualTrade.from_dict(t) for t in data.get("trades", [])]
        )


@dataclass
class LearningRecord:
    """Chronicles learning improvements and pattern effectiveness adjustments."""
    record_id: str
    timestamp: datetime
    symbol: str
    learned_patterns_count: int
    successful_patterns: List[str]
    failed_patterns: List[str]
    context_rules_discovered: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningRecord":
        return cls(
            record_id=data["record_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbol=data["symbol"],
            learned_patterns_count=int(data["learned_patterns_count"]),
            successful_patterns=data.get("successful_patterns", []),
            failed_patterns=data.get("failed_patterns", []),
            context_rules_discovered=data.get("context_rules_discovered", {})
        )


@dataclass
class AnalysisReport:
    """Represents the final, read-only Newborn Market Discovery Brain live analysis output."""
    report_id: str
    symbol: str
    timestamp: datetime
    latest_observations: List[Dict[str, Any]]
    active_hypotheses: List[Dict[str, Any]]
    simulated_trades: List[Dict[str, Any]]
    reasoning_quality_score: float
    is_read_only_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisReport":
        return cls(
            report_id=data["report_id"],
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            latest_observations=data.get("latest_observations", []),
            active_hypotheses=data.get("active_hypotheses", []),
            simulated_trades=data.get("simulated_trades", []),
            reasoning_quality_score=float(data["reasoning_quality_score"]),
            is_read_only_compliant=bool(data.get("is_read_only_compliant", True))
        )
