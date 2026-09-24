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
        lang: str = "fa",
        newborn_brain_report: Optional[Dict[str, Any]] = None
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

        # Consume explicit LiveAnalysisBrain proposal
        brain_suggested_action = "WAIT"
        brain_report_consumed = False
        if newborn_brain_report and isinstance(newborn_brain_report, dict):
            brain_report_consumed = True
            hypotheses = newborn_brain_report.get("active_hypotheses", [])
            if hypotheses and isinstance(hypotheses, list) and len(hypotheses) > 0:
                brain_suggested_action = str(hypotheses[0].get("suggested_virtual_action", "WAIT")).upper()
            else:
                brain_suggested_action = str(newborn_brain_report.get("suggested_virtual_action", "WAIT")).upper()

        if brain_suggested_action not in ["BUY", "SELL", "WAIT", "AVOID"]:
            brain_suggested_action = "WAIT"

        # Formulate Advisory Setup based on Brain Proposal & Structural Alignment
        action = "WAIT"
        entry = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        confidence = float(alignment.get("confidence", 50))

        trend = narrative.get("trend", "NEUTRAL")
        latest_sweep = liquidity.get("latest_sweep")
        obs = zones.get("order_blocks", [])
        fvgs = zones.get("fair_value_gaps", [])

        # Governance Invariant: When Brain report is consumed, Brain proposal constrains Planner
        if brain_report_consumed:
            if brain_suggested_action in ["WAIT", "AVOID"]:
                action = brain_suggested_action
            else:
                # Brain proposed BUY or SELL: Planner validates against structural alignment and formats trade parameters
                if brain_suggested_action == "BUY" and "BULLISH" in alignment.get("alignment", ""):
                    action = "BUY"
                    entry = current_price
                    stop_loss = current_price - (current_price * 0.01) # fallback 1%
                    if obs:
                        bullish_obs = [ob for ob in obs if ob["type"] == "BULLISH_OB"]
                        if bullish_obs:
                            stop_loss = max(stop_loss, bullish_obs[0]["bottom"])

                    take_profit = current_price + (current_price * 0.02) # fallback 2%
                    resting_bsl = liquidity.get("resting_bsl", [])
                    if resting_bsl:
                        take_profit = resting_bsl[0]["level"]

                elif brain_suggested_action == "SELL" and "BEARISH" in alignment.get("alignment", ""):
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
                else:
                    action = "WAIT"
        else:
            # Fallback path when direct LiveAnalysisBrain report is not passed: evaluate structural alignment
            if "BULLISH" in alignment.get("alignment", ""):
                action = "BUY"
                entry = current_price
                stop_loss = current_price - (current_price * 0.01)
                if obs:
                    bullish_obs = [ob for ob in obs if ob["type"] == "BULLISH_OB"]
                    if bullish_obs:
                        stop_loss = max(stop_loss, bullish_obs[0]["bottom"])

                take_profit = current_price + (current_price * 0.02)
                resting_bsl = liquidity.get("resting_bsl", [])
                if resting_bsl:
                    take_profit = resting_bsl[0]["level"]
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

        # Strategy identity is strictly Multi-Timeframe Continuous Market Intelligence Core
        selected_strategy_name = "Multi-Timeframe Continuous Market Intelligence"

        # If market state is ranging or in compression without strong alignment, default to WAIT
        if narrative.get("state") in ["COMPRESSION", "RANGE"] and action != "WAIT":
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

        # Provenance metadata
        data_source = narrative.get("data_source", "MT5_XAUUSD_M1_RATES")
        data_mode = narrative.get("data_mode", "REAL")
        candle_count = narrative.get("candle_count", 30)
        latest_candle_timestamp = narrative.get("latest_candle_timestamp", "")
        context_identity = narrative.get("context_identity", "ctx-xauusd-mtf-brain")
        decision_cycle_id = narrative.get("decision_cycle_id", "cycle-mtf-brain-xauusd")

        decision_state = "BUY" if action == "BUY" else ("SELL" if action == "SELL" else "NO_TRADE")

        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "plan": {
                "action": action,
                "decision": decision_state,
                "decision_source": "BRAIN",
                "brain_suggested_action": brain_suggested_action,
                "brain_report_consumed": brain_report_consumed,
                "strategy": selected_strategy_name,
                "entry": entry if action in ["BUY", "SELL"] else 0.0,
                "stop_loss": stop_loss if action in ["BUY", "SELL"] else 0.0,
                "take_profit": take_profit if action in ["BUY", "SELL"] else 0.0,
                "risk_reward": rr if action in ["BUY", "SELL"] else 0.0,
                "confidence": confidence if action in ["BUY", "SELL"] else 0.0,
                "reasoning": reasoning,
                "data_source": data_source,
                "data_mode": data_mode,
                "candle_count": candle_count,
                "latest_candle_timestamp": latest_candle_timestamp,
                "context_identity": context_identity,
                "risk_budget_percent": 1.0,
                "decision_cycle_id": decision_cycle_id
            }
        }
