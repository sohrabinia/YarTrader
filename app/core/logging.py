import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Any, Dict

LOGS_ROOT = "logs"
try:
    os.makedirs(os.path.join(LOGS_ROOT, "application"), exist_ok=True)
    os.makedirs(os.path.join(LOGS_ROOT, "error"), exist_ok=True)
    os.makedirs(os.path.join(LOGS_ROOT, "audit"), exist_ok=True)
    os.makedirs(os.path.join(LOGS_ROOT, "intelligence"), exist_ok=True)
    os.makedirs(os.path.join(LOGS_ROOT, "security"), exist_ok=True)
    CAN_WRITE_FILES = True
except Exception:
    CAN_WRITE_FILES = False


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
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "TradeYar-AI",
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
logger = logging.getLogger("TradeYar-AI")
logger.setLevel(logging.DEBUG)
logger.propagate = False

if logger.handlers:
    logger.handlers.clear()

if CAN_WRITE_FILES:
    # 1. Application Handler
    try:
        app_handler = TimedRotatingFileHandler(
            filename=os.path.join(LOGS_ROOT, "application", "application.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(JSONFormatter())
        logger.addHandler(app_handler)
    except Exception:
        pass

    # 2. Error Handler
    try:
        err_handler = TimedRotatingFileHandler(
            filename=os.path.join(LOGS_ROOT, "error", "error.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(JSONFormatter())
        logger.addHandler(err_handler)
    except Exception:
        pass
else:
    # Graceful fallback to stdout stream logging under serverless/read-only envs
    try:
        fallback_handler = logging.StreamHandler()
        fallback_handler.setLevel(logging.INFO)
        fallback_handler.setFormatter(JSONFormatter())
        logger.addHandler(fallback_handler)
    except Exception:
        pass


# 3. Special Logger for Audit Events
audit_logger = logging.getLogger("TradeYar-AI.Audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False
if audit_logger.handlers:
    audit_logger.handlers.clear()

if CAN_WRITE_FILES:
    try:
        audit_handler = TimedRotatingFileHandler(
            filename=os.path.join(LOGS_ROOT, "audit", "audit.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        audit_handler.setFormatter(JSONFormatter())
        audit_logger.addHandler(audit_handler)
    except Exception:
        pass
else:
    try:
        fallback_audit = logging.StreamHandler()
        fallback_audit.setFormatter(JSONFormatter())
        audit_logger.addHandler(fallback_audit)
    except Exception:
        pass


# 4. Special Logger for Intelligence Decisions
intelligence_logger = logging.getLogger("TradeYar-AI.Intelligence")
intelligence_logger.setLevel(logging.INFO)
intelligence_logger.propagate = False
if intelligence_logger.handlers:
    intelligence_logger.handlers.clear()

if CAN_WRITE_FILES:
    try:
        intel_handler = TimedRotatingFileHandler(
            filename=os.path.join(LOGS_ROOT, "intelligence", "intelligence.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        intel_handler.setFormatter(JSONFormatter())
        intelligence_logger.addHandler(intel_handler)
    except Exception:
        pass
else:
    try:
        fallback_intel = logging.StreamHandler()
        fallback_intel.setFormatter(JSONFormatter())
        intelligence_logger.addHandler(fallback_intel)
    except Exception:
        pass


# 5. Special Logger for Security Events
security_logger = logging.getLogger("TradeYar-AI.Security")
security_logger.setLevel(logging.INFO)
security_logger.propagate = False
if security_logger.handlers:
    security_logger.handlers.clear()

if CAN_WRITE_FILES:
    try:
        security_handler = TimedRotatingFileHandler(
            filename=os.path.join(LOGS_ROOT, "security", "security.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        security_handler.setFormatter(JSONFormatter())
        security_logger.addHandler(security_handler)
    except Exception:
        pass
else:
    try:
        fallback_security = logging.StreamHandler()
        fallback_security.setFormatter(JSONFormatter())
        security_logger.addHandler(fallback_security)
    except Exception:
        pass


def log_event(level: str, event: str, **kwargs: Any) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, event, extra=kwargs)

def log_audit(event: str, **kwargs: Any) -> None:
    audit_logger.info(event, extra=kwargs)

def log_intelligence_decision(event: str, **kwargs: Any) -> None:
    intelligence_logger.info(event, extra=kwargs)

def log_security(event: str, **kwargs: Any) -> None:
    security_logger.info(event, extra=kwargs)
