import logging
from src.Infrastructure.logging import get_production_logger

class TelegramService:
    """
    Simulated Telegram Bot Service.
    Broadcasts daily reports, educational blog posts, and active in-app notifications
    directly to user channels under strict descriptive non-trading guidelines.
    """
    def __init__(self) -> None:
        self.logger = get_production_logger("application")

    def broadcast_market_update(self, symbol: str, direction: str, confidence: int, language: str = "en") -> bool:
        """Broadcasts passive market analysis snapshots to the public Telegram channel."""
        if language == "fa":
            msg = f"📣 [کانال ترید‌یار] تحلیل زنده نماد {symbol} H1\nجهت‌گیری: {direction}\nسطح اطمینان: {confidence}٪\n⚠️ هشدار: بازارهای مالی دارای ریسک نوسان هستند."
        else:
            msg = f"📣 [TradeYar Telegram Channel] Market Update: {symbol} H1\nDirection: {direction}\nConfidence: {confidence}%\n⚠️ Disclaimer: Speculative assets carry risk."

        self.logger.info(f"[TELEGRAM_BROADCAST] Message: {msg}")
        return True

    def send_account_alert(self, email: str, alert_text: str) -> bool:
        """Sends a secure, direct account notification alert to a user's Telegram handle."""
        msg = f"🔔 [TradeYar Direct Bot] To: {email} | Alert: {alert_text}"
        self.logger.info(f"[TELEGRAM_ALERT] Message: {msg}")
        return True

    def broadcast_educational_post(self, title: str, body: str) -> bool:
        """Broadcasts newly approved AI blog or reports to the community channel."""
        msg = f"📚 [TradeYar Academy] {title}\n\n{body}"
        self.logger.info(f"[TELEGRAM_EDUCATIONAL_BROADCAST] Message: {msg}")
        return True
