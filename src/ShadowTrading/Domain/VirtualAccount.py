import json
import os
import logging
from typing import Any, Dict, List, Optional
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionStatus

logger = logging.getLogger("VirtualAccount")

class VirtualAccount:
    """
    Manages the financial and position state of a virtual non-trading paper/shadow account.
    Calculates balance, equity, margin, fees, and handles persistence to survive restarts.
    """
    def __init__(self, initial_balance: float = 1000.0, account_id: str = "YARTRADER-PAPER-001") -> None:
        self.account_id = account_id
        self.initial_balance = float(initial_balance)
        self.cash_balance = float(initial_balance)
        self.equity = float(initial_balance)
        self.available_cash = float(initial_balance)
        self.used_margin = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.fees = 0.0
        self.slippage = 0.0
        self.positions: Dict[str, VirtualPosition] = {}

        # Default storage path
        self.persistence_path = os.path.join("runtime_logs", "paper_account.json")
        self.load_state()

    def get_open_positions(self) -> List[VirtualPosition]:
        return [p for p in self.positions.values() if p.status in [PositionStatus.OPEN, "MONITORING", "FILLED"]]

    def get_closed_positions(self) -> List[VirtualPosition]:
        return [p for p in self.positions.values() if p.status == PositionStatus.CLOSED]

    def get_pending_orders(self) -> List[VirtualPosition]:
        return [p for p in self.positions.values() if p.status == "PENDING"]

    def add_position(self, position: VirtualPosition) -> None:
        self.positions[position.position_id] = position
        self.recalculate()
        self.save_state()

    def recalculate(self) -> None:
        """Recalculates current account equity and margins based on open positions and PnL."""
        open_pos = self.get_open_positions()
        closed_pos = self.get_closed_positions()

        self.unrealized_pnl = sum(p.profit_loss for p in open_pos)
        self.realized_pnl = sum(p.profit_loss for p in closed_pos)

        # cash_balance accumulates realized profits/losses minus fees
        self.fees = sum(getattr(p, "fees", 0.0) for p in self.positions.values())
        self.slippage = sum(getattr(p, "slippage", 0.0) for p in self.positions.values())

        # Recalculate cash_balance = initial_balance + realized_pnl - fees
        self.cash_balance = self.initial_balance + self.realized_pnl - self.fees

        self.equity = self.cash_balance + self.unrealized_pnl
        # Simple simulated margin calculation: 5% of entry value per open position
        self.used_margin = sum(p.entry_price * p.volume * 0.05 for p in open_pos)
        self.available_cash = self.equity - self.used_margin

    def handle_position_closed(self, position_id: str) -> None:
        """Processes a newly closed position, recalculating states."""
        pos = self.positions.get(position_id)
        if pos and pos.status == PositionStatus.CLOSED:
            self.recalculate()
            self.save_state()

    def load_state(self) -> None:
        """Loads persistent account and position states from disk to ensure restart recovery."""
        if not os.path.exists(self.persistence_path):
            return

        try:
            with open(self.persistence_path, "r") as f:
                data = json.load(f)

            self.account_id = data.get("account_id", self.account_id)
            self.initial_balance = data.get("initial_balance", self.initial_balance)
            self.cash_balance = data.get("cash_balance", self.cash_balance)
            self.equity = data.get("equity", self.equity)
            self.available_cash = data.get("available_cash", self.available_cash)
            self.used_margin = data.get("used_margin", self.used_margin)
            self.unrealized_pnl = data.get("unrealized_pnl", self.unrealized_pnl)
            self.realized_pnl = data.get("realized_pnl", self.realized_pnl)
            self.fees = data.get("fees", self.fees)
            self.slippage = data.get("slippage", self.slippage)

            self.positions = {}
            for pos_dict in data.get("positions", []):
                pos = VirtualPosition(
                    symbol=pos_dict["symbol"],
                    direction=pos_dict["direction"],
                    entry_price=pos_dict["entry_price"],
                    volume=pos_dict.get("volume", 1.0),
                    stop_loss=pos_dict.get("stop_loss"),
                    take_profit=pos_dict.get("take_profit"),
                    reason=pos_dict.get("reason", ""),
                    confidence=pos_dict.get("confidence", 0.0),
                    evidence=pos_dict.get("evidence"),
                    position_id=pos_dict["position_id"],
                    timeframe=pos_dict.get("timeframe", "H1")
                )
                pos.status = pos_dict["status"]
                pos.profit_loss = pos_dict.get("profit_loss", 0.0)
                pos.current_price = pos_dict.get("current_price", pos.entry_price)
                pos.fees = pos_dict.get("fees", 0.0)
                pos.slippage = pos_dict.get("slippage", 0.0)
                pos.account_id = pos_dict.get("account_id", self.account_id)
                pos.mode = pos_dict.get("mode", "PAPER")
                pos.strategy_id = pos_dict.get("strategy_id", "strat-v3")
                pos.strategy_version = pos_dict.get("strategy_version", "strat-v3.2.1-heuristic")
                pos.decision_id = pos_dict.get("decision_id")

                self.positions[pos.position_id] = pos

            self.recalculate()
            logger.info(f"Successfully loaded and restored account '{self.account_id}' state from storage.")
        except Exception as e:
            logger.error(f"Error loading persistent account state: {e}")

    def save_state(self) -> None:
        """Saves current state to JSON file persistently."""
        try:
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            self.recalculate()

            serialized_positions = []
            for p in self.positions.values():
                d = p.to_dict()
                # Ensure custom fields are included in output
                d["fees"] = getattr(p, "fees", 0.0)
                d["slippage"] = getattr(p, "slippage", 0.0)
                d["account_id"] = getattr(p, "account_id", self.account_id)
                d["mode"] = getattr(p, "mode", "PAPER")
                d["strategy_id"] = getattr(p, "strategy_id", "strat-v3")
                d["strategy_version"] = getattr(p, "strategy_version", "strat-v3.2.1-heuristic")
                d["decision_id"] = getattr(p, "decision_id", None)
                serialized_positions.append(d)

            data = {
                "account_id": self.account_id,
                "initial_balance": self.initial_balance,
                "cash_balance": self.cash_balance,
                "equity": self.equity,
                "available_cash": self.available_cash,
                "used_margin": self.used_margin,
                "unrealized_pnl": self.unrealized_pnl,
                "realized_pnl": self.realized_pnl,
                "fees": self.fees,
                "slippage": self.slippage,
                "positions": serialized_positions
            }

            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving account state: {e}")

    def to_dict(self) -> Dict[str, Any]:
        self.recalculate()
        open_trades = [p.to_dict() for p in self.get_open_positions()]
        closed_trades = [p.to_dict() for p in self.get_closed_positions()]
        pending_orders = [p.to_dict() for p in self.get_pending_orders()]
        return {
            "account_id": self.account_id,
            "initial_balance": round(self.initial_balance, 2),
            "cash_balance": round(self.cash_balance, 2),
            "equity": round(self.equity, 2),
            "available_cash": round(self.available_cash, 2),
            "used_margin": round(self.used_margin, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "fees": round(self.fees, 2),
            "slippage": round(self.slippage, 2),
            "open_positions_count": len(open_trades),
            "closed_positions_count": len(closed_trades),
            "pending_orders_count": len(pending_orders),
            "open_positions": open_trades,
            "closed_positions": closed_trades,
            "pending_orders": pending_orders
        }
