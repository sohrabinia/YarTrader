import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class CustomTimeframeStructure:
    """
    Represents an internal AI market structure built purely from a sequence of raw ticks.
    Does NOT depend on broker or MT5 timeframes.
    """
    def __init__(
        self,
        frame_id: str,
        ticks: List[Dict[str, Any]]
    ) -> None:
        self.frame_id = frame_id
        self.tick_count = len(ticks)

        if not ticks:
            self.duration = 0.0
            self.price_range = 0.0
            self.movement_behavior = "EMPTY"
            self.high = 0.0
            self.low = 0.0
            self.open = 0.0
            self.close = 0.0
            self.timestamp = datetime.now()
            return

        # Sort ticks by time to be safe
        sorted_ticks = sorted(ticks, key=lambda t: t.get("timestamp", datetime.now()))
        self.timestamp = sorted_ticks[0].get("timestamp", datetime.now())

        # Calculate duration
        start_time = sorted_ticks[0].get("timestamp", datetime.now())
        end_time = sorted_ticks[-1].get("timestamp", datetime.now())
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        self.duration = (end_time - start_time).total_seconds()

        # Calculate high/low/open/close
        prices = [float(t["price"]) for t in sorted_ticks]
        self.high = max(prices)
        self.low = min(prices)
        self.open = prices[0]
        self.close = prices[-1]
        self.price_range = self.high - self.low

        # Movement behavior
        price_change = self.close - self.open
        if price_change > 0.0001:
            self.movement_behavior = "EXPANSION_UP"
        elif price_change < -0.0001:
            self.movement_behavior = "EXPANSION_DOWN"
        else:
            self.movement_behavior = "COMPRESSION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "tick_count": self.tick_count,
            "duration": self.duration,
            "price_range": round(self.price_range, 5),
            "high": round(self.high, 5),
            "low": round(self.low, 5),
            "open": round(self.open, 5),
            "close": round(self.close, 5),
            "movement_behavior": self.movement_behavior,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        }


class CustomTimeEngine:
    """
    Constructs custom AI-defined internal time structures from raw ticks.
    """
    def __init__(self, target_sizes: List[int] = None) -> None:
        # Default target sizes: 1, 4, 16, 64, 256, 1024
        self.target_sizes = target_sizes or [1, 4, 16, 64, 256, 1024]

    def build_structures(self, raw_ticks: List[Dict[str, Any]]) -> Dict[int, List[CustomTimeframeStructure]]:
        """
        Aggregates raw ticks into various custom block sizes (e.g., 64 tick structures).
        """
        structures = {}
        for size in self.target_sizes:
            structures[size] = []
            # Bundle into chunks of 'size'
            for i in range(0, len(raw_ticks), size):
                chunk = raw_ticks[i:i+size]
                if chunk:
                    frame_id = f"TF-{size}-{i // size}"
                    structures[size].append(CustomTimeframeStructure(frame_id, chunk))
        return structures
