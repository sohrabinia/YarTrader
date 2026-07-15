import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Deployment.storage import TradeYarStorageManager
from src.Infrastructure.Observability.logging import get_correlation_id


class AuditTrailManager:
    """Manages secure, read-only system audit trails to log key pipeline events, state outcomes, and agent activity."""

    def __init__(self) -> None:
        self._storage_manager = TradeYarStorageManager.get_manager()
        self._audit_file_path = os.path.join(self._storage_manager.get_runtime_dir(), "audit_trail.jsonl")
        self._records: List[Dict[str, Any]] = []

    def record_event(self, action: str, actor: str, outcome: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = {
            "timestamp": datetime.now().isoformat(),
            "correlation_id": get_correlation_id(),
            "action": action,
            "actor": actor,
            "outcome": outcome,
            "details": details or {}
        }
        self._records.append(record)

        try:
            os.makedirs(os.path.dirname(self._audit_file_path), exist_ok=True)
            with open(self._audit_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        return record

    def get_records(self) -> List[Dict[str, Any]]:
        return self._records

    def clear(self) -> None:
        self._records.clear()
