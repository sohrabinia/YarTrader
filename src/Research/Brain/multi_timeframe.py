from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from src.Research.Brain.models import MarketObservation, MarketEvent

class MultiTimeframePerception:
    """
    Coordinates multi-timeframe market perception across official trading timeframes (M1, M5, M15, H1, H4, D1, W1).
    Maps temporal containment structures to capture how higher timeframe structures
    are composed of smaller timeframe sequences (fractal containment mapping).
    """
    OFFICIAL_TRADING_TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1", "W1"]

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._timeframe_hierarchy = ["M1", "M5", "M15", "H1", "H4", "D1", "W1"]

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
        deltas = {
            "Tick": timedelta(seconds=1),
            "M1": timedelta(minutes=1),
            "M5": timedelta(minutes=5),
            "M15": timedelta(minutes=15),
            "H1": timedelta(hours=1),
            "H4": timedelta(hours=4),
            "D1": timedelta(days=1),
            "Daily": timedelta(days=1),
            "W1": timedelta(weeks=1),
            "MN1": timedelta(days=30)
        }
        return deltas.get(timeframe, timedelta(minutes=1))

    def generate_hierarchical_context(
        self,
        symbol: str,
        observations_by_tf: Dict[str, List[MarketObservation]],
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Constructs a unified HierarchicalMarketContext model across the 9 resolutions.
        """
        ts = timestamp or datetime.now(timezone.utc)

        # Calculate macro bias
        macro_bias = {}
        for tf in ["MN1", "W1", "D1"]:
            obs_list = observations_by_tf.get(tf, [])
            if len(obs_list) >= 2:
                # Determine direction purely mathematically
                diff = obs_list[-1].close_price - obs_list[0].close_price
                macro_bias[tf] = "Bullish" if diff > 0 else "Bearish"
            else:
                macro_bias[tf] = "Bullish" # fallback default

        # Calculate regime and structure
        regime_and_structure = {}
        for tf in ["H4", "H1"]:
            obs_list = observations_by_tf.get(tf, [])
            if len(obs_list) >= 3:
                # Basic trend check to determine regime
                diff = obs_list[-1].close_price - obs_list[-3].close_price
                if abs(diff) < 2.0:
                    regime_and_structure[tf] = "Accumulation"
                else:
                    regime_and_structure[tf] = "Recovery" if diff > 0 else "Distribution"
            else:
                regime_and_structure[tf] = "Accumulation"

        # Primary decision M15
        m15_obs = observations_by_tf.get("M15", [])
        m15_setup = "Neutral"
        quality_score = 0.5
        if len(m15_obs) >= 2:
            m15_diff = m15_obs[-1].close_price - m15_obs[-2].close_price
            if m15_diff > 0:
                m15_setup = "Long Reversal"
                quality_score = 0.8
            else:
                m15_setup = "Short Reversal"
                quality_score = 0.75

        primary_decision = {
            "timeframe": "M15",
            "setup": m15_setup,
            "quality_score": quality_score
        }

        # Primary execution M5
        m5_obs = observations_by_tf.get("M5", [])
        m5_trigger = "No Trigger"
        entry_price = 0.0
        if len(m5_obs) >= 1:
            entry_price = m5_obs[-1].close_price
            m5_trigger = "Breakout Confirmation" if m15_setup == "Long Reversal" else "Pullback Rejection"

        primary_execution = {
            "timeframe": "M5",
            "trigger": m5_trigger,
            "entry_price": entry_price
        }

        # Micro confirmations
        m1_obs = observations_by_tf.get("M1", [])
        m1_state = "Structure Hold" if len(m1_obs) > 0 and m1_obs[-1].close_price >= m1_obs[0].close_price else "Weak structure"

        micro_confirmation = {
            "M1": m1_state,
            "M5": "Structure Confirmation"
        }

        return {
            "symbol": symbol.upper(),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "macro_bias": macro_bias,
            "regime_and_structure": regime_and_structure,
            "primary_decision": primary_decision,
            "primary_execution": primary_execution,
            "micro_confirmation": micro_confirmation
        }
