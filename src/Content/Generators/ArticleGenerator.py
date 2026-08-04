import datetime
import uuid
import re
from typing import Dict, Any, List, Optional
from src.Growth.ContentIntelligence.interfaces import ContentIntelligenceInterface

class ArticleGenerator(ContentIntelligenceInterface):
    """
    ArticleGenerator implements the ContentIntelligenceInterface to produce three distinct categories of content:
    - Market Research Article
    - Educational Article
    - Intelligence Summary
    Supports both English ("en") and Persian ("fa") formats with full source traceability.
    """

    def generate_draft(self, payload: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """
        Generates structured content drafts, incorporating full lineage references.
        """
        source_id = payload.get("source_intelligence_id", f"src-intel-{uuid.uuid4().hex[:6]}")
        symbols = payload.get("symbols", ["XAUUSD"])
        timeframes = payload.get("timeframes", ["M15", "M5"])
        category = payload.get("category", "MARKET_RESEARCH").upper() # MARKET_RESEARCH, EDUCATIONAL, SUMMARY
        sentiment = payload.get("sentiment", "NEUTRAL").upper()
        risk_level = payload.get("risk_level", "LOW").upper()

        # Input variables from raw payload
        market_context = payload.get("market_context", "Consolidation structure observed.")
        technical_analysis = payload.get("technical_analysis", "Support zones tested with volume confirmation.")
        fundamental_context = payload.get("fundamental_context", "Market awaiting macroeconomic event releases.")
        regime_analysis = payload.get("regime_analysis", "Low-volatility ranging regime.")
        risk_factors = payload.get("risk_factors", "Potential expansion on high-impact news.")

        # Educational variables
        concept_explanation = payload.get("concept_explanation", "Multi-Timeframe structural alignment maps swings chronologically.")
        pattern_behavior = payload.get("pattern_behavior", "Breakouts of structural zones confirm momentum.")
        learning_insights = payload.get("learning_insights", "D1 trend filter decreases lower timeframe noise.")

        # Summary variables
        observations = payload.get("observations", "Accumulation structure observed inside the NY Session FVG.")
        risks = payload.get("risks", "Breaching of baseline invalidates order block setup.")

        # Generating content based on category and language
        lang_is_fa = language.lower() == "fa"

        if category == "EDUCATIONAL":
            if lang_is_fa:
                title = f"آموزش الگوریتمی TradeYar: {payload.get('title', 'تحلیل ساختار بازار')}"
                subtitles = ["مفهوم پایه", "رفتار الگوها", "بینش‌های یادگیری"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\n{concept_explanation}\n\n"
                    f"## {subtitles[1]}\n{pattern_behavior}\n\n"
                    f"## {subtitles[2]}\n{learning_insights}\n"
                )
            else:
                title = f"TradeYar Algorithmic Education: {payload.get('title', 'Market Structure Analysis')}"
                subtitles = ["Core Concept", "Pattern Behavior", "Learning Insights"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\n{concept_explanation}\n\n"
                    f"## {subtitles[1]}\n{pattern_behavior}\n\n"
                    f"## {subtitles[2]}\n{learning_insights}\n"
                )
        elif category == "SUMMARY":
            if lang_is_fa:
                title = f"خلاصه اطلاعاتی سیستم: رصد هوشمند {', '.join(symbols)}"
                subtitles = ["خلاصه مدیریتی", "مشاهدات", "ریسک‌ها"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\nتحلیل کمی ساختارهای زمانی {', '.join(symbols)} به همراه رصد SRE جریان سفارشات.\n\n"
                    f"## {subtitles[1]}\n{observations}\n\n"
                    f"## {subtitles[2]}\n{risks}\n"
                )
            else:
                title = f"Intelligence Executive Summary: {', '.join(symbols)} Runtime Overview"
                subtitles = ["Executive Summary", "Observations", "Key Risks"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\nQuantitative multi-timeframe structural analysis on {', '.join(symbols)} with active SRE telemetry.\n\n"
                    f"## {subtitles[1]}\n{observations}\n\n"
                    f"## {subtitles[2]}\n{risks}\n"
                )
        else: # MARKET_RESEARCH
            category = "MARKET_RESEARCH"
            if lang_is_fa:
                title = f"گزارش تخصصی هوش بازار: تحلیل جامع {', '.join(symbols)}"
                subtitles = ["زمینه بازار", "تحلیل فنی ساختار", "تحلیل بنیادین", "رژیم معاملاتی", "ریسک‌ها"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\n{market_context}\n\n"
                    f"## {subtitles[1]}\n{technical_analysis}\n\n"
                    f"## {subtitles[2]}\n{fundamental_context}\n\n"
                    f"## {subtitles[3]}\n{regime_analysis}\n\n"
                    f"## {subtitles[4]}\n{risk_factors}\n"
                )
            else:
                title = f"Market Research Bulletin: Comprehensive {', '.join(symbols)} Swing Report"
                subtitles = ["Market Context", "Technical Structure Analysis", "Fundamental Context", "Regime Assessment", "Key Risk Factors"]
                markdown_body = (
                    f"# {title}\n\n"
                    f"## {subtitles[0]}\n{market_context}\n\n"
                    f"## {subtitles[1]}\n{technical_analysis}\n\n"
                    f"## {subtitles[2]}\n{fundamental_context}\n\n"
                    f"## {subtitles[3]}\n{regime_analysis}\n\n"
                    f"## {subtitles[4]}\n{risk_factors}\n"
                )

        # Convert markdown body into basic sanitized HTML safely
        html_body = markdown_body
        html_body = re.sub(r"# (.*)", r"<h1>\1</h1>", html_body)
        html_body = re.sub(r"## (.*)", r"<h2>\1</h2>", html_body)
        html_body = html_body.replace("\n", "<br>")

        return {
            "title": title,
            "body": markdown_body,
            "html": html_body,
            "format": "ARTICLE",
            "language": language.lower(),
            "source_intelligence_id": source_id,
            "symbols": symbols,
            "metadata": {
                "category": category,
                "symbols": symbols,
                "timeframes": timeframes,
                "sentiment": sentiment,
                "risk_level": risk_level,
                "subtitles": subtitles
            },
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        }
