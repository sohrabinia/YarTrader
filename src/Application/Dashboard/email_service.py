import logging
from src.Infrastructure.logging import get_production_logger

class EmailService:
    """
    Production-grade simulated Transactional Email Service.
    Supports secure onboarding emails, password recovery templates, and subscription invoice billing.
    Enforces high-fidelity localization translation (FA/EN) on all templates.
    """
    def __init__(self) -> None:
        self.logger = get_production_logger("application")

    def send_welcome_email(self, email: str, language: str = "en") -> bool:
        """Sends a welcome and platform onboarding email to newly registered users."""
        if language == "fa":
            subject = "به ترید‌یار خوش آمدید!"
            body = f"سلام {email}، به سامانه هوشمند کشف بازار و مالی ترید‌یار خوش آمدید. حساب شما فعال است."
        else:
            subject = "Welcome to TradeYar AI!"
            body = f"Hello {email}, welcome to TradeYar AI Financial Intelligence. Your passive descriptive account is now active."

        # Simulate transmission by writing to production logger
        self.logger.info(f"[EMAIL_SENT] To: {email} | Subject: {subject} | Body: {body}")
        return True

    def send_password_recovery_email(self, email: str, code: str, language: str = "en") -> bool:
        """Sends a numeric 6-digit recovery code for password resets."""
        if language == "fa":
            subject = "بازیابی رمز عبور ترید‌یار"
            body = f"کد امنیتی یکبار مصرف بازیابی رمز عبور شما: {code} است. این کد پس از ۱۵ دقیقه منقضی می‌شود."
        else:
            subject = "TradeYar AI Password Recovery"
            body = f"Your one-time password recovery security code is: {code}. It expires in 15 minutes."

        self.logger.info(f"[EMAIL_SENT] To: {email} | Subject: {subject} | Body: {body}")
        return True

    def send_subscription_invoice(self, email: str, plan_name: str, amount: float, language: str = "en") -> bool:
        """Sends an active billing invoice for upgrading user plans."""
        if language == "fa":
            subject = "فاکتور خرید اشتراک ترید‌یار"
            body = f"پرداخت شما تایید شد! طرح {plan_name} با موفقیت فعال گردید. مبلغ: {amount} دلار."
        else:
            subject = "TradeYar AI Billing Invoice"
            body = f"Payment Approved! Your {plan_name} plan has been activated. Amount: ${amount}."

        self.logger.info(f"[EMAIL_SENT] To: {email} | Subject: {subject} | Body: {body}")
        return True
