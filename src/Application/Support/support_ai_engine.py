import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupportQuery:
    """
    Immutable domain representation of an incoming user support or explanation query.
    """
    message: str
    symbol: str = "XAUUSD"
    interval: str = "M15"
    strategy: str = "TREND"
    lang: str = "fa"
    user_context: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if not self.message or not isinstance(self.message, str) or not self.message.strip():
            raise ValidationException("SupportQuery message must be a non-empty string.")
        if len(self.message) > 1000:
            raise ValidationException("SupportQuery message length cannot exceed 1000 characters.")


@dataclass(frozen=True)
class SupportResponse:
    """
    Immutable domain representation of a grounded support AI response.
    """
    response_text: str
    status: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response_text,
            "status": self.status,
            "timestamp": self.timestamp.isoformat()
        }


class SupportAIEngine:
    """
    Pure, deterministic Support AI Domain Engine.
    Processes support queries and maps them to explainable, grounded responses
    using actual Phase 10–16 foundation summaries and DecisionExplainer outputs.
    Strictly forbids hallucinating account balances, positions, orders, or P&L.
    """

    def generate_response(
        self,
        query: SupportQuery,
        foundation_data: Optional[Dict[str, Any]] = None
    ) -> SupportResponse:
        query.validate()
        msg_lower = query.message.strip().lower()
        lang = (query.lang or "fa").lower()

        # Account / Private state check
        if any(term in msg_lower for term in ["موجودی", "بالانس", "سود", "زیان", "پوزیشن", "سفارش", "balance", "pnl", "equity", "position", "order"]):
            user_ctx = query.user_context
            if not user_ctx or not user_ctx.get("authenticated"):
                resp_text = (
                    "اطلاعات حساب کاربری در دسترس نیست. جهت دسترسی به وضعیت حساب خود لطفاً ابتدا وارد شوید."
                    if lang == "fa" else
                    "I don't have access to your private account state. Please sign in to access your account information."
                )
                return SupportResponse(response_text=resp_text, status="UNAUTHENTICATED_ACCESS_LIMIT")

            # Check if actual account balance is available in user context
            balance_val = user_ctx.get("balance")
            if balance_val is None:
                resp_text = (
                    "اطلاعات حساب کاربری در لایه فعلی در دسترس نیست. سیستم در وضعیت ایزوله بدون دسترسی به حساب واقعی عمل می‌کند."
                    if lang == "fa" else
                    "Account state is currently unavailable in this environment."
                )
                return SupportResponse(response_text=resp_text, status="DATA_UNAVAILABLE_LIMIT")

            resp_text = (
                f"موجودی حساب کاربری شما: {balance_val} دلار."
                if lang == "fa" else
                f"Your account balance is: ${balance_val}."
            )
            return SupportResponse(response_text=resp_text, status="ACCOUNT_CONTEXT_PROVIDED")

        # System / Foundation Domain Explanations
        if foundation_data:
            gov_data = foundation_data.get("governance")
            if "حاکمیت" in msg_lower or "governance" in msg_lower:
                if gov_data:
                    state = gov_data.get("governance_state", "UNKNOWN")
                    quality = gov_data.get("evidence_quality", "UNKNOWN")
                    resp_text = (
                        f"وضعیت حاکمیت تصمیم‌گیری برای {query.symbol}: {state} (کیفیت داده: {quality})."
                        if lang == "fa" else
                        f"Decision governance status for {query.symbol}: {state} (Data Quality: {quality})."
                    )
                    return SupportResponse(response_text=resp_text, status="GOVERNANCE_EXPLAINED")

            intel_data = foundation_data.get("intelligence")
            if "هوش" in msg_lower or "intelligence" in msg_lower or "آمادگی" in msg_lower:
                if intel_data:
                    readiness = intel_data.get("decision_readiness_state", "UNKNOWN")
                    score = intel_data.get("context_sufficiency_score", 0.0)
                    resp_text = (
                        f"ارزیابی هوش تاریخی برای {query.symbol}: وضعیت آمادگی = {readiness} (امتیاز کفایت داده = {score})."
                        if lang == "fa" else
                        f"Historical intelligence status for {query.symbol}: Readiness = {readiness} (Sufficiency score = {score})."
                    )
                    return SupportResponse(response_text=resp_text, status="INTELLIGENCE_EXPLAINED")

        # General Concept / Decision Explanation Fallback
        if any(term in msg_lower for term in ["یادگیری", "یاد", "learn", "cognition"]):
            resp_text = (
                "لایه‌های یادگیری آماری (Phase 11) و حافظه ساختاریافته (Phase 12) فراوانی سیگنال‌ها را محاسبه و ثبت می‌کنند. هیچ مدل ML غیرشفافی استفاده نمی‌شود."
                if lang == "fa" else
                "Statistical learning (Phase 11) and Memory Foundation (Phase 12) track historical signal frequencies deterministically."
            )
        elif any(term in msg_lower for term in ["معامله نکرد", "not trade", "why didn"]):
            resp_text = (
                "عدم انجام معامله به دلیل عدم برآورده شدن شروط گیت حاکمیت (Phase 16) یا حد آستانه حجم/ریسک است."
                if lang == "fa" else
                "No trade was triggered because Decision Governance (Phase 16) or risk gates were not satisfied."
            )
        elif any(term in msg_lower for term in ["چرا", "why", "باز", "open"]):
            resp_text = (
                f"استراتژی {query.strategy} بر اساس داده‌های تاریخی {query.symbol} و همگرایی ساختاری محاسبه می‌شود. سیستم از الگوریتم‌های قطعی بدون خطای نگاه به آینده استفاده می‌کند."
                if lang == "fa" else
                f"The {query.strategy} strategy evaluates market structure on {query.symbol} using deterministic algorithms without look-ahead bias."
            )
        else:
            resp_text = (
                "پلتفرم YarTrader یک سیستم تحلیل خودکار و بدون وابستگی به شاخص‌های تاخیری است. تمام محاسبات و ارزیابی‌های حاکمیتی بر اساس شواهد قطعی تاریخی انجام می‌شوند."
                if lang == "fa" else
                "YarTrader is an autonomous cognitive research platform evaluating non-linear market structure deterministically."
            )

        return SupportResponse(response_text=resp_text, status="GENERAL_EXPLANATION_PROVIDED")
