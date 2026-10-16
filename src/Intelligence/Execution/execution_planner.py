"""Fail-closed compatibility facade for execution plans.

The hierarchical Base behavior and costed Base-reaction engines are the only
strategy authority. This legacy planner deliberately cannot emit BUY or SELL.
"""
from typing import Dict, Any, Optional


class ExecutionIntelligencePlanner:
    """Compatibility facade that never manufactures an alternative strategy signal."""

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
        newborn_brain_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return WAIT unless an independent risk gate requires AVOID.

        Inputs from Brain hypotheses, narrative, liquidity, zones, alignment and
        similarity are telemetry only. No Base plan was supplied to this legacy
        interface, so it cannot author an entry, stop or target.
        """
        del liquidity, zones, alignment, similarity, current_price, strategy_eval, lang, newborn_brain_report
        risk_blocked = not portfolio_risk.get("approved", True)
        action = "AVOID" if risk_blocked else "WAIT"
        reason = (
            "Portfolio risk gate blocked the setup."
            if risk_blocked
            else "No validated Base-hierarchy plan supplied; legacy planner cannot emit a trade."
        )
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "plan": {
                "action": action,
                "decision": action,
                "strategy": "BASE_HIERARCHY",
                "status": action,
                "entry": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "risk_reward": 0.0,
                "confidence": 0.0,
                "reason": reason,
                "reasoning": [reason],
                "decision_source": "BASE_HIERARCHY_ONLY",
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "data_source": narrative.get("data_source", "UNKNOWN"),
                "data_mode": narrative.get("data_mode", "UNKNOWN"),
                "candle_count": narrative.get("candle_count", 0),
                "latest_candle_timestamp": narrative.get("latest_candle_timestamp", ""),
                "context_identity": narrative.get("context_identity", ""),
                "decision_cycle_id": narrative.get("decision_cycle_id", ""),
            },
        }
