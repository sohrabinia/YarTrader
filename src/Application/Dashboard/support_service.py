from typing import List, Dict, Any

class SupportAIService:
    """
    Production-grade AI Support Assistant with conversational persistence,
    automated knowledge base/FAQ matching, and escalation channels to administrators.
    """
    def __init__(self) -> None:
        # Persistence map: user_email -> list of message dicts
        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        # Escalated status: user_email -> bool
        self._escalated: Dict[str, bool] = {}

        # Localized Knowledge Base FAQ matching
        self._faq_en = {
            "risk": "Trading financial speculation involves high capital risks. Please check our Risk Disclosure page.",
            "price": "TradeYar subscription is $29.99/mo for the PRO tier and $99.99/mo for the PREMIUM tier.",
            "monetize": "You can upgrade to premium tiers dynamically inside the dashboard and unlock advanced analysis views.",
            "mt5": "Our MT5 provider connects directly to real terminal feeds in read-only passive mode.",
            "guarantee": "No. Speculative assets never guarantee profit. Past success is not indicative of future outcomes."
        }
        self._faq_fa = {
            "ریسک": "معاملات در بازارهای مالی حاوی ریسک بسیار بالایی است. لطفاً بخش سلب مسئولیت را بخوانید.",
            "قیمت": "اشتراک ویژه ترید‌یار برای سطح PRO ماهانه ۲۹.۹۹ دلار و برای سطح PREMIUM ماهانه ۹۹.۹۹ دلار است.",
            "خرید": "شما می‌توانید به صورت مستقیم در پنل کاربری خود اقدام به ارتقای طرح کاربری نمایید.",
            "متاتریدر": "اتصال ما به متاتریدر ۵ کاملاً به صورت غیرفعال و فقط خواندنی (بدون دسترسی معاملات) می‌باشد.",
            "تضمین": "خیر. در بازارهای مالی هیچ تضمین سود قطعی وجود ندارد. عملکردهای گذشته تضمینی برای آینده نیست."
        }

    def add_message(self, email: str, sender: str, text: str) -> None:
        """Adds a message to the conversation history thread."""
        email_clean = email.strip().lower()
        if email_clean not in self._conversations:
            self._conversations[email_clean] = []
        self._conversations[email_clean].append({
            "sender": sender,  # "USER", "AI", "ADMIN"
            "text": text
        })

    def get_conversation_history(self, email: str) -> List[Dict[str, str]]:
        """Retrieves full conversation history list for a user."""
        email_clean = email.strip().lower()
        return self._conversations.get(email_clean, [])

    def process_ai_query(self, email: str, query: str, language: str = "en") -> str:
        """
        Processes user question, matches local Knowledge Base FAQ if triggered,
        applies conversational persistence, and returns AI answer.
        """
        self.add_message(email, "USER", query)
        query_lower = query.lower()

        # Match FAQ
        reply = ""
        faq_dict = self._faq_fa if language == "fa" else self._faq_en
        for key, val in faq_dict.items():
            if key in query_lower:
                reply = val
                break

        if not reply:
            if language == "fa":
                reply = "درخواست شما دریافت شد. مدل‌های هوش مصنوعی ترید‌یار در حال پایش مستمر رفتار بازار هستند."
            else:
                reply = "Your request was received. TradeYar AI models are continuously monitoring raw structural price changes."

        self.add_message(email, "AI", reply)
        return reply

    def escalate_thread(self, email: str) -> None:
        """Escalates user conversation thread directly to platform administrators."""
        email_clean = email.strip().lower()
        self._escalated[email_clean] = True
        self.add_message(email_clean, "SYSTEM", "[ESCALATED_TO_ADMIN] Support agent notified.")

    def is_escalated(self, email: str) -> bool:
        """Checks if a user thread is escalated."""
        email_clean = email.strip().lower()
        return self._escalated.get(email_clean, False)
