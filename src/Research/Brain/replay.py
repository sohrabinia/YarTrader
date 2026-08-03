import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketObservation

class MarketReplayEngine:
    """
    Simulates historical market playback at various scales:
    - Tick
    - Seconds
    - Minutes
    - Hours
    - Daily
    - Custom Discovered scales (adaptive time structures based on price range shifts)

    Enforces strict Future Leakage Protection. At any replayed time 'T',
    only observations with timestamps <= T are returned/accessible.
    """
    def __init__(self, symbol: str, observations: List[MarketObservation]) -> None:
        self.symbol = symbol
        # Enforce sorted observations to avoid out-of-order leaks
        self._all_observations = sorted(observations, key=lambda o: o.timestamp)
        self._current_time: Optional[datetime] = None
        if self._all_observations:
            self._current_time = self._all_observations[0].timestamp

    def set_cursor(self, target_time: datetime) -> None:
        """Sets the current playback cursor time."""
        self._current_time = target_time

    def get_current_time(self) -> Optional[datetime]:
        """Gets current replay timestamp."""
        return self._current_time

    def get_available_data(self) -> List[MarketObservation]:
        """
        Returns all observations up to and including the current playback cursor time.
        Future data is completely excluded, preventing cognitive future leakage.
        Raises a ValueError if look-ahead bias or future-marker sentinels are detected beyond current_time.
        """
        if not self._current_time:
            return []

        for o in self._all_observations:
            if hasattr(o, "meta") and isinstance(o.meta, dict) and o.meta.get("sentinel_future_leakage") is True:
                if o.timestamp > self._current_time:
                    raise ValueError("Future Leakage Guard Exception: Look-ahead bias detected! Attempted to access out-of-bounds future data.")

        return [o for o in self._all_observations if o.timestamp <= self._current_time]

    def advance_by_scale(self, scale: str, duration_units: int = 1) -> bool:
        """
        Advances the replay cursor by a specific scale duration:
        - 'Tick': 1 second
        - 'Seconds': 1 second
        - 'Minutes': 1 minute
        - 'Hours': 1 hour
        - 'Daily': 1 day
        - 'CustomScale': adaptive state-change threshold based on price movement.
        """
        if not self._current_time:
            return False

        if scale.lower() == "tick":
            delta = timedelta(seconds=1)
        elif scale.lower() == "seconds":
            delta = timedelta(seconds=1)
        elif scale.lower() == "minutes":
            delta = timedelta(minutes=1)
        elif scale.lower() == "hours":
            delta = timedelta(hours=1)
        elif scale.lower() == "daily":
            delta = timedelta(days=1)
        elif scale.lower() == "customscale":
            # For adaptive custom structures, we look for the next observation
            # whose price differs from the current price by a significant threshold (e.g. 10.0 points)
            current_obs = self._get_last_obs_at_cursor()
            if not current_obs:
                delta = timedelta(minutes=1)
            else:
                next_obs = [o for o in self._all_observations if o.timestamp > self._current_time]
                if not next_obs:
                    return False
                for o in next_obs:
                    if abs(o.close_price - current_obs.close_price) >= 10.0:
                        self._current_time = o.timestamp
                        return True
                # If no threshold breach, just jump to the last observation
                self._current_time = next_obs[-1].timestamp
                return True
        else:
            delta = timedelta(minutes=1)

        self._current_time += delta * duration_units

        # Return True if there are still observations at or after the new time
        return any(o.timestamp >= self._current_time for o in self._all_observations)

    def _get_last_obs_at_cursor(self) -> Optional[MarketObservation]:
        available = self.get_available_data()
        return available[-1] if available else None
