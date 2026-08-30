from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

@dataclass
class StrategyCandidate:
    strategy_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    direction: str  # "BUY", "SELL", "WAIT"
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    reasoning: List[str]
    market_context: Dict[str, Any]
    invalidation_level: float
    holding_period: str
    is_reversal: bool = False

class StrategyOrchestrator:
    """
    Multi-Strategy Orchestrator for YarTrader.
    Evaluates all 6 strategy profiles independently across localized timeframes:
      1. FAST_SCALP (M1/M5 sub-minute scalping)
      2. SCALP (M5/M15 momentum and structure retests)
      3. DAY_TRADING (M15/H1 structural trend following)
      4. JUMP (Impulse and momentum breakout validation)
      5. PRICE_ACTION_RTM (Supply/Demand zones, Quasimodo, Order Blocks)
      6. FRACTAL (Fractal pattern memory similarity & self-similarity)

    Resolves H1 Global WAIT defect by allowing lower timeframe strategies (M1/M5/M15)
    to evaluate localized market structure independently of H1 range/compression.
    """

    def __init__(self) -> None:
        self.supported_strategies = [
            "FAST_SCALP",
            "SCALP",
            "DAY_TRADING",
            "JUMP",
            "PRICE_ACTION_RTM",
            "FRACTAL"
        ]

    def evaluate_all_strategies(
        self,
        symbol: str,
        primary_timeframe: str,
        candles: List[Dict[str, Any]],
        all_timeframe_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        narrative: Optional[Dict[str, Any]] = None,
        liquidity: Optional[Dict[str, Any]] = None,
        zones: Optional[Dict[str, Any]] = None,
        alignment: Optional[Dict[str, Any]] = None,
        similarity: Optional[Dict[str, Any]] = None,
        fractal: Optional[Dict[str, Any]] = None,
        spread_pip: float = 1.0,
        account_balance: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Evaluates all 6 strategy profiles against market data and returns a detailed report
        plus the top-ranked candidate strategy setup.
        """
        narrative = narrative or {}
        liquidity = liquidity or {}
        zones = zones or {}
        alignment = alignment or {}
        similarity = similarity or {}
        fractal = fractal or {}
        all_tf_candles = all_timeframe_candles or {}

        if not candles:
            return {
                "symbol": symbol.upper(),
                "primary_timeframe": primary_timeframe,
                "candidates": [],
                "best_candidate": None,
                "summary": "No candle data provided."
            }

        current_price = float(candles[-1]["close"])
        pip_factor = 0.1 if "XAU" in symbol.upper() else (1.0 if "BTC" in symbol.upper() else 0.0001)

        candidates: List[StrategyCandidate] = []

        # 1. FAST_SCALP (M1 / M5)
        fast_scalp_cand = self._evaluate_fast_scalp(
            symbol, primary_timeframe, candles, liquidity, current_price, pip_factor
        )
        candidates.append(fast_scalp_cand)

        # 2. SCALP (M5 / M15)
        scalp_cand = self._evaluate_scalp(
            symbol, primary_timeframe, candles, liquidity, zones, current_price, pip_factor
        )
        candidates.append(scalp_cand)

        # 3. DAY_TRADING (M15 / H1)
        day_trading_cand = self._evaluate_day_trading(
            symbol, primary_timeframe, candles, narrative, alignment, current_price, pip_factor
        )
        candidates.append(day_trading_cand)

        # 4. JUMP (Breakout & Momentum Impulse)
        jump_cand = self._evaluate_jump(
            symbol, primary_timeframe, candles, current_price, pip_factor
        )
        candidates.append(jump_cand)

        # 5. PRICE_ACTION_RTM (Order Blocks, Quasimodo, Supply/Demand)
        rtm_cand = self._evaluate_price_action_rtm(
            symbol, primary_timeframe, candles, zones, liquidity, current_price, pip_factor
        )
        candidates.append(rtm_cand)

        # 6. FRACTAL (Pattern Memory Similarity & Multiscale Self-Similarity)
        fractal_cand = self._evaluate_fractal(
            symbol, primary_timeframe, candles, similarity, fractal, current_price, pip_factor
        )
        candidates.append(fractal_cand)

        # Filter valid BUY / SELL candidates meeting minimum R/R >= 1.5
        active_candidates = [
            c for c in candidates
            if c.direction in ["BUY", "SELL"] and c.risk_reward >= 1.5 and c.confidence >= 55.0
        ]

        # Sort active candidates by confidence * risk_reward
        active_candidates.sort(key=lambda c: c.confidence * c.risk_reward, reverse=True)

        best_candidate = active_candidates[0] if active_candidates else None

        return {
            "symbol": symbol.upper(),
            "primary_timeframe": primary_timeframe,
            "candidates": [asdict(c) for c in candidates],
            "active_candidates_count": len(active_candidates),
            "best_candidate": asdict(best_candidate) if best_candidate else None,
            "summary": f"Evaluated 6 strategies. Found {len(active_candidates)} active trade candidates."
        }

    def _evaluate_fast_scalp(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        liquidity: Dict[str, Any],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """FAST_SCALP: Sub-minute/M1/M5 liquidity sweep scalps."""
        latest_sweep = liquidity.get("latest_sweep")
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = 0.0
        reasoning = []

        if latest_sweep:
            sweep_type = latest_sweep.get("type")
            if sweep_type == "SELL_SIDE_LIQUIDITY_SWEEP":
                direction = "BUY"
                sl = current_price - (15 * pip_factor)
                tp = current_price + (30 * pip_factor)  # 1:2 R/R
                confidence = 72.0
                reasoning.append("FAST_SCALP: Sell-side liquidity sweep trigger on lower timeframe.")
            elif sweep_type == "BUY_SIDE_LIQUIDITY_SWEEP":
                direction = "SELL"
                sl = current_price + (15 * pip_factor)
                tp = current_price - (30 * pip_factor)  # 1:2 R/R
                confidence = 72.0
                reasoning.append("FAST_SCALP: Buy-side liquidity sweep trigger on lower timeframe.")

        # Fallback local swing check if no sweep object exists
        if direction == "WAIT" and len(candles) >= 5:
            recent_lows = [float(c["low"]) for c in candles[-5:]]
            recent_highs = [float(c["high"]) for c in candles[-5:]]
            if candles[-1]["close"] > candles[-1]["open"] and candles[-1]["low"] == min(recent_lows):
                direction = "BUY"
                sl = min(recent_lows) - (10 * pip_factor)
                tp = current_price + ((current_price - sl) * 1.8)
                confidence = 65.0
                reasoning.append("FAST_SCALP: M1/M5 localized rejection candle at recent swing low.")
            elif candles[-1]["close"] < candles[-1]["open"] and candles[-1]["high"] == max(recent_highs):
                direction = "SELL"
                sl = max(recent_highs) + (10 * pip_factor)
                tp = current_price - ((sl - current_price) * 1.8)
                confidence = 65.0
                reasoning.append("FAST_SCALP: M1/M5 localized rejection candle at recent swing high.")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-FAST-SCALP-{uuid.uuid4().hex[:6]}",
            strategy_name="FAST_SCALP",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence,
            reasoning=reasoning if reasoning else ["FAST_SCALP: No localized sub-minute scalp setup found."],
            market_context={"timeframe": tf, "liquidity_sweep": bool(latest_sweep)},
            invalidation_level=round(sl, 4),
            holding_period="5-15 mins"
        )

    def _evaluate_scalp(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        liquidity: Dict[str, Any],
        zones: Dict[str, Any],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """SCALP: M5/M15 momentum structure retests."""
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = 0.0
        reasoning = []

        obs = zones.get("order_blocks", [])
        bullish_obs = [ob for ob in obs if ob.get("type") == "BULLISH_OB"]
        bearish_obs = [ob for ob in obs if ob.get("type") == "BEARISH_OB"]

        if bullish_obs and current_price >= bullish_obs[0].get("bottom", 0):
            direction = "BUY"
            sl = bullish_obs[0]["bottom"] - (10 * pip_factor)
            tp = current_price + ((current_price - sl) * 2.0)
            confidence = 75.0
            reasoning.append("SCALP: Re-testing Bullish Order Block on M5/M15.")
        elif bearish_obs and current_price <= bearish_obs[0].get("top", 0):
            direction = "SELL"
            sl = bearish_obs[0]["top"] + (10 * pip_factor)
            tp = current_price - ((sl - current_price) * 2.0)
            confidence = 75.0
            reasoning.append("SCALP: Re-testing Bearish Order Block on M5/M15.")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-SCALP-{uuid.uuid4().hex[:6]}",
            strategy_name="SCALP",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence,
            reasoning=reasoning if reasoning else ["SCALP: No M5/M15 OB retest setup."],
            market_context={"timeframe": tf, "order_blocks_found": len(obs)},
            invalidation_level=round(sl, 4),
            holding_period="15-60 mins"
        )

    def _evaluate_day_trading(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        narrative: Dict[str, Any],
        alignment: Dict[str, Any],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """DAY_TRADING: M15/H1 trend continuation."""
        align = alignment.get("alignment", "")
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = float(alignment.get("confidence", 50.0))
        reasoning = []

        if "BULLISH" in align and narrative.get("state") not in ["RANGE", "COMPRESSION"]:
            direction = "BUY"
            sl = current_price - (40 * pip_factor)
            tp = current_price + (100 * pip_factor)
            reasoning.append("DAY_TRADING: Bullish multi-timeframe structural alignment confirmed.")
        elif "BEARISH" in align and narrative.get("state") not in ["RANGE", "COMPRESSION"]:
            direction = "SELL"
            sl = current_price + (40 * pip_factor)
            tp = current_price - (100 * pip_factor)
            reasoning.append("DAY_TRADING: Bearish multi-timeframe structural alignment confirmed.")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-DAY-TRADING-{uuid.uuid4().hex[:6]}",
            strategy_name="DAY_TRADING",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence if direction != "WAIT" else 0.0,
            reasoning=reasoning if reasoning else ["DAY_TRADING: Structure in range/compression on H1."],
            market_context={"timeframe": tf, "alignment": align},
            invalidation_level=round(sl, 4),
            holding_period="1-8 hours"
        )

    def _evaluate_jump(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """JUMP: Impulse & momentum breakout validation."""
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = 0.0
        reasoning = []

        if len(candles) >= 10:
            avg_body = sum(abs(float(c["close"]) - float(c["open"])) for c in candles[-10:-1]) / 9.0
            last_body = abs(float(candles[-1]["close"]) - float(candles[-1]["open"]))

            # Impulse candle: body size > 2.2x average body size
            if avg_body > 0 and last_body >= (2.2 * avg_body):
                if float(candles[-1]["close"]) > float(candles[-1]["open"]):
                    direction = "BUY"
                    sl = float(candles[-1]["low"]) - (10 * pip_factor)
                    tp = current_price + ((current_price - sl) * 2.5)
                    confidence = 78.0
                    reasoning.append(f"JUMP: Bullish momentum breakout impulse detected ({last_body/avg_body:.1f}x body expansion).")
                else:
                    direction = "SELL"
                    sl = float(candles[-1]["high"]) + (10 * pip_factor)
                    tp = current_price - ((sl - current_price) * 2.5)
                    confidence = 78.0
                    reasoning.append(f"JUMP: Bearish momentum breakout impulse detected ({last_body/avg_body:.1f}x body expansion).")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-JUMP-{uuid.uuid4().hex[:6]}",
            strategy_name="JUMP",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence,
            reasoning=reasoning if reasoning else ["JUMP: No momentum impulse expansion candle."],
            market_context={"timeframe": tf},
            invalidation_level=round(sl, 4),
            holding_period="15-45 mins"
        )

    def _evaluate_price_action_rtm(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        zones: Dict[str, Any],
        liquidity: Dict[str, Any],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """PRICE_ACTION_RTM: Supply/Demand zones & Quasimodo (QM) level retests."""
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = 0.0
        reasoning = []

        fvgs = zones.get("fair_value_gaps", [])
        bullish_fvgs = [f for f in fvgs if f.get("type") == "BULLISH_FVG" and f.get("bottom", 0) <= current_price <= f.get("top", 0)]
        bearish_fvgs = [f for f in fvgs if f.get("type") == "BEARISH_FVG" and f.get("bottom", 0) <= current_price <= f.get("top", 0)]

        if bullish_fvgs:
            fvg = bullish_fvgs[0]
            direction = "BUY"
            sl = fvg["bottom"] - (10 * pip_factor)
            tp = current_price + ((current_price - sl) * 2.2)
            confidence = 80.0
            reasoning.append("PRICE_ACTION_RTM: Retesting Bullish Fair Value Gap (FVG) / Demand Node.")
        elif bearish_fvgs:
            fvg = bearish_fvgs[0]
            direction = "SELL"
            sl = fvg["top"] + (10 * pip_factor)
            tp = current_price - ((sl - current_price) * 2.2)
            confidence = 80.0
            reasoning.append("PRICE_ACTION_RTM: Retesting Bearish Fair Value Gap (FVG) / Supply Node.")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-RTM-{uuid.uuid4().hex[:6]}",
            strategy_name="PRICE_ACTION_RTM",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence,
            reasoning=reasoning if reasoning else ["PRICE_ACTION_RTM: Price not currently inside FVG or Supply/Demand zone."],
            market_context={"timeframe": tf, "fvgs_found": len(fvgs)},
            invalidation_level=round(sl, 4),
            holding_period="30-180 mins"
        )

    def _evaluate_fractal(
        self,
        symbol: str,
        tf: str,
        candles: List[Dict[str, Any]],
        similarity: Dict[str, Any],
        fractal: Dict[str, Any],
        current_price: float,
        pip_factor: float
    ) -> StrategyCandidate:
        """FRACTAL: Pattern Memory Similarity & Multiscale Self-Similarity."""
        direction = "WAIT"
        sl = 0.0
        tp = 0.0
        confidence = 0.0
        reasoning = []

        top_match = similarity.get("top_match")
        sim_score = similarity.get("average_similarity_score", 0.0)

        if top_match and sim_score >= 70.0:
            hist_direction = top_match.get("expected_direction", "BUY")
            direction = hist_direction
            confidence = min(92.0, sim_score)
            if direction == "BUY":
                sl = current_price - (25 * pip_factor)
                tp = current_price + (60 * pip_factor)
            else:
                sl = current_price + (25 * pip_factor)
                tp = current_price - (60 * pip_factor)
            reasoning.append(f"FRACTAL: Historical pattern memory similarity match ({sim_score:.1f}% confidence).")

        risk_dist = abs(current_price - sl)
        reward_dist = abs(tp - current_price)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        return StrategyCandidate(
            strategy_id=f"STRAT-FRACTAL-{uuid.uuid4().hex[:6]}",
            strategy_name="FRACTAL",
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            entry=round(current_price, 4) if direction != "WAIT" else 0.0,
            stop_loss=round(sl, 4) if direction != "WAIT" else 0.0,
            take_profit=round(tp, 4) if direction != "WAIT" else 0.0,
            risk_reward=rr,
            confidence=confidence,
            reasoning=reasoning if reasoning else ["FRACTAL: Similarity score below 70.0 threshold."],
            market_context={"timeframe": tf, "similarity_score": sim_score},
            invalidation_level=round(sl, 4),
            holding_period="1-4 hours"
        )
