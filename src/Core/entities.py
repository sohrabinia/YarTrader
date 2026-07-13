from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass(frozen=True)
class Asset:
    """Represents an investment asset under management or analysis."""
    symbol: str
    name: str
    asset_class: str  # e.g., "Equity", "Fixed_Income", "Crypto", "Forex"
    is_active: bool = True

@dataclass(frozen=True)
class MarketData:
    """Represents a point-in-time pricing and liquidity snapshot of an asset."""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None

@dataclass(frozen=True)
class RiskParameters:
    """Represents risk constraints and tolerance parameters."""
    max_single_asset_exposure: float  # e.g., 0.20 for 20% limit
    max_portfolio_drawdown: float     # e.g., 0.15 for 15% stop limit
    target_volatility_limit: float    # e.g., 0.25 annual limit
    leverage_allowed: bool = False

@dataclass(frozen=True)
class DecisionReport:
    """
    Represents an autonomous financial intelligence decision / portfolio allocation model.
    Note: Strictly contains research/allocation decisions; no buy/sell trading triggers are generated here.
    """
    decision_id: str
    target_weights: Dict[str, float]  # mapping of symbol to target weight (e.g. {"AAPL": 0.15})
    reasoning: str
    risk_evaluation: str
    timestamp: datetime
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class PerformanceMetric:
    """Represents continuous learning feedback and tracking metric records."""
    metric_id: str
    metric_name: str
    value: float
    calculated_at: datetime
    context: Dict[str, str] = field(default_factory=dict)
