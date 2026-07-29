from typing import List, Dict, Any
from src.Research.Brain.models import MarketObservation, MarketEvent, MarketSequence

class ObservationBrain:
    """
    Analyzes raw chronological MarketObservation data to detect raw mathematical price action
    sequences and events without subjective vocabulary (e.g., trend, breakout).
    """
    def __init__(self, symbol: str, timeframe: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.sequence = MarketSequence(symbol=symbol, timeframe=timeframe)

    def process_observations(self, observations: List[MarketObservation]) -> MarketSequence:
        """Processes observations, appends new ones to the sequence, and detects raw price action events."""
        # Ensure unique observations in the internal sequence
        existing_ts = {obs.timestamp for obs in self.sequence.observations}
        for obs in observations:
            if obs.timestamp not in existing_ts:
                self.sequence.observations.append(obs)
                existing_ts.add(obs.timestamp)

        # Sort chronologically
        self.sequence.observations.sort(key=lambda x: x.timestamp)

        # Detect raw events
        self.sequence.events = self._detect_raw_events()
        return self.sequence

    def _detect_raw_events(self) -> List[MarketEvent]:
        """
        Detects objective, name-free mathematical sequence events:
        - Consecutive price movements (bullish/bearish sequences)
        - Price change in points
        - Movement duration in candles
        - Subsequent reaction type (retracement or extension) and magnitude
        """
        obs_list = self.sequence.observations
        if len(obs_list) < 5:
            return []

        events: List[MarketEvent] = []
        i = 0
        n = len(obs_list)

        while i < n - 2:
            # Let's group consecutive candles of the same polarity
            start_idx = i
            first_candle = obs_list[start_idx]
            is_bullish = first_candle.close_price >= first_candle.open_price

            # Find sequence length
            j = start_idx + 1
            while j < n:
                curr_candle = obs_list[j]
                curr_bullish = curr_candle.close_price >= curr_candle.open_price
                if curr_bullish != is_bullish:
                    break
                j += 1

            seq_len = j - start_idx
            end_idx = j - 1

            # Calculate price change from open of start to close of end
            price_change = obs_list[end_idx].close_price - obs_list[start_idx].open_price

            # Look at subsequent reaction (next 2-3 candles)
            reaction_candles = 0
            reaction_magnitude = 0.0
            reaction_type = "stability"

            if j < n:
                react_start_idx = j
                react_end_idx = min(j + 3, n - 1)
                reaction_candles = react_end_idx - react_start_idx + 1
                reaction_close = obs_list[react_end_idx].close_price
                react_open = obs_list[react_start_idx].open_price
                reaction_magnitude = reaction_close - react_open

                # Retracement check: reaction is opposite sign of original price change
                if price_change * reaction_magnitude < 0:
                    reaction_type = "retracement"
                elif price_change * reaction_magnitude > 0:
                    reaction_type = "extension"
                else:
                    reaction_type = "stability"

            # Record previous sequence length (events recorded so far)
            prev_len = len(events)

            event_obj = MarketEvent(
                symbol=self.symbol,
                timeframe=self.timeframe,
                start_time=obs_list[start_idx].timestamp,
                end_time=obs_list[end_idx].timestamp,
                price_change=price_change,
                duration_candles=seq_len,
                previous_sequence_len=prev_len,
                reaction_type=reaction_type,
                reaction_magnitude=reaction_magnitude,
                meta={
                    "direction": "upward" if price_change >= 0 else "downward",
                    "consecutive_bullish_candles": seq_len if is_bullish else 0,
                    "consecutive_bearish_candles": seq_len if not is_bullish else 0
                }
            )
            events.append(event_obj)

            # Move index forward
            i = j

        return events

    def generate_raw_description(self, event: MarketEvent) -> str:
        """Generates a raw objective description of the event without forbidden subjective terms."""
        direction = event.meta.get("direction", "neutral")
        desc = (
            f"Price moved {direction} {abs(event.price_change):.2f} points. "
            f"Movement duration: {event.duration_candles} candles. "
            f"After movement: {event.reaction_type} of {abs(event.reaction_magnitude):.2f} points occurred. "
            f"Previous sequence: {event.previous_sequence_len} events."
        )
        return desc
