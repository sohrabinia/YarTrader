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

        # Build detailed alignment scorecard
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

    def align_m15_m5_pipeline(
        self,
        symbol: str,
        timeframe_narratives: Dict[str, Dict[str, Any]],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Executes M15 Primary Decision Gate & M5 Execution Trigger pipeline.
        - setup_detected: checks if M15 has setup (e.g., trend is bullish/bearish).
        - trigger_confirmed: checks if M5 matches the M15 bias.
        - htf_filter: H1/H4/D1/W1/MN1 act as direction filters & confidence multipliers.
        """
        m15_narr = timeframe_narratives.get("M15", {})
        m5_narr = timeframe_narratives.get("M5", {})

        m15_trend = m15_narr.get("trend", "NEUTRAL").upper()
        if m15_trend not in ["BULLISH", "BEARISH"]:
            return {
                "decision_action": "WAIT",
                "reason": "No M15 structure setup detected. Decision gate requires active M15 structure.",
                "confidence": 0.0,
                "setup_present": False,
                "trigger_confirmed": False,
                "confidence_multipliers": {}
            }

        m15_setup = "Long Reversal" if m15_trend == "BULLISH" else "Short Reversal"

        m5_trend = m5_narr.get("trend", "NEUTRAL").upper()
        m5_confirmed = (m15_trend == m5_trend)

        if not m5_confirmed:
            return {
                "decision_action": "WAIT",
                "reason": f"M15 setup present ({m15_setup}), but M5 trigger confirmation ({m5_trend}) does not match.",
                "confidence": 30.0,
                "setup_present": True,
                "trigger_confirmed": False,
                "confidence_multipliers": {}
            }

        htf_keys = ["H1", "H4", "D1", "W1", "MN1"]
        congruence_count = 0
        total_htf = 0
        multipliers = {}

        for htf in htf_keys:
            if htf in timeframe_narratives:
                total_htf += 1
                htf_trend = timeframe_narratives[htf].get("trend", "NEUTRAL").upper()
                if htf_trend == m15_trend:
                    congruence_count += 1
                    multipliers[htf] = 1.15
                elif htf_trend == "NEUTRAL":
                    multipliers[htf] = 1.00
                else:
                    multipliers[htf] = 0.70  # Degrade trade confidence under counter-trend conditions

        base_confidence = 75.0
        final_confidence = base_confidence

        for htf, mult in multipliers.items():
            final_confidence *= mult

        final_confidence = min(100.0, max(10.0, final_confidence))

        decision_action = "BUY" if m15_trend == "BULLISH" else "SELL"

        pip_size = 0.10 if "XAU" in symbol.upper() else 0.0001
        multiplier = 150 if "XAU" in symbol.upper() else 200

        if decision_action == "BUY":
            stop_loss = current_price - (multiplier * pip_size)
            take_profit = current_price + (multiplier * 2 * pip_size)
        else:
            stop_loss = current_price + (multiplier * pip_size)
            take_profit = current_price - (multiplier * 2 * pip_size)

        reason = f"M15 Setup ({m15_setup}) with M5 Execution Trigger ({m5_trend}) confirmed."
        if congruence_count < total_htf:
            reason += f" Counter-trend macro timeframes degraded overall confidence to {round(final_confidence, 2)}%."

        return {
            "decision_action": decision_action,
            "reason": reason,
            "confidence": round(final_confidence, 2),
            "setup_present": True,
            "trigger_confirmed": True,
            "stop_loss": round(stop_loss, 4),
            "take_profit": round(take_profit, 4),
            "macro_alignment": {
                "congruence_pct": round((congruence_count / total_htf * 100.0) if total_htf > 0 else 100.0, 2),
                "multipliers": multipliers
            }
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
