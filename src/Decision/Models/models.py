from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

class DecisionState:
    """Standardized valid decision status states."""
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REVIEW_REQUIRED = "ReviewRequired"
    NO_ACTION = "NoAction"
    INSUFFICIENT_DATA = "InsufficientData"


@dataclass(frozen=True)
class DecisionContext:
    """Represents the research, metadata, and environment inputs of a decision workflow."""
    StrategyId: str
    AssetWeights: Dict[str, float]
    TargetRiskProfile: str
    Parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionReason:
    """Represents logical justification and evaluation comments."""
    AnalysisSummary: str
    RiskAuditStatus: str
    ConfidenceScore: float


@dataclass(frozen=True)
class TradeDecisionSchema:
    """Standardized trade decision schema containing complete risk/reward and learning metadata."""
    symbol: str
    signal_timeframe: str
    context_timeframe: str
    entry: float
    stop_loss: float
    take_profit: float
    spread_cost: float
    risk: float
    reward: float
    real_rr: float
    historical_win_rate: float
    expected_value: float
    decision: str  # ALLOW or NO_TRADE


@dataclass(frozen=True)
class DecisionResult:
    """Represents the outcome of a decision evaluation workflow."""
    DecisionId: str
    Context: DecisionContext
    State: str  # must be a valid DecisionState (Approved, Rejected, ReviewRequired, NoAction)
    Reason: DecisionReason
    CreatedAt: datetime
    TradeSchema: TradeDecisionSchema | None = None


@dataclass(frozen=True)
class AutonomousTradingDecision:
    """
    Immutable, traceable, auditable, and versioned single source of truth contract
    for autonomous trading decisions across Research, Decision, Risk, Execution,
    Lifecycle, and Learning pipelines.
    """
    decision_id: str
    cycle_id: str
    action: str  # BUY | SELL | WAIT | AVOID
    symbol: str
    timeframe: str
    entry: float
    stop_loss: float
    take_profit: float
    volume: float
    risk_reward: float
    confidence: float
    reasoning: list[str] | str
    evidence: Dict[str, Any]
    risk_status: str  # APPROVED | REJECTED | PENDING
    execution_status: str  # INITIATED | SUBMITTED | REJECTED | FILLED | SKIPPED
    configuration_version: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        reasoning_list = self.reasoning if isinstance(self.reasoning, list) else [str(self.reasoning)]
        return {
            "decision_id": self.decision_id,
            "cycle_id": self.cycle_id,
            "action": self.action,
            "symbol": self.symbol.upper(),
            "timeframe": self.timeframe.upper(),
            "entry": float(self.entry),
            "stop_loss": float(self.stop_loss),
            "take_profit": float(self.take_profit),
            "volume": float(self.volume),
            "risk_reward": float(self.risk_reward),
            "confidence": float(self.confidence),
            "reasoning": reasoning_list,
            "evidence": self.evidence if isinstance(self.evidence, dict) else {},
            "risk_status": self.risk_status,
            "execution_status": self.execution_status,
            "configuration_version": self.configuration_version,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AutonomousTradingDecision":
        return cls(
            decision_id=d["decision_id"],
            cycle_id=d.get("cycle_id", f"cycle-{d['decision_id']}"),
            action=d["action"].upper(),
            symbol=d["symbol"].upper(),
            timeframe=d["timeframe"].upper(),
            entry=float(d.get("entry", 0.0)),
            stop_loss=float(d.get("stop_loss", 0.0)),
            take_profit=float(d.get("take_profit", 0.0)),
            volume=float(d.get("volume", 0.01)),
            risk_reward=float(d.get("risk_reward", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            reasoning=d.get("reasoning", []),
            evidence=d.get("evidence", {}),
            risk_status=d.get("risk_status", "APPROVED"),
            execution_status=d.get("execution_status", "INITIATED"),
            configuration_version=d.get("configuration_version", "1.2.0"),
            timestamp=d.get("timestamp", datetime.now().isoformat())
        )
