from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

@dataclass
class CampaignLeg:
    """Represents an individual position leg within a multi-leg trade campaign."""
    leg_id: str
    campaign_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_lots: float
    risk_pct: float  # e.g., 2.0 for initial leg, 1.0 for add-on leg
    risk_amount_usd: float
    margin_required_usd: float
    effective_be_price: float
    is_effective_risk_free: bool = False
    status: str = "ACTIVE"  # "ACTIVE", "PROTECTED", "CLOSED"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    setup: str = "M5_STRUCTURAL_SETUP"
    zone: str = "RTM_BASE_NODE"
    reason_codes: List[str] = field(default_factory=list)


@dataclass
class TradeCampaign:
    """Represents an overarching structured trading campaign containing one or more legs."""
    campaign_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    status: str = "ACTIVE"  # "ACTIVE", "SETTLED", "FLATTENED"
    legs: List[CampaignLeg] = field(default_factory=list)
    total_locked_profit_usd: float = 0.0
    total_current_risk_usd: float = 0.0
    max_risk_pct: float = 2.0  # Initial risk cap
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settled_at: Optional[datetime] = None
    settlement_reason: Optional[str] = None

    @property
    def active_legs(self) -> List[CampaignLeg]:
        return [leg for leg in self.legs if leg.status in ["ACTIVE", "PROTECTED"]]

    @property
    def all_legs_effective_risk_free(self) -> bool:
        active = self.active_legs
        if not active:
            return False
        return all(leg.is_effective_risk_free for leg in active)
