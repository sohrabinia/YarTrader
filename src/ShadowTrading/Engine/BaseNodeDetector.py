import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

class BaseStructure:
    """
    Represents a detected market compression area (Base).
    """
    def __init__(
        self,
        symbol: str,
        high: float,
        low: float,
        duration: float,
        tick_count: int,
        tests: int = 1,
        expansion_direction: str = "NONE",
        historical_result: str = "PENDING",
        success_rate: float = 0.5,
        base_id: Optional[str] = None,
        creation_time: Optional[datetime] = None
    ) -> None:
        self.base_id = base_id or f"Base-{uuid.uuid4().hex[:8]}"
        self.symbol = symbol
        self.creation_time = creation_time or datetime.now()
        self.high = float(high)
        self.low = float(low)
        self.duration = float(duration)
        self.tick_count = int(tick_count)
        self.tests = int(tests)
        self.expansion_direction = expansion_direction  # UP, DOWN, NONE
        self.historical_result = historical_result      # WIN, LOSS, PENDING
        self.success_rate = float(success_rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_id": self.base_id,
            "symbol": self.symbol,
            "creation_time": self.creation_time.isoformat() if isinstance(self.creation_time, datetime) else str(self.creation_time),
            "high": round(self.high, 5),
            "low": round(self.low, 5),
            "duration": self.duration,
            "tick_count": self.tick_count,
            "tests": self.tests,
            "expansion_direction": self.expansion_direction,
            "historical_result": self.historical_result,
            "success_rate": round(self.success_rate, 2)
        }


class NodeStructure:
    """
    Represents a detected price reaction point (Node).
    """
    def __init__(
        self,
        price_level: float,
        creation_context: str,
        movement_phase: str,
        reaction_strength: float,
        outcome: str = "PENDING",
        node_id: Optional[str] = None
    ) -> None:
        self.node_id = node_id or f"Node-{uuid.uuid4().hex[:8]}"
        self.price_level = float(price_level)
        self.creation_context = creation_context  # e.g., "Velocity spike reaction"
        self.movement_phase = movement_phase      # e.g., "Reversal", "Continuation"
        self.reaction_strength = float(reaction_strength)
        self.outcome = outcome                    # SUCCESS, FAILURE, PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "price_level": round(self.price_level, 5),
            "creation_context": self.creation_context,
            "movement_phase": self.movement_phase,
            "reaction_strength": round(self.reaction_strength, 2),
            "outcome": self.outcome
        }


class BaseNodeDetector:
    """
    Analyses tick sequences to detect Bases and Nodes.
    """
    def __init__(self, compression_threshold: float = 0.5) -> None:
        self.compression_threshold = compression_threshold

    def detect_base(self, symbol: str, ticks: List[Dict[str, Any]]) -> Optional[BaseStructure]:
        """
        Detects compression areas (Bases) from raw tick sequences.
        """
        if len(ticks) < 10:
            return None

        prices = [float(t["price"]) for t in ticks]
        high = max(prices)
        low = min(prices)
        price_range = high - low

        if price_range <= self.compression_threshold:
            # Calculate duration
            times = [t.get("timestamp", datetime.now()) for t in ticks]
            sorted_times = sorted([datetime.fromisoformat(t) if isinstance(t, str) else t for t in times])
            duration = (sorted_times[-1] - sorted_times[0]).total_seconds()

            # Count touches to boundaries
            tests = 0
            for p in prices:
                if abs(p - high) < 0.05 or abs(p - low) < 0.05:
                    tests += 1

            return BaseStructure(
                symbol=symbol,
                high=high,
                low=low,
                duration=duration,
                tick_count=len(ticks),
                tests=tests,
                creation_time=sorted_times[0]
            )
        return None

    def detect_node(self, ticks: List[Dict[str, Any]]) -> Optional[NodeStructure]:
        """
        Detects sudden reaction points (Nodes) from tick velocity peaks.
        """
        if len(ticks) < 3:
            return None

        prices = [float(t["price"]) for t in ticks]
        # Look for quick rebound
        change_1 = prices[-1] - prices[-2]
        change_2 = prices[-2] - prices[-3]

        # If there is a sharp reversal, we mark prices[-2] as a node
        if change_1 * change_2 < 0 and abs(change_1) > 0.1 and abs(change_2) > 0.1:
            strength = abs(change_1) + abs(change_2)
            phase = "Reversal" if abs(change_1) > abs(change_2) else "Continuation"
            return NodeStructure(
                price_level=prices[-2],
                creation_context="High velocity tick peak",
                movement_phase=phase,
                reaction_strength=strength
            )
        return None
