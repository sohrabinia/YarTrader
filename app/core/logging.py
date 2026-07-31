import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Any, Dict

LOGS_ROOT = "logs"
os.makedirs(os.path.join(LOGS_ROOT, "application"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "error"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "audit"), exist_ok=True)
os.makedirs(os.path.join(LOGS_ROOT, "intelligence"), exist_ok=True)


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

# 1. Application Handler
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

# 2. Error Handler
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


# 3. Special Logger for Audit Events
audit_logger = logging.getLogger("TradeYar-AI.Audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False
if audit_logger.handlers:
    audit_logger.handlers.clear()

audit_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "audit", "audit.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
audit_handler.setFormatter(JSONFormatter())
audit_logger.addHandler(audit_handler)


# 4. Special Logger for Intelligence Decisions
intelligence_logger = logging.getLogger("TradeYar-AI.Intelligence")
intelligence_logger.setLevel(logging.INFO)
intelligence_logger.propagate = False
if intelligence_logger.handlers:
    intelligence_logger.handlers.clear()

intel_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOGS_ROOT, "intelligence", "intelligence.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
intel_handler.setFormatter(JSONFormatter())
intelligence_logger.addHandler(intel_handler)


def log_event(level: str, event: str, **kwargs: Any) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, event, extra=kwargs)

def log_audit(event: str, **kwargs: Any) -> None:
    audit_logger.info(event, extra=kwargs)

def log_intelligence_decision(event: str, **kwargs: Any) -> None:
    intelligence_logger.info(event, extra=kwargs)
