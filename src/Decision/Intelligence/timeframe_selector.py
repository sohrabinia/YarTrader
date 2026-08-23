import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Brain.trading_knowledge import TradingKnowledgeBase, MarketStructureState

logger = logging.getLogger("AutomaticTimeframeSelector")


@dataclass
class UnifiedSignalContract:
    signal_id: str
    symbol: str
    timeframe: str
    direction: str  # "BUY" | "SELL" | "WAIT"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    pattern_id: str
    market_context: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimeframeSelectionResult:
    selected_timeframe: str
    reason: str
    confidence: float
    alignment_scores: Dict[str, float]


class AutomaticTimeframeSelector:
    """
    Ranks M5, M15, H1, H4 timeframes based on structural clarity,
    liquidity sweep presence, and higher-timeframe alignment scores.
    """

    def __init__(self) -> None:
        self.knowledge_base = TradingKnowledgeBase()

    def select_best_timeframe(
        self,
        symbol: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]]
    ) -> TimeframeSelectionResult:
        supported_tfs = ["M5", "M15", "H1", "H4"]
        tf_states: Dict[str, MarketStructureState] = {}
        alignment_scores: Dict[str, float] = {}

        for tf in supported_tfs:
            candles = candles_by_tf.get(tf) or candles_by_tf.get(tf.lower()) or []
            if candles:
                state = self.knowledge_base.analyze_market_structure(candles)
                tf_states[tf] = state
                # Score components: Trend clarity + Sweep presence + Momentum
                score = 0.50
                if state.trend in ["BULLISH", "BEARISH"]:
                    score += 0.25
                if state.liquidity_sweep:
                    score += 0.15
                if state.structure_type in ["TRENDING_UP", "TRENDING_DOWN"]:
                    score += 0.10
                alignment_scores[tf] = round(score, 2)
            else:
                alignment_scores[tf] = 0.0

        # Primary setup preference: M15 -> M5 -> H1 -> H4
        best_tf = "M15"
        best_score = alignment_scores.get("M15", 0.0)

        for tf in ["M5", "H1", "H4"]:
            if alignment_scores.get(tf, 0.0) > best_score:
                best_tf = tf
                best_score = alignment_scores[tf]

        if best_score < 0.60:
            return TimeframeSelectionResult(
                selected_timeframe="M15",
                reason="Low multi-timeframe structural alignment score across all timeframes.",
                confidence=best_score,
                alignment_scores=alignment_scores
            )

        return TimeframeSelectionResult(
            selected_timeframe=best_tf,
            reason=f"Highest structural alignment score ({best_score}) on {best_tf}.",
            confidence=best_score,
            alignment_scores=alignment_scores
        )
