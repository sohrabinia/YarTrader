import os
import json
import uuid
import threading
from datetime import datetime
from typing import Any, Dict, Optional, List
from src.Application.Deployment.storage import TradeYarStorageManager

_correlation_context = threading.local()


def get_correlation_id() -> str:
    """Retrieves the active correlation ID or initializes a new one for the current thread context."""
    if not getattr(_correlation_context, "correlation_id", None):
        _correlation_context.correlation_id = str(uuid.uuid4())
    return _correlation_context.correlation_id


def set_correlation_id(cid: str) -> None:
    """Sets a specific correlation ID for the current thread context."""
    _correlation_context.correlation_id = cid


def clear_correlation_id() -> None:
    """Clears the correlation ID for the current thread context."""
    if hasattr(_correlation_context, "correlation_id"):
        delattr(_correlation_context, "correlation_id")


class StructuredLogger:
    """Structured JSON Logger incorporating log levels and thread-local Correlation IDs."""

    def __init__(self, service_name: str = "RG_V3_AI") -> None:
        self.service_name = service_name
        self._storage_manager = TradeYarStorageManager.get_manager()
        self._log_file_path = os.path.join(self._storage_manager.get_log_dir(), "tradeyar_ai_observability.log")
        self._logs: List[str] = []

    def log(self, level: str, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        record = {
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
            "level": level.upper(),
            "event": event,
            "correlation_id": get_correlation_id(),
            "metadata": metadata or {}
        }
        json_str = json.dumps(record)
        self._logs.append(json_str)

        try:
            os.makedirs(os.path.dirname(self._log_file_path), exist_ok=True)
            with open(self._log_file_path, "a", encoding="utf-8") as f:
                f.write(json_str + "\n")
        except Exception:
            pass

        return json_str

    def debug(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("DEBUG", event, metadata)

    def info(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("INFO", event, metadata)

    def warning(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("WARNING", event, metadata)

    def error(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("ERROR", event, metadata)

    def get_logs(self) -> List[str]:
        return self._logs

    def clear(self) -> None:
        self._logs.clear()
