from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketObservation

class DataRealityLayer:
    """
    Receives raw market data streams or historical data blocks from MT5,
    validates integrity (ascending timestamps, missing candles detection),
    normalizes raw states without subjective interpretation, and maintains raw market state.
    """
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._raw_states: Dict[str, List[MarketObservation]] = {
            "Tick": [], "M1": [], "M5": [], "M15": [], "H1": [], "H4": [], "Daily": [], "D1": []
        }
        self._timeframe_durations = {
            "Tick": timedelta(seconds=1),
            "M1": timedelta(minutes=1),
            "M5": timedelta(minutes=5),
            "M15": timedelta(minutes=15),
            "H1": timedelta(hours=1),
            "H4": timedelta(hours=4),
            "Daily": timedelta(days=1),
            "D1": timedelta(days=1)
        }

    def ingest_raw_candles(self, timeframe: str, candles: List[Dict[str, Any]]) -> List[MarketObservation]:
        """
        Ingests a list of raw dictionaries representing candles, validates them,
        normalizes to MarketObservation, and stores/returns them.
        """
        if timeframe not in self._raw_states:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        normalized: List[MarketObservation] = []
        for c in candles:
            timestamp = c["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            obs = MarketObservation(
                symbol=self.symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                high=float(c["high"]),
                low=float(c["low"]),
                open_price=float(c["open"]),
                close_price=float(c["close"]),
                volume=float(c.get("volume", 0.0)),
                meta=c.get("meta", {})
            )
            normalized.append(obs)

        # Validate ascending timestamps
        validated = self._validate_and_deduplicate(timeframe, normalized)

        # Merge into existing states
        self._merge_observations(timeframe, validated)
        return validated

    def _validate_and_deduplicate(self, timeframe: str, observations: List[MarketObservation]) -> List[MarketObservation]:
        """Ensures observations are sorted by timestamp and removes duplicates."""
        if not observations:
            return []

        sorted_obs = sorted(observations, key=lambda x: x.timestamp)
        unique_obs: List[MarketObservation] = []

        for obs in sorted_obs:
            if not unique_obs or unique_obs[-1].timestamp != obs.timestamp:
                unique_obs.append(obs)
            elif unique_obs[-1].timestamp == obs.timestamp:
                # Keep latest update (higher volume or overwrite)
                unique_obs[-1] = obs

        return unique_obs

    def _merge_observations(self, timeframe: str, new_obs: List[MarketObservation]) -> None:
        """Merges new observations with stored states maintaining chronological order and uniqueness."""
        current = self._raw_states[timeframe]
        combined = current + new_obs
        self._raw_states[timeframe] = self._validate_and_deduplicate(timeframe, combined)

    def detect_missing_candles(self, timeframe: str) -> List[datetime]:
        """
        Scans stored chronological observations for this timeframe to detect missing gaps.
        Returns a list of expected timestamps that are missing.
        """
        observations = self._raw_states[timeframe]
        if len(observations) < 2:
            return []

        missing: List[datetime] = []
        expected_delta = self._timeframe_durations.get(timeframe)
        if not expected_delta or timeframe == "Tick":
            return []

        for i in range(1, len(observations)):
            prev_t = observations[i-1].timestamp
            curr_t = observations[i].timestamp
            diff = curr_t - prev_t

            # Allow minor slack but detect gaps larger than 1.5x of timeframe duration
            if diff > expected_delta * 1.5:
                # Estimate missing slots
                temp_t = prev_t + expected_delta
                while temp_t < curr_t:
                    # Skip typical weekend gaps if daily/H4 to avoid false positives
                    is_weekend = temp_t.weekday() >= 5
                    if not (is_weekend and timeframe in ["H4", "Daily"]):
                        missing.append(temp_t)
                    temp_t += expected_delta

        return missing

    def get_raw_state(self, timeframe: str) -> List[MarketObservation]:
        """Retrieves raw stored market observations for a specific timeframe."""
        return self._raw_states.get(timeframe, [])
