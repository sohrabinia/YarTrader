from datetime import datetime
from src.Infrastructure.logging import get_production_logger

class AuditLogService:
    """
    Dedicated Audit and Activity Tracking Service for compliance and security forensics.
    Writes structured security events and user interactions to dedicated, production-grade files.
    """
    def __init__(self) -> None:
        self.security_logger = get_production_logger("security")
        self.user_logger = get_production_logger("user_activity")

    def log_security_event(self, email: str, action: str, status: str, details: str = "") -> None:
        """Logs security-critical actions (registration, login, authorization changes)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] [SECURITY_EVENT] User: {email} | Action: {action} | Status: {status} | Details: {details}"
        self.security_logger.info(msg)

    def log_user_activity(self, email: str, action: str, resource: str, details: str = "") -> None:
        """Logs standard user interactions (watching symbols, viewing analyses, upgrading plans)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] [USER_ACTIVITY] User: {email} | Action: {action} | Resource: {resource} | Details: {details}"
        self.user_logger.info(msg)
