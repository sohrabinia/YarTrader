import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Agents.interfaces import IIntelligenceAgent
from src.Application.Agents.context import AgentContext
from src.Application.Agents.communication import IntelligenceMessage
from src.Application.Knowledge.knowledge import IntelligenceKnowledgeBase
from src.Infrastructure.exceptions import ValidationException


class ConversationalSupportAgent(IIntelligenceAgent):
    """
    Human-like Conversational Support Agent.
    Provides natural multi-turn chat assistance, MT5 troubleshooting, subscription guidance,
    and ticket escalation across 5 locales (fa, en, tr, ar, de).
    """

    def __init__(
        self,
        agent_id: str = "agent-support",
        knowledge_base: Optional[IntelligenceKnowledgeBase] = None
    ) -> None:
        self._agent_id = agent_id
        self._name = "Conversational Support Agent"
        self._responsibility = "Provides natural human-like customer support, troubleshooting, and ticket escalation."
        self._domain = "Customer Support"
        self._version = "1.0.0"
        self._autonomy_level = "L3"
        self._lifecycle_status = "IMPLEMENTED"
        self.knowledge_base = knowledge_base or IntelligenceKnowledgeBase()
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> message history

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def responsibility(self) -> str:
        return self._responsibility

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def version(self) -> str:
        return self._version

    @property
    def autonomy_level(self) -> str:
        return self._autonomy_level

    @property
    def lifecycle_status(self) -> str:
        return self._lifecycle_status

    def _detect_intent(self, user_message: str) -> str:
        msg_lower = user_message.lower()
        if "mt5" in msg_lower or "metatrader" in msg_lower or "connect" in msg_lower or "terminal" in msg_lower:
            return "MT5_TROUBLESHOOTING"
        elif "price" in msg_lower or "plan" in msg_lower or "subscription" in msg_lower or "billing" in msg_lower or "wallet" in msg_lower:
            return "SUBSCRIPTION_BILLING"
        elif "risk" in msg_lower or "trade" in msg_lower or "fractal" in msg_lower or "signal" in msg_lower:
            return "PLATFORM_FEATURES"
        elif "human" in msg_lower or "escalate" in msg_lower or "ticket" in msg_lower or "agent" in msg_lower:
            return "ESCALATE_HUMAN"
        else:
            return "GENERAL_INQUIRY"

    def chat(self, session_id: str, user_message: str, locale: str = "fa") -> Dict[str, Any]:
        """Multi-turn conversational handler with knowledge grounding and ticket escalation."""
        if not user_message or not user_message.strip():
            raise ValidationException("Support Error: User message cannot be empty.")

        msg_lower = user_message.lower()
        forbidden_patterns = [
            "secret_key", "private_key", "password_reset_override",
            "execute_order", "ignore previous instructions", "admin credentials"
        ]
        for forbidden_term in forbidden_patterns:
            if forbidden_term in msg_lower:
                raise ValidationException(f"Security Violation: Support Agent cannot process action '{forbidden_term}'.")

        if session_id not in self.conversations:
            self.conversations[session_id] = []

        history = self.conversations[session_id]
        history.append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

        intent = self._detect_intent(user_message)
        response_text = ""
        escalated = False
        ticket_id = None

        if intent == "MT5_TROUBLESHOOTING":
            if locale == "fa":
                response_text = "برای اتصال MT5، ابتدا بررسی کنید حساب DEMO شما فعال است و شماره سرور و پاسپورد را درست وارد کرده‌اید. همچنین مطمئن شوید گزینه Allow Automated Trading روشن باشد."
            else:
                response_text = "To connect MT5, ensure your DEMO account credentials and server name are accurate. Also verify 'Allow Algo Trading' is checked in MT5 options."
        elif intent == "SUBSCRIPTION_BILLING":
            if locale == "fa":
                response_text = "ما از پرداخت‌های ارز دیجیتال با کیف پول‌های تایید شده TRC20، ERC20، Solana و TON پشتیبانی می‌کنیم. می‌توانید پلن خود را در بخش Billing انتخاب کنید."
            else:
                response_text = "We support verified crypto payments on TRON TRC20, EVM ERC20, Solana SPL, and TON networks. Select your tier in the Billing section."
        elif intent == "PLATFORM_FEATURES":
            if locale == "fa":
                response_text = "سامانه YarTrader بر پایه ساختارهای فرکتالی چندزمانی و کنترل ریسک قطعی کار می‌کند. هیچ سیگنال ضمانتی صادر نمی‌شود و اولویت با مدیریت ریسک است."
            else:
                response_text = "YarTrader operates on multi-timeframe fractal structures and deterministic risk control. All decisions pass through strict risk gates."
        elif intent == "ESCALATE_HUMAN":
            escalated = True
            ticket_id = f"tkt-{uuid.uuid4().hex[:8]}"
            if locale == "fa":
                response_text = f"درخواست شما ثبت شد و تیکت پشتیبانی شماره {ticket_id} برای بررسی کارشناسان ایجاد گردید."
            else:
                response_text = f"Your request has been escalated to human support. Support Ticket ID: {ticket_id}."
        else:
            if locale == "fa":
                response_text = "سلام! من دستیار هوشمند YarTrader هستم. چگونه می‌توانم در خصوص اتصالات MT5، اشتراک‌ها یا قابلیت‌های پلتفرم به شما کمک کنم؟"
            else:
                response_text = "Hello! I am YarTrader's AI Support Assistant. How can I assist you today regarding MT5 setup, subscription billing, or platform features?"

        assistant_msg = {
            "role": "assistant",
            "content": response_text,
            "intent": intent,
            "escalated": escalated,
            "ticket_id": ticket_id,
            "timestamp": datetime.now().isoformat()
        }
        history.append(assistant_msg)

        return {
            "session_id": session_id,
            "reply": response_text,
            "intent": intent,
            "escalated": escalated,
            "ticket_id": ticket_id,
            "turn_count": len(history),
            "locale": locale
        }

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        user_msg = message.payload.get("user_message", "")
        session_id = message.payload.get("session_id", "default_session")
        locale = message.payload.get("locale", "fa")

        chat_res = self.chat(session_id=session_id, user_message=user_msg, locale=locale)

        return IntelligenceMessage(
            message_id=f"msg-supp-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="SupportResponse",
            payload=chat_res,
            trace_trail=list(message.trace_trail)
        )
