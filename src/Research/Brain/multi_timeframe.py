from datetime import datetime
from typing import Dict, List, Any
from src.Research.Brain.models import MarketObservation, MarketEvent

class MultiTimeframePerception:
    """
    Coordinates multi-timeframe market perception across Tick, M1, M5, M15, H1, H4, Daily.
    Maps temporal containment structures to capture how higher timeframe structures
    are composed of smaller timeframe sequences (fractal containment mapping).
    """
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._timeframe_hierarchy = ["Tick", "M1", "M5", "M15", "H1", "H4", "Daily"]

    def map_fractal_relationships(
        self,
        timeframe_observations: Dict[str, List[MarketObservation]]
    ) -> Dict[str, Any]:
        """
        Maps structural overlaps between consecutive levels in the timeframe hierarchy.
        For example, find which H1 observations are contained within a given H4 observation period.
        """
        relationships: Dict[str, Any] = {}

        # Loop through consecutive timeframes in hierarchy
        for i in range(len(self._timeframe_hierarchy) - 1):
            lower_tf = self._timeframe_hierarchy[i]
            higher_tf = self._timeframe_hierarchy[i+1]

            lower_data = timeframe_observations.get(lower_tf, [])
            higher_data = timeframe_observations.get(higher_tf, [])

            overlap_map: Dict[str, List[Dict[str, Any]]] = {}

            for h_obs in higher_data:
                # Approximate duration of the higher timeframe candle to construct a window
                start_time = h_obs.timestamp
                # Calculate approximate end_time based on next observation or timeframe name
                end_time = start_time + self._get_timeframe_delta(higher_tf)

                contained: List[MarketObservation] = []
                for l_obs in lower_data:
                    if start_time <= l_obs.timestamp <= end_time:
                        contained.append(l_obs)

                if contained:
                    key = h_obs.timestamp.isoformat()
                    overlap_map[key] = [
                        {
                            "timestamp": o.timestamp.isoformat(),
                            "close": o.close_price,
                            "volume": o.volume
                        }
                        for o in contained
                    ]

            if overlap_map:
                relationships[f"{higher_tf}_contains_{lower_tf}"] = {
                    "higher_timeframe": higher_tf,
                    "lower_timeframe": lower_tf,
                    "mappings_count": len(overlap_map),
                    "mappings": overlap_map
                }

        return relationships

    def _get_timeframe_delta(self, timeframe: str) -> Any:
        from datetime import timedelta
        deltas = {
            "Tick": timedelta(seconds=1),
            "M1": timedelta(minutes=1),
            "M5": timedelta(minutes=5),
            "M15": timedelta(minutes=15),
            "H1": timedelta(hours=1),
            "H4": timedelta(hours=4),
            "Daily": timedelta(days=1)
        }
        return deltas.get(timeframe, timedelta(minutes=1))
