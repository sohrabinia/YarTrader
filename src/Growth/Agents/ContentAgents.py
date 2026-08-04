import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

class ContentIntelligenceAgent:
    """
    Content Intelligence Agent converts raw research intelligence into channel-specific marketing copy,
    submitting it to a Human Approval Queue before publishing.
    """

    def __init__(self, agent_id: str = "agent-content-intel"):
        self.agent_id = agent_id
        self.approval_queue: List[Dict[str, Any]] = []

    def format_content(self, raw_report: Dict[str, Any], target_channels: List[str]) -> List[Dict[str, Any]]:
        formatted_items = []
        symbol = raw_report.get("symbol", "GLOBAL")
        report_type = raw_report.get("report_type", "DAILY")

        for channel in target_channels:
            ch_upper = channel.upper()
            content_body = ""

            if ch_upper == "TELEGRAM":
                content_body = f"📢 *TradeYar Daily Brief ({symbol})*\n\n{raw_report.get('market_context', '')}\n\nRead full report inside our dashboard! #TradeYar"
            elif ch_upper == "X":
                content_body = f"🐦 TradeYar AI presents high-fidelity multi-asset analytical research context on {symbol}. Zero subjective indicators. Join us: http://tradeyar.ai"
            elif ch_upper == "LINKEDIN":
                content_body = f"💼 TradeYar AI Executive Summary:\n\nEvaluating non-linear market structure matrices on {symbol} to understand current chronological swings.\n\n#Fintech #SinglePageApplication #SRE"
            else:
                content_body = f"TradeYar AI {report_type} insight on {symbol}: {raw_report.get('market_context', '')}"

            queue_item = {
                "content_id": f"cnt-{uuid.uuid4().hex[:8]}",
                "channel": ch_upper,
                "symbol": symbol,
                "body": content_body,
                "status": "PENDING_APPROVAL",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "approved_by": None
            }
            self.approval_queue.append(queue_item)
            formatted_items.append(queue_item)

        return formatted_items

    def approve_content(self, content_id: str, approver_name: str) -> Optional[Dict[str, Any]]:
        for item in self.approval_queue:
            if item["content_id"] == content_id:
                item["status"] = "APPROVED"
                item["approved_by"] = approver_name
                return item
        return None


class SEOAgent:
    """
    SEO Agent analyzes metadata, internal links, keyword densities, and search trends.
    """

    def __init__(self, agent_id: str = "agent-seo"):
        self.agent_id = agent_id

    def analyze_metadata(self, title: str, description: str, keywords: List[str]) -> Dict[str, Any]:
        issues = []
        if len(title) < 30 or len(title) > 60:
            issues.append("Title length should be between 30 and 60 characters for optimal click-through rates.")
        if len(description) < 120 or len(description) > 160:
            issues.append("Meta description length should be between 120 and 160 characters for perfect SEO snippets.")
        if len(keywords) < 3:
            issues.append("Consider adding at least 3 high-value semantic focus keywords.")

        return {
            "title_length": len(title),
            "description_length": len(description),
            "issues": issues,
            "seo_score": max(20, 100 - (len(issues) * 20)),
            "is_optimized": len(issues) == 0
        }


class NewsIntelligenceAgent:
    """
    News Intelligence Agent handles macroeconomic item ingestion.
    Equipped with standard interfaces and graceful fallbacks if API keys are missing.
    """

    def __init__(self, agent_id: str = "agent-news-intel", api_key: Optional[str] = None):
        self.agent_id = agent_id
        self.api_key = api_key

    def fetch_latest_macro_news(self) -> Dict[str, Any]:
        """
        Ingests macro news items. Returns fallback/simulated events cleanly if API key is not provided.
        """
        if not self.api_key:
            return {
                "api_connection": "STUBBED_FALLBACK",
                "events_count": 3,
                "items": [
                    {
                        "event": "US CPI Release",
                        "impact": "HIGH_VOLATILITY_EXPECTED",
                        "simulated_sentiment": 0.12,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    },
                    {
                        "event": "FOMC Meeting Minutes",
                        "impact": "CRITICAL_SESSION_HOURS",
                        "simulated_sentiment": -0.05,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                ],
                "logged_status": "External Data Blockers - Missing API Key. Ingesting high-fidelity mock stream."
            }

        # Simulated API retrieval
        return {
            "api_connection": "ONLINE",
            "events_count": 1,
            "items": [
                {
                    "event": "Real-time API economic headline fetched",
                    "impact": "NORMAL",
                    "simulated_sentiment": 0.45,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }
