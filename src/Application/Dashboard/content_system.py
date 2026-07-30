from datetime import datetime
from typing import Dict, Any, List

class ContentItem:
    """Represents a generated content asset (blog post, report, or social update)."""
    def __init__(self, title: str, body: str, category: str, language: str = "en") -> None:
        self.title = title
        self.body = body
        self.category = category  # "blog", "report", "social"
        self.language = language
        self.status = "DRAFT"
        self.fact_checked = False
        self.risk_checked = False
        self.published_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "category": self.category,
            "language": self.language,
            "status": self.status,
            "fact_checked": self.fact_checked,
            "risk_checked": self.risk_checked,
            "published_at": self.published_at
        }


class ContentIntelligenceSystem:
    """
    Simulates TradeYar AI Content Agent Pipelines.
    Implements a multi-agent generation and verification loop:
    Generate -> Fact Check -> Risk Check -> Publish
    """
    def __init__(self) -> None:
        pass

    def run_research_agent(self, topic: str) -> str:
        """Simulates the Research Agent aggregating market facts and raw trends."""
        return f"[Research Fact] Market structure for {topic} shows major consolidation near key horizontal bounds."

    def run_writer_agent(self, research_data: str, category: str) -> Dict[str, str]:
        """Simulates the Writer Agent creating educational or analysis article bodies."""
        if category == "blog":
            title = "Understanding Fractal Market Scales"
            body = f"Education Section: {research_data} Speculators analyze raw structure to uncover price continuation dynamics without presets."
        elif category == "report":
            title = "Daily XAUUSD Structural Analysis Report"
            body = f"Market Report: {research_data} Demand accumulation holds above key hourly zones."
        else:
            title = "Social Snippet"
            body = f"TradeYar AI Daily: {research_data} Raw price action points to stable momentum. #TradingAI"
        return {"title": title, "body": body}

    def run_translator_agent(self, title: str, body: str) -> Dict[str, str]:
        """Simulates the Translator Agent localizing English outputs to Persian (FA)."""
        # Return a mock Persian translation representation
        fa_title = f"[ترجمه] {title} — هوش مصنوعی ترید‌یار"
        fa_body = f"[تحلیل بومی‌سازی شده]: {body}. مدل ترید‌یار از تحلیل‌های عددی ساختار بازار برای تایید فرضیه‌ها استفاده می‌کند."
        return {"title": fa_title, "body": fa_body}

    def run_seo_agent(self, title: str, body: str) -> str:
        """Simulates the SEO Agent appending search-friendly meta descriptions and tags."""
        return f"{body} [SEO Meta Description: Explore advanced AI-driven market discovery and descriptive raw price action analysis.]"

    def run_quality_checker(self, item: ContentItem) -> bool:
        """Simulates the Quality Checker & Fact-Check step."""
        # Ensure it has solid educational guidelines and no forbidden active trading keywords
        forbid = ["place order", "buy signal", "sell signal", "trading alert"]
        content_lower = f"{item.title} {item.body}".lower()
        if any(f in content_lower for f in forbid):
            return False
        item.fact_checked = True
        return True

    def run_risk_checker(self, item: ContentItem) -> bool:
        """Simulates the Risk Check safety gate, appending strict risk disclosures."""
        if "risk" not in item.body.lower():
            item.body += "\n\n[Risk Disclosure: Speculative financial markets contain substantial loss risks. AI results do not guarantee profits.]"
        item.risk_checked = True
        return True

    def generate_and_publish_pipeline(self, topic: str, category: str, language: str = "en") -> Dict[str, Any]:
        """
        Executes the complete multi-agent pipeline:
        Generate -> Fact Check -> Risk Check -> Publish
        """
        # 1. Research
        res = self.run_research_agent(topic)

        # 2. Write
        doc = self.run_writer_agent(res, category)
        title, body = doc["title"], doc["body"]

        # 3. Translate if FA
        if language == "fa":
            trans = self.run_translator_agent(title, body)
            title, body = trans["title"], trans["body"]

        # 4. SEO optimization
        body = self.run_seo_agent(title, body)

        # Create draft content item
        item = ContentItem(title, body, category, language)

        # 5. Quality Fact-Check Gate
        if not self.run_quality_checker(item):
            item.status = "REJECTED_BY_FACT_CHECK"
            return item.to_dict()

        # 6. Risk Check Gate
        if not self.run_risk_checker(item):
            item.status = "REJECTED_BY_RISK_CHECK"
            return item.to_dict()

        # 7. Publish
        item.status = "PUBLISHED"
        item.published_at = datetime.now().isoformat()
        return item.to_dict()
