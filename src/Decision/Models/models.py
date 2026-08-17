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
