from typing import List, Dict, Any, Optional

class MultiTimeframeAlignmentEngine:
    """
    Synthesizes and aligns market structure, trends, and regimes across multiple timeframes
    from higher timeframes (e.g., D1/H4) down to execution frames (H1/M15/M1).
    Ensures that low-timeframe execution plans are structurally aligned with high-timeframe flows.
    """
    def __init__(self) -> None:
        pass

    def align_structures(self, symbol: str, timeframe_narratives: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aligns structures across multiple timeframes.
        timeframe_narratives is a dictionary mapping timeframe keys (e.g., 'H4', 'H1', 'M15' or custom integer structures)
        to their analyzed narratives from MarketNarrativeEngine.
        """
        if not timeframe_narratives:
            return self._unaligned_result(symbol)

        sorted_frames = sorted(
            timeframe_narratives.keys(),
            key=self._frame_sort_weight,
            reverse=True
        )

        trends = []
        states = []
        for tf in sorted_frames:
            narr = timeframe_narratives[tf]
            trends.append(narr.get("trend", "NEUTRAL"))
            states.append(narr.get("state", "UNKNOWN"))

        # Determine overall trend and state alignment
        all_bullish = all(t == "BULLISH" for t in trends)
        all_bearish = all(t == "BEARISH" for t in trends)

        alignment_status = "PARTIALLY_ALIGNED"
        confidence = 65

        if all_bullish:
            alignment_status = "FULLY_ALIGNED_BULLISH"
            confidence = 88
        elif all_bearish:
            alignment_status = "FULLY_ALIGNED_BEARISH"
            confidence = 88
        elif len(trends) >= 2 and trends[0] == trends[1]:
            alignment_status = "HIGH_TIMEFRAME_ALIGNED"
            confidence = 75
        elif len(trends) >= 2 and trends[-1] == "NEUTRAL":
            alignment_status = "UNALIGNED"
            confidence = 50

        # Build detailed alignment scorecards
        checks = {
            "trend_alignment": alignment_status,
            "regime_congruence": "HIGH" if len(set(states)) <= 2 else "MIXED",
            "congruent_timeframes": sorted_frames,
            "trends_map": {tf: timeframe_narratives[tf].get("trend", "NEUTRAL") for tf in sorted_frames},
            "states_map": {tf: timeframe_narratives[tf].get("state", "RANGE") for tf in sorted_frames}
        }

        return {
            "symbol": symbol.upper(),
            "alignment": alignment_status,
            "confidence": confidence,
            "checks": checks,
            "summary": f"Multi-timeframe structural alignment status: {alignment_status} with {confidence}% confidence."
        }

    def _frame_sort_weight(self, tf_str: str) -> float:
        """Helper to sort timeframes from high to low."""
        weights = {
            "MN1": 43200.0, "MN": 43200.0,
            "W1": 10080.0, "W": 10080.0,
            "D1": 1440.0, "D": 1440.0, "DAILY": 1440.0,
            "H4": 240.0,
            "H1": 60.0, "H": 60.0,
            "M30": 30.0,
            "M15": 15.0,
            "M5": 5.0,
            "M1": 1.0
        }
        # Support integer tick-bars too
        try:
            return float(tf_str)
        except ValueError:
            return weights.get(tf_str.upper(), 60.0)

    def _unaligned_result(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "alignment": "UNALIGNED",
            "confidence": 30,
            "checks": {
                "trend_alignment": "UNKNOWN",
                "regime_congruence": "UNKNOWN",
                "congruent_timeframes": [],
                "trends_map": {},
                "states_map": {}
            },
            "summary": "No timeframe narratives provided for structural alignment."
        }
