from datetime import datetime, timezone
from typing import Dict, Any, List

class DailyIntelligenceAgent:
    """
    Daily Intelligence Agent generates high-fidelity daily market briefs.
    Enforces strict disclaimers explicitly blocking any direct signals or financial advice.
    """

    def __init__(self, agent_id: str = "agent-daily-intel"):
        self.agent_id = agent_id

    def generate_daily_brief(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        symbol_upper = symbol.upper()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Determine brief narrative based on provided inputs
        structure = market_data.get("structure", "Range")
        liquidity = market_data.get("liquidity", "Consolidated")
        volatility = market_data.get("volatility", "Normal")

        brief_text = (
            f"Daily technical brief for {symbol_upper} at {now}. "
            f"Market structure is identified as {structure} under {volatility} volatility. "
            f"Liquidity clusters are observed around {liquidity} levels. "
            f"AI interpretive assessment models indicate moderate confidence."
        )

        return {
            "agent_id": self.agent_id,
            "timestamp": now,
            "symbol": symbol_upper,
            "brief": brief_text,
            "volatility": volatility,
            "structure": structure,
            "liquidity": liquidity,
            "disclaimer": (
                "DISCLAIMER: This document is for educational and market research purposes only. "
                "It does not constitute financial advice, buy/sell trading signals, investment recommendations, "
                "or profitability guarantees. Treat all data as simulation parameters only."
            )
        }


class ResearchPublisherAgent:
    """
    Research Publisher Agent produces comprehensive weekly and monthly reports.
    Integrates market context, historical analyses, scenario structures, and conclusion statements.
    """

    def __init__(self, agent_id: str = "agent-research-publisher"):
        self.agent_id = agent_id

    def publish_report(self, symbol: str, report_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol_upper = symbol.upper()
        type_upper = report_type.upper() # WEEKLY, MONTHLY, DAILY
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        market_context = data.get("market_context", "Broad multi-asset lateral trend.")
        historical_analysis = data.get("historical_analysis", "Consistent historical support zones intact.")
        scenario_bullish = data.get("scenario_bullish", "Expansion above current fair-value gap levels.")
        scenario_bearish = data.get("scenario_bearish", "Break down below low-volatility baseline zones.")
        conclusion = data.get("conclusion", "Remain vigilant under pending macroeconomic event releases.")

        return {
            "report_id": f"rep-{symbol_upper[:3]}-{type_upper[:3]}-{now[:10]}",
            "agent_id": self.agent_id,
            "published_at": now,
            "symbol": symbol_upper,
            "report_type": type_upper,
            "market_context": market_context,
            "historical_analysis": historical_analysis,
            "scenarios": {
                "bullish": scenario_bullish,
                "bearish": scenario_bearish
            },
            "conclusion": conclusion,
            "disclaimer": (
                "DISCLAIMER: This research analysis is purely advisory and descriptive. "
                "Past performance is not indicative of future market results. Zero financial advisory is offered."
            )
        }
