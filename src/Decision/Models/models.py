from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

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
class ExecutableTradingContract:
    """
    Formal Phase C Executable Trading Contract governing execution parameters,
    style boundaries, timeframe constraints, and risk context.
    """
    trade_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_lots: float
    account_equity: float
    free_margin: float
    execution_timeframe: str = "M5"
    trading_style: str = "FAST_SCALP"  # "FAST_SCALP", "SCALP", "DAY_TRADING"
    campaign_id: Optional[str] = None
    leg_id: Optional[str] = None
    risk_pct: float = 2.0
    is_add_on: bool = False
    reason_codes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invalidation_condition: str = "STRUCTURAL_INVALIDATION"

    def validate_contract_rules(self) -> Dict[str, Any]:
        rejection_reasons = []

        if self.execution_timeframe.upper() != "M5":
            rejection_reasons.append(f"Execution timeframe '{self.execution_timeframe}' violates primary M5 contract.")

        allowed_styles = ["FAST_SCALP", "SCALP", "DAY_TRADING"]
        if self.trading_style.upper() not in allowed_styles:
            rejection_reasons.append(f"Trading style '{self.trading_style}' is forbidden. Allowed: {allowed_styles}.")

        if self.direction.upper() not in ["BUY", "SELL"]:
            rejection_reasons.append(f"Invalid direction '{self.direction}'. Must be BUY or SELL.")

        if self.account_equity <= 0:
            rejection_reasons.append("Account equity must be greater than zero.")

        if self.volume_lots < 0.01:
            rejection_reasons.append(f"Volume lots {self.volume_lots} below minimum bound 0.01.")

        if self.direction.upper() == "BUY":
            if self.stop_loss >= self.entry_price:
                rejection_reasons.append(f"Buy SL ({self.stop_loss}) must be below entry price ({self.entry_price}).")
            if self.take_profit <= self.entry_price:
                rejection_reasons.append(f"Buy TP ({self.take_profit}) must be above entry price ({self.entry_price}).")
        elif self.direction.upper() == "SELL":
            if self.stop_loss <= self.entry_price:
                rejection_reasons.append(f"Sell SL ({self.stop_loss}) must be above entry price ({self.entry_price}).")
            if self.take_profit >= self.entry_price:
                rejection_reasons.append(f"Sell TP ({self.take_profit}) must be below entry price ({self.entry_price}).")

        return {
            "is_valid": len(rejection_reasons) == 0,
            "rejection_reasons": rejection_reasons
        }


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
