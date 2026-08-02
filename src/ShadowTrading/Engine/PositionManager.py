import logging
from datetime import datetime
from typing import List, Optional
from src.ShadowTrading.Domain.VirtualAccount import VirtualAccount
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionStatus

logger = logging.getLogger("PositionManager")

class PositionManager:
    """
    Orchestrates the virtual position lifecycle (Opening, Price Monitoring, and Exit evaluation).
    """
    def __init__(self, account: VirtualAccount) -> None:
        self.account = account

    def open_virtual_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        volume: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reason: str = "",
        confidence: float = 0.0,
        evidence: Optional[dict] = None,
        timeframe: str = "H1"
    ) -> VirtualPosition:
        """Instantiates and registers a new virtual position."""
        pos = VirtualPosition(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            confidence=confidence,
            evidence=evidence,
            timeframe=timeframe
        )
        self.account.add_position(pos)
        logger.info(f"Opened virtual position: {pos.position_id} {pos.direction} {pos.symbol} on {pos.timeframe} @ {pos.entry_price}")
        return pos

    def update_prices_and_evaluate(self, symbol: str, current_price: float) -> List[VirtualPosition]:
        """
        Updates current prices for all open positions of a symbol, evaluates stop-losses
        and take-profits, and returns any positions closed during this cycle.
        """
        closed_positions = []
        open_positions = [p for p in self.account.get_open_positions() if p.symbol == symbol]

        for pos in open_positions:
            pos.update_price(current_price)
            if pos.check_sl_tp():
                self.account.handle_position_closed(pos.position_id)
                closed_positions.append(pos)
                logger.info(f"Closed virtual position on TP/SL trigger: {pos.position_id} Result={pos.result.value if pos.result else 'None'} P/L={pos.profit_loss}")

        self.account.recalculate()
        return closed_positions
