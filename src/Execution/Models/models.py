from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OrderRequest:
    """Represents a passive, parameter-driven order definition block."""
    Symbol: str
    OrderType: str  # e.g., "Buy", "Sell" (as a metadata descriptor)
    Volume: float
    TargetWeight: float


@dataclass(frozen=True)
class OrderResponse:
    """Represents a mock order response block returned by adapters."""
    OrderId: str
    Symbol: str
    Status: str  # e.g., "MockPlaced", "Rejected"
    SubmittedAt: datetime


@dataclass(frozen=True)
class ExecutionResult:
    """Represents a passive record outcome from execution processing simulations."""
    ExecutionId: str
    Symbol: str
    Price: float
    FilledVolume: float
    ExecutedAt: datetime
