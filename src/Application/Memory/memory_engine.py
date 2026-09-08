from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class MemoryRecord:
    """
    Immutable domain representation of a single historical knowledge record.
    Stores facts produced by historical Learning (Phase 11).
    Zero AI, zero LLM, zero vector embeddings.
    """
    id: str
    timestamp: datetime
    symbol: str
    interval: str
    strategy_type: str
    observation_type: str
    metrics: Dict[str, Any]
    confidence: float
    source_phase: str = "PHASE_11_LEARNING"

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationException("MemoryRecord id must be a non-empty string.")
        if not isinstance(self.timestamp, datetime):
            raise ValidationException("MemoryRecord timestamp must be a valid datetime instance.")
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo != timezone.utc:
            raise ValidationException("MemoryRecord timestamp must be in UTC timezone.")
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValidationException("MemoryRecord symbol must be a non-empty string.")
        if not self.interval or not isinstance(self.interval, str):
            raise ValidationException("MemoryRecord interval must be a non-empty string.")
        if not self.strategy_type or not isinstance(self.strategy_type, str):
            raise ValidationException("MemoryRecord strategy_type must be a non-empty string.")
        if not self.observation_type or not isinstance(self.observation_type, str):
            raise ValidationException("MemoryRecord observation_type must be a non-empty string.")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValidationException("MemoryRecord confidence must be a float between 0.0 and 1.0.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "observation_type": self.observation_type,
            "metrics": self.metrics,
            "confidence": self.confidence,
            "source_phase": self.source_phase
        }


class MemoryStore:
    """
    Deterministic in-memory storage for structured MemoryRecord instances.
    Provides filtering by symbol, strategy, and date range.
    No database, no vector search, no AI agent state.
    """
    def __init__(self) -> None:
        self._records: List[MemoryRecord] = []

    def clear(self) -> None:
        self._records.clear()

    def add_record(self, record: MemoryRecord) -> None:
        if not record:
            raise ValidationException("Cannot add None as MemoryRecord.")
        record.validate()
        # Prevent exact duplicate IDs
        if any(r.id == record.id for r in self._records):
            return
        self._records.append(record)

    def get_records(
        self,
        symbol: Optional[str] = None,
        strategy_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MemoryRecord]:
        filtered = list(self._records)

        if symbol:
            sym_clean = symbol.strip().upper()
            filtered = [r for r in filtered if r.symbol.upper() == sym_clean]

        if strategy_type:
            strat_clean = strategy_type.strip().upper()
            filtered = [r for r in filtered if r.strategy_type.upper() == strat_clean]

        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            filtered = [r for r in filtered if r.timestamp >= start_time]

        if end_time:
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Always return sorted chronologically by timestamp
        filtered.sort(key=lambda r: r.timestamp)
        return filtered

    def count(self) -> int:
        return len(self._records)
