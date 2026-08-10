import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.ShadowTrading.Domain.VirtualAccount import VirtualAccount
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Engine.PositionManager import PositionManager
from src.ShadowTrading.Services.TradeEvaluator import TradeEvaluator
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem

logger = logging.getLogger("ShadowTradingEngine")

class ShadowTradingEngine:
    """
    Unified Orchestrator and API Interface for the TradeYar Shadow/Paper Trading Engine.
    Handles simulated account tracking, position lifecycles, real-time pricing updates,
    and automatic Judge & Memory learning loop integration.
    """
    _instance: Optional["ShadowTradingEngine"] = None

    @classmethod
    def get_instance(cls, initial_balance: float = 1000.0) -> "ShadowTradingEngine":
        if cls._instance is None:
            cls._instance = cls(initial_balance)
        return cls._instance

    def __init__(self, initial_balance: float = 1000.0) -> None:
        # Load or initialize the persistent paper account
        self.account = VirtualAccount(initial_balance, account_id="YARTRADER-PAPER-001")
        self.position_manager = PositionManager(self.account)
        self.judge = JudgeBrain()
        self.memory_system = MarketMemorySystem()
        self.trade_evaluator = TradeEvaluator(self.judge, self.memory_system)

    def reset_account(self, balance: float = 1000.0) -> None:
        """Resets the account state for fresh testing or initialization and persists it."""
        self.account = VirtualAccount(balance, account_id="YARTRADER-PAPER-001")
        self.position_manager = PositionManager(self.account)
        self.account.save_state()

    def handle_decision(
        self,
        decision_action: str,  # BUY, SELL, or WAIT
        current_price: float,
        confidence: float = 0.0,
        reason: str = "",
        evidence: Optional[Dict[str, Any]] = None,
        symbol: str = "XAUUSD",
        volume: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        timeframe: str = "H1",
        mode: str = "PAPER"
    ) -> Optional[VirtualPosition]:
        """
        Consumes a decision intelligence event.
        If direction is BUY or SELL, triggers the opening of a new virtual position.
        """
        if decision_action.upper() not in ["BUY", "SELL"]:
            logger.info(f"Ignored shadow/paper decision: {decision_action} state received (WAIT).")
            return None

        # Check existing active position to prevent overexposure
        active = [
            p for p in self.account.get_open_positions()
            if p.symbol.upper() == symbol.upper()
            and p.timeframe.upper() == timeframe.upper()
            and p.direction.upper() == decision_action.upper()
        ]
        if active:
            logger.warning(f"Simulated position of direction {decision_action} already open on {symbol} on {timeframe}. Skipping duplication.")
            return None

        # Open Virtual Position
        pos = self.position_manager.open_virtual_position(
            symbol=symbol,
            direction=decision_action,
            entry_price=current_price,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            confidence=confidence,
            evidence=evidence,
            timeframe=timeframe
        )
        if pos:
            # Propagate custom fields
            pos.account_id = self.account.account_id
            pos.mode = mode.upper()
            pos.filled_at = pos.open_time.isoformat()
            self.account.save_state()

        return pos

    def update_market_price(self, symbol: str, current_price: float, timeframe: str = "H1") -> List[VirtualPosition]:
        """
        Processes a live streamed market tick update.
        Triggers price updates, evaluates TP/SL breaches, and performs automated evaluations.
        """
        closed_positions = self.position_manager.update_prices_and_evaluate(symbol, current_price)

        # Trigger judge evaluations & memory logging on newly closed positions
        for pos in closed_positions:
            try:
                self.trade_evaluator.evaluate_and_memorize(pos, timeframe=timeframe)
            except Exception as e:
                logger.error(f"Failed to evaluate closed virtual position: {str(e)}")

        if closed_positions:
            self.account.recalculate()
            self.account.save_state()

        return closed_positions

    def get_metrics(self) -> Dict[str, Any]:
        """Compiles overall performance and account telemetry metrics."""
        self.account.recalculate()
        closed = self.account.get_closed_positions()
        wins = sum(1 for p in closed if p.result and (p.result == "WIN" or getattr(p.result, "value", None) == "WIN"))
        losses = sum(1 for p in closed if p.result and (p.result == "LOSS" or getattr(p.result, "value", None) == "LOSS"))
        total = len(closed)

        win_rate = (wins / total * 100.0) if total > 0 else 0.0
        avg_confidence = sum(p.confidence for p in closed) / total if total > 0 else 0.0

        return {
            "account_id": self.account.account_id,
            "balance": round(self.account.cash_balance, 2),
            "equity": round(self.account.equity, 2),
            "available_cash": round(self.account.available_cash, 2),
            "used_margin": round(self.account.used_margin, 2),
            "unrealized_pnl": round(self.account.unrealized_pnl, 2),
            "realized_pnl": round(self.account.realized_pnl, 2),
            "fees": round(self.account.fees, 2),
            "slippage": round(self.account.slippage, 2),
            "open_positions_count": len(self.account.get_open_positions()),
            "closed_positions_count": total,
            "performance": {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate_pct": round(win_rate, 2),
                "average_confidence_pct": round(avg_confidence, 2)
            }
        }

    def tick_update(self) -> None:
        """
        Processes a safe periodic heartbeat and updates live shadow prices if active.
        """
        logger.debug("ShadowTradingEngine tick update heartbeat.")
        open_positions = self.account.get_open_positions()
        if not open_positions:
            return

        for pos in open_positions:
            pass
