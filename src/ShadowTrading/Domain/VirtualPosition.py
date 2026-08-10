import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from src.ShadowTrading.Domain.TradeState import PositionStatus, PositionResult

class VirtualPosition:
    """
    Represents an active, pending, or closed virtual shadow/paper position.
    Strictly simulated; has no active trading connection or real capital.
    Supports BACKTEST, PAPER, SHADOW, and LIVE modes.
    """
    def __init__(
        self,
        symbol: str,
        direction: str,  # BUY or SELL
        entry_price: float,
        volume: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reason: str = "",
        confidence: float = 0.0,
        evidence: Optional[Dict[str, Any]] = None,
        position_id: Optional[str] = None,
        open_time: Optional[datetime] = None,
        timeframe: str = "H1",
        account_id: str = "YARTRADER-PAPER-001",
        mode: str = "PAPER",
        strategy_id: str = "strat-v3",
        strategy_version: str = "strat-v3.2.1-heuristic",
        decision_id: Optional[str] = None
    ) -> None:
        self.position_id = position_id or f"vpos-{uuid.uuid4().hex[:8]}"
        self.account_id = account_id
        self.symbol = symbol
        self.timeframe = timeframe.upper()
        self.direction = direction.upper()  # BUY or SELL
        self.entry_price = float(entry_price)
        self.current_price = float(entry_price)
        self.volume = float(volume)

        self.open_time = open_time or datetime.now()
        self.created_at = self.open_time.isoformat()
        self.filled_at = None
        self.close_time: Optional[datetime] = None

        # SL/TP Setup: If not provided, set reasonable defaults (e.g. 15 points)
        self.stop_loss = float(stop_loss) if stop_loss is not None else self._calculate_default_sl()
        self.take_profit = float(take_profit) if take_profit is not None else self._calculate_default_tp()

        # Operational Mode and Tracking
        self.mode = mode.upper()  # BACKTEST, PAPER, SHADOW, LIVE
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        self.decision_id = decision_id or f"dec-{uuid.uuid4().hex[:8]}"

        # Costs and Fees
        self.fees = 2.0 * self.volume  # realistic standard fee of $2 per lot
        self.slippage = 0.1 * self.volume  # realistic slippage simulation

        # Status matching both Position and Order structures
        self.status = PositionStatus.OPEN  # Default to OPEN / FILLED for compatibility
        self.result: Optional[PositionResult] = None
        self.profit_loss: float = 0.0
        self.reason = reason
        self.confidence = float(confidence)
        self.evidence = evidence or {}

    def _calculate_default_sl(self) -> float:
        points_offset = 15.0 if "JPY" not in self.symbol else 1.0
        if "XAU" in self.symbol:
            points_offset = 15.0
        if self.direction == "BUY":
            return self.entry_price - points_offset
        return self.entry_price + points_offset

    def _calculate_default_tp(self) -> float:
        points_offset = 30.0 if "JPY" not in self.symbol else 2.0
        if "XAU" in self.symbol:
            points_offset = 30.0
        if self.direction == "BUY":
            return self.entry_price + points_offset
        return self.entry_price - points_offset

    def update_price(self, price: float) -> None:
        """Updates the current market price and recalculates floating profit/loss."""
        self.current_price = float(price)
        if self.status == PositionStatus.OPEN:
            self.status = PositionStatus.MONITORING

        # Contract multipliers for standard PnL computation representation
        multiplier = 100.0 if "XAU" in self.symbol else 10000.0
        if "JPY" in self.symbol:
            multiplier = 100.0

        if self.direction == "BUY":
            self.profit_loss = (self.current_price - self.entry_price) * multiplier * self.volume
        else:
            self.profit_loss = (self.entry_price - self.current_price) * multiplier * self.volume

    def check_sl_tp(self) -> bool:
        """
        Checks if take-profit or stop-loss levels have been breached.
        Closes position and returns True if closed.
        """
        if self.status == PositionStatus.CLOSED:
            return False

        closed = False
        if self.direction == "BUY":
            if self.current_price >= self.take_profit:
                self.close(PositionResult.WIN)
                closed = True
            elif self.current_price <= self.stop_loss:
                self.close(PositionResult.LOSS)
                closed = True
        else:  # SELL
            if self.current_price <= self.take_profit:
                self.close(PositionResult.WIN)
                closed = True
            elif self.current_price >= self.stop_loss:
                self.close(PositionResult.LOSS)
                closed = True
        return closed

    def close(self, result: PositionResult, close_price: Optional[float] = None, close_time: Optional[datetime] = None) -> None:
        """Closes the position and seals its P/L state."""
        if self.status == PositionStatus.CLOSED:
            return

        self.status = PositionStatus.CLOSED
        self.result = result
        self.close_time = close_time or datetime.now()
        if close_price is not None:
            self.update_price(close_price)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "volume": self.volume,
            "open_time": self.open_time.isoformat(),
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "result": self.result.value if (self.result and hasattr(self.result, "value")) else str(self.result) if self.result else None,
            "profit_loss": round(self.profit_loss, 2),
            "reason": self.reason,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "mode": self.mode,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "decision_id": self.decision_id,
            "created_at": self.created_at,
            "filled_at": self.filled_at,
            "fees": self.fees,
            "slippage": self.slippage
        }
