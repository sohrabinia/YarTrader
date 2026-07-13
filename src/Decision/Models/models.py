from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

class DecisionState:
    """Standardized valid decision status states."""
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REVIEW_REQUIRED = "ReviewRequired"
    NO_ACTION = "NoAction"


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
class DecisionResult:
    """Represents the outcome of a decision evaluation workflow."""
    DecisionId: str
    Context: DecisionContext
    State: str  # must be a valid DecisionState (Approved, Rejected, ReviewRequired, NoAction)
    Reason: DecisionReason
    CreatedAt: datetime
