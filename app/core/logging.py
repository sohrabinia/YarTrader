import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timezone
from typing import Any, Dict

try:
    from src.Application.Deployment.storage import YarTraderStorageManager
    LOGS_ROOT = YarTraderStorageManager.get_manager().get_log_dir()
except Exception:
    LOGS_ROOT = "logs"

os.makedirs(os.path.join(LOGS_ROOT, "application"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "error"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "audit"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "intelligence"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "security"), exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom formatter to format log records into structured JSON."""
    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
        'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
        'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName',
        'process', 'message'
    }

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": "YarTrader",
            "event": record.getMessage()
        }

        # Add custom extra fields from the LogRecord dict
        for key, val in record.__dict__.items():
            if key not in self.STANDARD_ATTRS and not key.startswith('_'):
                log_data[key] = val

        # Handle exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# Configure central logger
logger = logging.getLogger("YarTrader")
logger.setLevel(logging.DEBUG)
logger.propagate = False

# Backward compatibility alias
logging.getLogger("TradeYar-AI").handlers = logger.handlers

if logger.handlers:
    logger.handlers.clear()

class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that gracefully handles Windows file lock PermissionError during log rotation."""
    def doRollover(self):
        try:
            super().doRollover()
        except (PermissionError, OSError):
            if self.stream is None or self.stream.closed:
                self.stream = self._open()


# 1. Application Handler
app_handler = SafeTimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "application", "application.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
app_handler.setLevel(logging.INFO)
app_handler.setFormatter(JSONFormatter())
logger.addHandler(app_handler)

# 2. Error Handler
err_handler = SafeTimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "error", "error.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
err_handler.setLevel(logging.ERROR)
err_handler.setFormatter(JSONFormatter())
logger.addHandler(err_handler)


# 3. Special Logger for Audit Events
audit_logger = logging.getLogger("YarTrader.Audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False
if audit_logger.handlers:
    audit_logger.handlers.clear()

audit_handler = SafeTimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "audit", "audit.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
audit_handler.setFormatter(JSONFormatter())
audit_logger.addHandler(audit_handler)


# 4. Special Logger for Intelligence Decisions
intelligence_logger = logging.getLogger("YarTrader.Intelligence")
intelligence_logger.setLevel(logging.INFO)
intelligence_logger.propagate = False
if intelligence_logger.handlers:
    intelligence_logger.handlers.clear()

intel_handler = SafeTimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "intelligence", "intelligence.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
intel_handler.setFormatter(JSONFormatter())
intelligence_logger.addHandler(intel_handler)


# 5. Special Logger for Security Events
security_logger = logging.getLogger("YarTrader.Security")
security_logger.setLevel(logging.INFO)
security_logger.propagate = False
if security_logger.handlers:
    security_logger.handlers.clear()

security_handler = SafeTimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "security", "security.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
security_handler.setFormatter(JSONFormatter())
security_logger.addHandler(security_handler)


def _safe_extra(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    reserved = {
        "name", "msg", "args", "levelname", "levelno",
        "pathname", "filename", "module", "exc_info",
        "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread",
        "threadName", "processName", "process", "message"
    }

    sensitive_keys = {
        "password", "password_hash", "token", "secret", "key", "credentials", "private_key", "api_key", "auth", "session"
    }

    def redact_val(k: str, v: Any) -> Any:
        kl = str(k).lower()
        for sk in sensitive_keys:
            if sk in kl:
                return "[REDACTED]"
        if isinstance(v, dict):
            return {nk: redact_val(nk, nv) for nk, nv in v.items()}
        if isinstance(v, list):
            return [redact_val(str(i), nv) for i, nv in enumerate(v)]
        return v

    return {
        key: redact_val(key, value)
        for key, value in kwargs.items()
        if key not in reserved
    }


def log_event(level: str, event: str, **kwargs: Any) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, event, extra=_safe_extra(kwargs))


def log_audit(event: str, **kwargs: Any) -> None:
    audit_logger.info(event, extra=_safe_extra(kwargs))


def log_intelligence_decision(event: str, **kwargs: Any) -> None:
    intelligence_logger.info(event, extra=_safe_extra(kwargs))


def log_security(event: str, **kwargs: Any) -> None:
    security_logger.info(event, extra=_safe_extra(kwargs))
