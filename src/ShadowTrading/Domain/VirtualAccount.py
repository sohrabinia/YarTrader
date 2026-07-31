from typing import Any, Dict, List, Optional
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionStatus

class VirtualAccount:
    """
    Manages the financial and position state of a virtual non-trading shadow account.
    Calculates balance, floating PnL, and live account equity.
    """
    def __init__(self, initial_balance: float = 10000.0) -> None:
        self.balance = float(initial_balance)
        self.equity = float(initial_balance)
        self.positions: Dict[str, VirtualPosition] = {}

    def get_open_positions(self) -> List[VirtualPosition]:
        return [p for p in self.positions.values() if p.status != PositionStatus.CLOSED]

    def get_closed_positions(self) -> List[VirtualPosition]:
        return [p for p in self.positions.values() if p.status == PositionStatus.CLOSED]

    def add_position(self, position: VirtualPosition) -> None:
        self.positions[position.position_id] = position
        self.recalculate()

    def recalculate(self) -> None:
        """Recalculates current account equity based on open position floating profits/losses."""
        open_pnl = sum(p.profit_loss for p in self.get_open_positions())
        # Equity is balance + floating open profits/losses
        self.equity = self.balance + open_pnl

    def handle_position_closed(self, position_id: str) -> None:
        """Processes a newly closed position, adding its finalized profit/loss to the balance."""
        pos = self.positions.get(position_id)
        if pos and pos.status == PositionStatus.CLOSED:
            self.balance += pos.profit_loss
            self.recalculate()

    def to_dict(self) -> Dict[str, Any]:
        self.recalculate()
        open_trades = [p.to_dict() for p in self.get_open_positions()]
        closed_trades = [p.to_dict() for p in self.get_closed_positions()]
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "open_positions_count": len(open_trades),
            "closed_positions_count": len(closed_trades),
            "open_positions": open_trades,
            "closed_positions": closed_trades
        }
