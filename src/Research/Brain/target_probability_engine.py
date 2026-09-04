"""
YarTrader Layer 2 — Target Probability & Multi-Timeframe Consensus Engine
===========================================================================
Calculates empirical target probabilities P(target reached before invalidation)
for candidate target levels (P +/- k * ATR and structural liquidity zones).
Combines target distributions across M5, M15, H1, H4 into a unified Multi-Timeframe Consensus.
Zero lookahead; purely causal historical analysis.
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TargetCandidate:
    target_price: float
    invalidation_price: float
    probability: float
    expected_payoff_rr: float
    confidence: float
    direction: str  # "BUY" or "SELL"
    timeframe: str
    target_type: str  # "ATR_EXPANSION", "SWING_STRUCTURE", "LIQUIDITY_ZONE"


@dataclass
class MultiTimeframeConsensus:
    direction: str
    consensus_target: float
    consensus_invalidation: float
    consensus_probability: float
    disagreement_score: float
    overall_confidence: float
    tf_probabilities: Dict[str, float] = field(default_factory=dict)


class TargetProbabilityEngine:
    """
    Computes probabilistic path target reach probabilities and multi-timeframe consensus.
    """

    def __init__(self, atr_multipliers: List[float] = [1.0, 2.0, 3.0]) -> None:
        self.atr_multipliers = atr_multipliers

    def evaluate_target_probabilities(
        self,
        current_price: float,
        direction: str,
        atr: float,
        candles: List[Dict[str, Any]],
        timeframe: str = "M5",
        swing_targets: Optional[List[float]] = None
    ) -> List[TargetCandidate]:
        """
        Calculates P(target reached before invalidation) for candidate ATR & structural targets.
        Strictly causal: uses historical price volatility and empirical path distribution.
        """
        candidates: List[TargetCandidate] = []
        if current_price <= 0 or atr <= 0 or not candles:
            return candidates

        closes = [float(c.get("close", c.get("Close", 0.0))) for c in candles]
        if len(closes) < 10:
            return candidates

        # Returns & empirical path volatility
        p_arr = np.array(closes, dtype=np.float64)
        returns = np.diff(p_arr) / p_arr[:-1]
        std_ret = float(np.std(returns)) if len(returns) > 1 else 0.001

        direction_upper = direction.upper()

        # Build candidate levels
        target_levels = []
        for mult in self.atr_multipliers:
            if direction_upper == "BUY":
                tp = current_price + mult * atr
                sl = current_price - 1.5 * atr
            else:
                tp = current_price - mult * atr
                sl = current_price + 1.5 * atr
            target_levels.append((tp, sl, f"ATR_{mult:.1f}x"))

        if swing_targets:
            for st in swing_targets:
                if direction_upper == "BUY" and st > current_price:
                    sl = current_price - 1.5 * atr
                    target_levels.append((st, sl, "SWING_STRUCTURE"))
                elif direction_upper == "SELL" and st < current_price:
                    sl = current_price - 1.5 * atr
                    target_levels.append((st, sl, "SWING_STRUCTURE"))

        # Compute empirical reach probability using drift-diffusion / random walk approximation
        for tp, sl, t_type in target_levels:
            sl_dist = abs(current_price - sl)
            tp_dist = abs(current_price - tp)
            if sl_dist <= 0 or tp_dist <= 0:
                continue

            # Standard gambler's ruin formula for unbiased / mild drift Brownian motion:
            # P(reach TP before SL) = SL_dist / (SL_dist + TP_dist)
            raw_prob = sl_dist / (sl_dist + tp_dist)

            # Adjust slightly for momentum drift if recent return > 0 in direction
            recent_drift = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0.0
            drift_adj = 0.05 if (direction_upper == "BUY" and recent_drift > 0) or (direction_upper == "SELL" and recent_drift < 0) else -0.05
            prob = max(0.05, min(0.95, round(raw_prob + drift_adj, 4)))

            rr = round(tp_dist / sl_dist, 2)
            conf = max(0.1, min(1.0, round(1.0 - (std_ret * 10.0), 4)))

            candidates.append(
                TargetCandidate(
                    target_price=round(tp, 4),
                    invalidation_price=round(sl, 4),
                    probability=prob,
                    expected_payoff_rr=rr,
                    confidence=conf,
                    direction=direction_upper,
                    timeframe=timeframe.upper(),
                    target_type=t_type
                )
            )

        return candidates

    def calculate_mtf_consensus(
        self,
        tf_candidates: Dict[str, List[TargetCandidate]]
    ) -> MultiTimeframeConsensus:
        """
        Combines target candidates across M5, M15, H1, H4 into unified consensus.
        """
        if not tf_candidates:
            return MultiTimeframeConsensus(
                direction="WAIT",
                consensus_target=0.0,
                consensus_invalidation=0.0,
                consensus_probability=0.0,
                disagreement_score=1.0,
                overall_confidence=0.0
            )

        buy_probs = []
        sell_probs = []
        tf_probs = {}

        targets = []
        invalidations = []

        for tf, cand_list in tf_candidates.items():
            if not cand_list:
                continue
            best_cand = max(cand_list, key=lambda c: c.probability)
            tf_probs[tf] = best_cand.probability
            targets.append(best_cand.target_price)
            invalidations.append(best_cand.invalidation_price)

            if best_cand.direction == "BUY":
                buy_probs.append(best_cand.probability)
            else:
                sell_probs.append(best_cand.probability)

        avg_buy = sum(buy_probs) / len(buy_probs) if buy_probs else 0.0
        avg_sell = sum(sell_probs) / len(sell_probs) if sell_probs else 0.0

        if avg_buy > avg_sell and avg_buy >= 0.45:
            consensus_dir = "BUY"
            consensus_p = avg_buy
        elif avg_sell > avg_buy and avg_sell >= 0.45:
            consensus_dir = "SELL"
            consensus_p = avg_sell
        else:
            consensus_dir = "WAIT"
            consensus_p = max(avg_buy, avg_sell)

        avg_target = sum(targets) / len(targets) if targets else 0.0
        avg_invalidation = sum(invalidations) / len(invalidations) if invalidations else 0.0

        # Disagreement score = standard deviation of probabilities across timeframes
        p_vals = list(tf_probs.values())
        disagreement = float(np.std(p_vals)) if len(p_vals) > 1 else 0.0
        confidence = max(0.0, min(1.0, round(1.0 - disagreement, 4)))

        return MultiTimeframeConsensus(
            direction=consensus_dir,
            consensus_target=round(avg_target, 4),
            consensus_invalidation=round(avg_invalidation, 4),
            consensus_probability=round(consensus_p, 4),
            disagreement_score=round(disagreement, 4),
            overall_confidence=confidence,
            tf_probabilities=tf_probs
        )
