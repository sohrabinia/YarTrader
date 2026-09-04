from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class OrderRequest:
    """Represents an order request definition block."""
    Symbol: str
    OrderType: str  # "Buy", "Sell", "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
    Volume: float
    TargetWeight: float = 0.0
    Price: Optional[float] = None
    StopLoss: Optional[float] = None
    TakeProfit: Optional[float] = None
    Deviation: int = 20
    Comment: str = "YarTrader Execution"
    Magic: int = 100001
    PositionTicket: Optional[int] = None  # Used when closing a specific position ticket


@dataclass(frozen=True)
class OrderResponse:
    """Represents order response block returned by adapters."""
    OrderId: Optional[str] = None  # Real MT5 Order Ticket (e.g. str(mt5_order_ticket)) or None if failed/unknown
    Symbol: str = "XAUUSD"
    Status: str = "Failed"  # e.g., "Placed", "Executed", "Rejected", "Failed"
    SubmittedAt: Optional[datetime] = None
    Retcode: Optional[int] = None
    Comment: str = ""
    DealTicket: Optional[str] = None
    PositionTicket: Optional[str] = None
    Price: Optional[float] = None
    Volume: Optional[float] = None
    RawResponse: Optional[Dict[str, Any]] = field(default=None)


@dataclass(frozen=True)
class ExecutionResult:
    """Represents a record outcome from execution processing."""
    ExecutionId: str
    Symbol: str
    Price: float
    FilledVolume: float
    ExecutedAt: datetime
    Commission: float = 0.0
    Swap: float = 0.0
    Profit: float = 0.0
    RawDeal: Optional[Dict[str, Any]] = field(default=None)
