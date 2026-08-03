import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

class BaseStructure:
    """
    Represents a detected market compression area (Base).
    Supports orderly state transitions: Creation -> Formation -> Compression -> Break -> Reaction -> Outcome
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
        creation_time: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        price_range: Optional[float] = None,
        volume_behavior: str = "NEUTRAL",
        break_type: str = "NONE",
        result: str = "PENDING",
        state: str = "Creation"
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

        # Extended schema parameters
        self.start_time = start_time or self.creation_time
        self.end_time = end_time or self.start_time
        self.price_range = price_range if price_range is not None else (self.high - self.low)
        self.volume_behavior = volume_behavior
        self.break_type = break_type
        self.result = result
        self.state = state  # Creation -> Formation -> Compression -> Break -> Reaction -> Outcome

        # Multi-reaction outcome tracking separated from the raw Base Structure itself
        self.reactions: List[Dict[str, Any]] = []

    def transition_state(self, next_state: str) -> None:
        """Transitions the Base state strictly along the orderly lifecycle progression."""
        valid_states = ["Creation", "Formation", "Compression", "Break", "Reaction", "Outcome"]
        if next_state not in valid_states:
            raise ValueError(f"Invalid state: {next_state}")

        current_idx = valid_states.index(self.state)
        next_idx = valid_states.index(next_state)

        # Transition must proceed in orderly sequence (idx + 1)
        if next_idx != current_idx + 1:
            raise ValueError(f"State transition integrity violation: cannot jump from '{self.state}' directly to '{next_state}'")

        self.state = next_state

    @property
    def fingerprint(self) -> str:
        """Generates a unique structural fingerprint for the Base compression area."""
        import hashlib
        raw_str = f"{self.symbol}:{self.high:.4f}:{self.low:.4f}:{self.price_range:.4f}:{self.volume_behavior}:{self.break_type}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def add_reaction_outcome(self, reaction_id: str, reaction_type: str, outcome_result: str, feedback: str) -> None:
        """Saves a specific reaction outcome independent of the Base structure itself to support multi-reaction history."""
        self.reactions.append({
            "reaction_id": reaction_id,
            "reaction_type": reaction_type,
            "outcome_result": outcome_result,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        })

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
            "success_rate": round(self.success_rate, 2),
            "start_time": self.start_time.isoformat() if isinstance(self.start_time, datetime) else str(self.start_time),
            "end_time": self.end_time.isoformat() if isinstance(self.end_time, datetime) else str(self.end_time),
            "price_range": round(self.price_range, 5),
            "volume_behavior": self.volume_behavior,
            "break_type": self.break_type,
            "result": self.result,
            "state": self.state,
            "fingerprint": self.fingerprint,
            "reactions": self.reactions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseStructure":
        def parse_dt(v: Any) -> Optional[datetime]:
            if not v:
                return None
            try:
                return datetime.fromisoformat(v)
            except Exception:
                return None

        base = cls(
            symbol=data["symbol"],
            high=data["high"],
            low=data["low"],
            duration=data["duration"],
            tick_count=data["tick_count"],
            tests=data.get("tests", 1),
            expansion_direction=data.get("expansion_direction", "NONE"),
            historical_result=data.get("historical_result", "PENDING"),
            success_rate=data.get("success_rate", 0.5),
            base_id=data.get("base_id"),
            creation_time=parse_dt(data.get("creation_time")),
            start_time=parse_dt(data.get("start_time")),
            end_time=parse_dt(data.get("end_time")),
            price_range=data.get("price_range"),
            volume_behavior=data.get("volume_behavior", "NEUTRAL"),
            break_type=data.get("break_type", "NONE"),
            result=data.get("result", "PENDING"),
            state=data.get("state", "Creation")
        )
        base.reactions = data.get("reactions", [])
        return base


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


class NodePathTracker:
    """
    Traces Base to Node path tracking sequences (e.g. mapping reaction sequences after base breakout).
    """
    def __init__(self) -> None:
        self.active_paths: List[Dict[str, Any]] = []

    def start_path_tracking(self, base: BaseStructure) -> Dict[str, Any]:
        path = {
            "path_id": f"Path-{uuid.uuid4().hex[:8]}",
            "base_id": base.base_id,
            "symbol": base.symbol,
            "start_time": base.start_time,
            "nodes": [],
            "status": "TRACKING",
            "outcome": "PENDING"
        }
        self.active_paths.append(path)
        return path

    def add_node_to_path(self, path_id: str, node: NodeStructure, reaction_type: str = "Reaction") -> Optional[Dict[str, Any]]:
        for path in self.active_paths:
            if path["path_id"] == path_id:
                path["nodes"].append({
                    "node_id": node.node_id,
                    "price_level": node.price_level,
                    "reaction_type": reaction_type,
                    "timestamp": datetime.now()
                })
                return path
        return None

    def finalize_path(self, path_id: str, outcome: str) -> Optional[Dict[str, Any]]:
        for path in self.active_paths:
            if path["path_id"] == path_id:
                path["status"] = "COMPLETED"
                path["outcome"] = outcome
                return path
        return None


class BaseNodeDetector:
    """
    Analyses tick sequences to detect Bases and Nodes.
    """
    def __init__(self, compression_threshold: float = 0.5) -> None:
        self.compression_threshold = compression_threshold

    def calculate_tick_velocity(self, ticks: List[Dict[str, Any]]) -> float:
        """
        Calculates the average price change velocity of ticks.
        """
        if len(ticks) < 2:
            return 0.0
        prices = [float(t["price"]) for t in ticks]
        times = [t.get("timestamp", datetime.now()) for t in ticks]
        sorted_times = sorted([datetime.fromisoformat(t) if isinstance(t, str) else t for t in times])
        total_time = (sorted_times[-1] - sorted_times[0]).total_seconds()
        if total_time <= 0.0:
            return 0.0

        price_diff = abs(prices[-1] - prices[0])
        return price_diff / total_time

    def calculate_volume_pressure(self, ticks: List[Dict[str, Any]]) -> float:
        """
        Computes buying/selling volume ratio to analyze market micro-structure.
        """
        if not ticks:
            return 0.5
        buy_volume = 0.0
        sell_volume = 0.0
        for t in ticks:
            vol = float(t.get("volume", 1.0))
            direction = t.get("direction", "BUY")
            if direction == "BUY":
                buy_volume += vol
            else:
                sell_volume += vol
        total = buy_volume + sell_volume
        return buy_volume / total if total > 0.0 else 0.5

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

            # Micro-structure behavior analysis
            velocity = self.calculate_tick_velocity(ticks)
            volume_p = self.calculate_volume_pressure(ticks)
            vol_behavior = "ACCUMULATION" if volume_p > 0.6 else ("DISTRIBUTION" if volume_p < 0.4 else "NEUTRAL")

            return BaseStructure(
                symbol=symbol,
                high=high,
                low=low,
                duration=duration,
                tick_count=len(ticks),
                tests=tests,
                creation_time=sorted_times[0],
                start_time=sorted_times[0],
                end_time=sorted_times[-1],
                price_range=price_range,
                volume_behavior=vol_behavior,
                state="Compression"
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
