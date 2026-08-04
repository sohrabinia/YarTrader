import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

class SymbolTimeContext:
    """
    Represents an isolated cognitive intelligence and shadow trading context
    for a specific Symbol + Internal Timeframe (e.g. XAUUSD_64 or XAUUSD_M5).
    Guarantees complete memory isolation (no cross-contamination across contexts).
    """
    def __init__(self, symbol: str, timeframe: Any) -> None:
        self.symbol = symbol.upper()
        try:
            self.timeframe = int(timeframe)
        except (ValueError, TypeError):
            self.timeframe = timeframe
        self.context_id = f"{self.symbol}_{self.timeframe}"

        # State Buffers
        self.tick_buffer: List[Dict[str, Any]] = []
        self.trades: List[Any] = []  # List of ShadowTrade objects for this context
        self.bases: List[Dict[str, Any]] = []
        self.nodes: List[Dict[str, Any]] = []
        self.patterns: List[Dict[str, Any]] = []
        self.learning: List[Dict[str, Any]] = []

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates performance statistics strictly isolated for this context."""
        completed = [t for t in self.trades if t.status in ["TARGET_HIT", "STOP_HIT", "TIMEOUT", "INVALIDATED"]]
        wins = sum(1 for t in completed if t.status == "TARGET_HIT")
        losses = sum(1 for t in completed if t.status == "STOP_HIT")
        total = len(completed)
        win_rate = (wins / total * 100.0) if total > 0 else 0.0
        avg_confidence = (sum(t.confidence for t in completed) / total) if total > 0 else 0.0

        return {
            "context_id": self.context_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_trades": len(self.trades),
            "completed_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "average_confidence_pct": round(avg_confidence, 2),
            "active_orders_count": len([t for t in self.trades if t.status == "CREATED"]),
            "running_positions_count": len([t for t in self.trades if t.status == "RUNNING"])
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "ticks_count": len(self.tick_buffer),
            "trades_count": len(self.trades),
            "bases_count": len(self.bases),
            "nodes_count": len(self.nodes),
            "patterns_count": len(self.patterns),
            "learning_count": len(self.learning)
        }
