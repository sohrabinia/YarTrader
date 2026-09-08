import logging
from typing import Dict, Any, Optional

from src.Application.Support.support_ai_engine import SupportAIEngine, SupportQuery, SupportResponse
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class SupportAIService:
    """
    Application Service orchestrating Support AI queries and explanations.
    Provides bounded, grounded answers without execution authority.
    """

    def __init__(self, support_engine: Optional[SupportAIEngine] = None) -> None:
        self.engine = support_engine or SupportAIEngine()

    def process_chat_message(
        self,
        message: str,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        lang: str = "fa",
        user_context: Optional[Dict[str, Any]] = None,
        foundation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes an incoming user support message, validates inputs, delegates to SupportAIEngine,
        and returns a standardized JSON dictionary matching the API contract.
        """
        if not message or not isinstance(message, str):
            raise ValidationException("Message must be a non-empty string.")

        query = SupportQuery(
            message=message.strip(),
            symbol=symbol or "XAUUSD",
            interval=interval or "M15",
            strategy=strategy or "TREND",
            lang=lang or "fa",
            user_context=user_context
        )

        response: SupportResponse = self.engine.generate_response(
            query=query,
            foundation_data=foundation_data
        )

        return response.to_dict()
