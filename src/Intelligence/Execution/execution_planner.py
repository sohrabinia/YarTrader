from typing import List, Dict, Any, Optional
from src.Intelligence.Execution.xai import ExplainableExecutionIntelligence

class ExecutionIntelligencePlanner:
    """
    Synthesizes narrative, liquidity, zones, alignment, and risk factors
    into structured, explainable execution plans (BUY, SELL, WAIT, AVOID).
    Acts as an advisory engine only; strictly does NOT place actual orders.
    """
    def __init__(self) -> None:
        self.xai = ExplainableExecutionIntelligence()

    def generate_execution_plan(
        self,
        symbol: str,
        timeframe: str,
        narrative: Dict[str, Any],
        liquidity: Dict[str, Any],
        zones: Dict[str, Any],
        alignment: Dict[str, Any],
        similarity: Dict[str, Any],
        portfolio_risk: Dict[str, Any],
        current_price: float,
        strategy_eval: Optional[Dict[str, Any]] = None,
        lang: str = "fa"
    ) -> Dict[str, Any]:
        """
        Synthesizes technical analysis parameters and portfolio risk rules to generate
        a highly structured, advisory-only execution plan.
        """
        # Strict governance: if portfolio risk is not approved, override to AVOID
        if not portfolio_risk.get("approved", True):
            avoid_reasons = [
                "Portfolio risk limits violated!" if lang == "en" else "محدودیت‌های ریسک سبد دارایی نقض شده است!"
            ] + portfolio_risk.get("violations", [])
            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "plan": {
                    "action": "AVOID",
                    "entry": 0.0,
                    "stop_loss": 0.0,
                    "take_profit": 0.0,
                    "risk_reward": 0.0,
                    "confidence": 0.0,
                    "reasoning": avoid_reasons
                }
            }

        # Formulate Advisory Setup based on detected Liquidity Sweeps or Order Block retests
        action = "WAIT"
        entry = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        confidence = float(alignment.get("confidence", 50))

        trend = narrative.get("trend", "NEUTRAL")
        latest_sweep = liquidity.get("latest_sweep")
        obs = zones.get("order_blocks", [])
        fvgs = zones.get("fair_value_gaps", [])

        # Long Trigger: Swept Sell Side Liquidity, or retesting Bullish OB, and aligned bullish
        if "BULLISH" in alignment.get("alignment", ""):
            action = "BUY"
            entry = current_price
            # Stop loss below the lowest of recent swing low or OB bottom
            stop_loss = current_price - (current_price * 0.01) # fallback 1%
            if obs:
                bullish_obs = [ob for ob in obs if ob["type"] == "BULLISH_OB"]
                if bullish_obs:
                    stop_loss = max(stop_loss, bullish_obs[0]["bottom"])

            # Take profit near resting buy side liquidity or nearest bearish OB
            take_profit = current_price + (current_price * 0.02) # fallback 2%
            resting_bsl = liquidity.get("resting_bsl", [])
            if resting_bsl:
                take_profit = resting_bsl[0]["level"]

        # Short Trigger: Swept Buy Side Liquidity, or retesting Bearish OB, and aligned bearish
        elif "BEARISH" in alignment.get("alignment", ""):
            action = "SELL"
            entry = current_price
            stop_loss = current_price + (current_price * 0.01)
            if obs:
                bearish_obs = [ob for ob in obs if ob["type"] == "BEARISH_OB"]
                if bearish_obs:
                    stop_loss = min(stop_loss, bearish_obs[0]["top"])

            take_profit = current_price - (current_price * 0.02)
            resting_ssl = liquidity.get("resting_ssl", [])
            if resting_ssl:
                take_profit = resting_ssl[0]["level"]

        # Incorporate StrategyOrchestrator candidates if primary alignment is WAIT or H1 is ranging
        selected_strategy_name = "DAY_TRADING"
        if strategy_eval and strategy_eval.get("best_candidate"):
            best_cand = strategy_eval["best_candidate"]
            cand_direction = best_cand.get("direction", "WAIT")
            if cand_direction in ["BUY", "SELL"]:
                # If primary HTF alignment is WAIT/RANGE, allow valid lower-timeframe strategy candidate (FAST_SCALP, SCALP, JUMP, RTM, FRACTAL)
                if action == "WAIT" or narrative.get("state") in ["COMPRESSION", "RANGE"]:
                    action = cand_direction
                    entry = float(best_cand.get("entry", current_price))
                    stop_loss = float(best_cand.get("stop_loss", 0.0))
                    take_profit = float(best_cand.get("take_profit", 0.0))
                    confidence = float(best_cand.get("confidence", 70.0))
                    selected_strategy_name = best_cand.get("strategy_name", "FAST_SCALP")

        # If ranging or compression and NO valid strategy candidate exists, set WAIT
        elif narrative.get("state") in ["COMPRESSION", "RANGE"] and action != "WAIT":
            action = "WAIT"

        # Calculate risk reward
        risk_dist = abs(entry - stop_loss)
        reward_dist = abs(take_profit - entry)
        rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

        # Build reasoning array
        sweep_type = latest_sweep["type"] if latest_sweep else None
        reasoning = self.xai.build_reasoning_array(
            action=action,
            alignment=alignment.get("alignment", "UNALIGNED"),
            confidence=confidence,
            trend=trend,
            liquidity_event=sweep_type,
            lang=lang
        )

        # Enforce round numbers
        entry = round(entry, 4)
        stop_loss = round(stop_loss, 4)
        take_profit = round(take_profit, 4)

        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "plan": {
                "action": action,
                "strategy": selected_strategy_name,
                "entry": entry if action in ["BUY", "SELL"] else 0.0,
                "stop_loss": stop_loss if action in ["BUY", "SELL"] else 0.0,
                "take_profit": take_profit if action in ["BUY", "SELL"] else 0.0,
                "risk_reward": rr if action in ["BUY", "SELL"] else 0.0,
                "confidence": confidence if action in ["BUY", "SELL"] else 0.0,
                "reasoning": reasoning
            }
        }
