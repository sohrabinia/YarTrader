import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("SupportAgent")

class ConversationalSupportAgent:
    """
    Enterprise Conversational AI Support Assistant for YarTrader.
    Provides natural language explanations regarding account access, wallet balances,
    trading intelligence signals, prop challenge compliance rules, and learning feedback.
    Never hallucinates account state, payment status, or trading authority.
    """
    def __init__(self) -> None:
        self.domain_knowledge = {
            "platform": "YarTrader is an autonomous financial intelligence platform for non-linear XAUUSD structural analysis and risk controls.",
            "broker": "YarTrader is strictly NOT a broker. It does not hold user deposits or investor funds.",
            "trading_modes": "Supports Backtest (past historical simulation), Demo (MT5 demo order execution), and Shadow (virtual paper paper-trading). Live trading is hard-blocked (LIVE_TRADING_ENABLED=False).",
            "prop_challenge": "Monitors prop firm evaluation rules including daily loss limit, max drawdown %, and exposure limits with live compliance alerts.",
            "risk_limits": "Enforces 2.0% max per-trade risk ceiling and an independent 8.0% daily loss kill switch."
        }

    def process_user_query(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        lang: str = "fa"
    ) -> Dict[str, Any]:
        """
        Processes a natural language user query with authenticated session context awareness.
        """
        if not query or not query.strip():
            return {
                "answer": "لطفاً سوال خود را مطرح کنید." if lang == "fa" else "Please enter your question.",
                "confidence": 1.0,
                "category": "GENERAL"
            }

        q_lower = query.lower()
        user_ctx = user_context or {}
        user_name = user_ctx.get("name", "کاربر گرامی" if lang == "fa" else "Valued User")

        # 1. Account & Login Queries
        if "ورود" in q_lower or "حساب" in q_lower or "login" in q_lower or "password" in q_lower:
            ans = (
                f"{user_name} عزیز، جهت ورود می‌توانید از ایمیل و رمز عبور یا ورود امن با گوگل استفاده کنید. در صورت فراموشی رمز عبور، لینک بازیابی به ایمیل شما ارسال می‌شود."
                if lang == "fa" else
                f"Dear {user_name}, you can sign in using your email/password or Google OIDC. For password recovery, use the reset link sent to your verified email."
            )
            return {"answer": ans, "confidence": 0.95, "category": "AUTH"}

        # 2. Wallet & Financial Ledger Queries
        elif "کیف پول" in q_lower or "موجودی" in q_lower or "wallet" in q_lower or "balance" in q_lower or "واریز" in q_lower or "تراکنش" in q_lower:
            ans = (
                f"حسابداری YarTrader بر پایه دفتر کل دوبل (Double-Entry Ledger) عمل می‌کند. موجودی و تراکنش‌های رسمی در بخش /wallet قابل مشاهده است."
                if lang == "fa" else
                f"YarTrader operates on a double-entry accounting ledger. Your available balance, invoices, and transaction history are managed in the /wallet view."
            )
            return {"answer": ans, "confidence": 0.95, "category": "FINANCE"}

        # 3. Prop Challenge Rules
        elif "پراپ" in q_lower or "چالش" in q_lower or "prop" in q_lower or "challenge" in q_lower or "drawdown" in q_lower:
            ans = (
                "پلن چالش پراپ قوانین حد ضرر روزانه، حداکثر افت سرمایه و حجم معامله را پایش می‌کند. هشدارها به صورت زنده صادر می‌شوند."
                if lang == "fa" else
                "The Prop Firm Challenge Plan monitors daily loss limits, max drawdown %, and exposure bounds with real-time compliance alerts."
            )
            return {"answer": ans, "confidence": 0.95, "category": "PROP_FIRM"}

        # 4. Trading Signals & Non-Trading Safety
        elif "سیگنال" in q_lower or "معامله" in q_lower or "signal" in q_lower or "trade" in q_lower or "wait" in q_lower:
            ans = (
                "تصمیم معامله بر اساس تحلیل غیرخطی و ۳ گیت کلان، ساختاری و ریسک اتخاذ می‌شود. کلیه سیگنال‌ها پیش از اجرا ارزیابی شده و در صورت عدم احراز شرایط، وضعیت WAIT (انتظار) اعلام می‌شود."
                if lang == "fa" else
                "Trading decision is based on non-linear structure and 3 strict gates (Macro, Structural, Risk). If any gate fails, direction remains WAIT."
            )
            return {"answer": ans, "confidence": 0.95, "category": "TRADING"}

        # 5. Default General Conversational Response
        else:
            ans = (
                f"{user_name} عزیز، پیام شما دریافت شد. سیستم هوش مصنوعی YarTrader بر اساس ساختارهای غیرخطی بازار و کنترل ریسک عمل می‌کند. چطور می‌توانم در زمینه سیستم یا کیف پول به شما کمک کنم؟"
                if lang == "fa" else
                f"Dear {user_name}, your query has been received. YarTrader operates on non-linear price structures and strict risk controls. How can I assist you with the platform or wallet today?"
            )
            return {"answer": ans, "confidence": 0.85, "category": "GENERAL"}

    def respond(self, message: str, lang: str = "fa", user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Convenience responder returning a direct answer string.
        """
        res = self.process_user_query(query=message, user_context=user_context, lang=lang)
        return res.get("answer", "")

global_support_agent = ConversationalSupportAgent()
