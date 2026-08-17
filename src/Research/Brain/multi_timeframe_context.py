from typing import Dict, List, Any, Optional
from datetime import datetime
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Brain.trading_knowledge import TradingKnowledgeBase, MarketStructureState

class MultiTimeframeContextEngine:
    """
    Multi-Timeframe Context Engine for YarTrader V1.2.
    Evaluates higher timeframe structure (D1/H4) for directional bias
    and lower timeframe structure (H1/M15/M5/M1) for entry triggers.
    """

    def __init__(self) -> None:
        self.knowledge_base = TradingKnowledgeBase()

    def evaluate_context(
        self,
        symbol: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]]
    ) -> Dict[str, Any]:
        """
        Evaluates multi-timeframe alignment across D1, H4, H1, M15, M5, M1.
        """
        tf_states: Dict[str, MarketStructureState] = {}
        for tf, candles in candles_by_tf.items():
            tf_states[tf.upper()] = self.knowledge_base.analyze_market_structure(candles)

        # Higher Timeframe Bias (D1 or H4)
        htf_state = tf_states.get("D1") or tf_states.get("H4") or MarketStructureState("RANGE", "RANGE_BOUND")
        htf_bias = htf_state.trend

        # Medium Timeframe Setup (H1 or M15)
        mtf_state = tf_states.get("H1") or tf_states.get("M15") or MarketStructureState("RANGE", "RANGE_BOUND")

        # Lower Timeframe Trigger (M5 or M1)
        ltf_state = tf_states.get("M5") or tf_states.get("M1") or MarketStructureState("RANGE", "RANGE_BOUND")

        # Alignment Check
        is_aligned = False
        decision_bias = "WAIT"
        alignment_reasoning = []

        if htf_bias == "BULLISH":
            alignment_reasoning.append("Higher Timeframe (D1/H4) structure is BULLISH.")
            if mtf_state.trend in ["BULLISH", "RANGE"]:
                alignment_reasoning.append("Medium Timeframe (H1/M15) pullback/structure supports long setup.")
                if ltf_state.trend == "BULLISH" or ltf_state.liquidity_sweep:
                    is_aligned = True
                    decision_bias = "BUY"
                    alignment_reasoning.append("Lower Timeframe (M5/M1) entry trigger confirmed (BUY).")
                else:
                    alignment_reasoning.append("Lower Timeframe entry trigger pending.")
            else:
                alignment_reasoning.append("Medium Timeframe counter-trend pullback in progress.")

        elif htf_bias == "BEARISH":
            alignment_reasoning.append("Higher Timeframe (D1/H4) structure is BEARISH.")
            if mtf_state.trend in ["BEARISH", "RANGE"]:
                alignment_reasoning.append("Medium Timeframe (H1/M15) pullback/structure supports short setup.")
                if ltf_state.trend == "BEARISH" or ltf_state.liquidity_sweep:
                    is_aligned = True
                    decision_bias = "SELL"
                    alignment_reasoning.append("Lower Timeframe (M5/M1) entry trigger confirmed (SELL).")
                else:
                    alignment_reasoning.append("Lower Timeframe entry trigger pending.")
            else:
                alignment_reasoning.append("Medium Timeframe counter-trend pullback in progress.")

        else:
            alignment_reasoning.append("Higher Timeframe is RANGE BOUND; waiting for clear structural breakout.")

        return {
            "symbol": symbol.upper(),
            "htf_bias": htf_bias,
            "decision_bias": decision_bias,
            "is_aligned": is_aligned,
            "reasoning": alignment_reasoning,
            "htf_state": htf_state,
            "mtf_state": mtf_state,
            "ltf_state": ltf_state
        }
