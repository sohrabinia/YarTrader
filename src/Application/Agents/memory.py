from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass
class MemoryEntry:
    """A structured intelligence memory record."""
    key: str
    value: Any
    timestamp: datetime
    ttl: Optional[timedelta] = None
    tags: List[str] = field(default_factory=list)


class AgentMemory:
    """
    Structured in-memory repository for storing and retrieving Agent historical insights.
    Integrates memory isolation per agent/namespace and TTL / FIFO expiration rules.
    Does not use any machine learning or external database storage.
    """
    def __init__(self, max_size: int = 100) -> None:
        self._max_size = max_size
        self._store: Dict[str, List[MemoryEntry]] = {}  # Namespace -> List[MemoryEntry]

    def store(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """Stores an entry under a given agent/namespace."""
        if not namespace:
            raise ValidationException("Memory Error: Namespace cannot be empty.")
        if not key:
            raise ValidationException("Memory Error: Key cannot be empty.")

        # Evict expired entries before adding new ones
        self.cleanup_expired(namespace)

        if namespace not in self._store:
            self._store[namespace] = []

        # FIFO Limit enforcement
        entries = self._store[namespace]
        if len(entries) >= self._max_size:
            entries.pop(0)  # Evict oldest entry

        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            ttl=ttl,
            tags=tags or []
        )
        entries.append(entry)

    def retrieve(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieves a non-expired memory value by namespace and key."""
        self.cleanup_expired(namespace)
        if namespace not in self._store:
            return None

        for entry in self._store[namespace]:
            if entry.key == key:
                return entry.value
        return None

    def query_by_tags(self, namespace: str, tags: List[str]) -> List[Any]:
        """Returns all values matching a list of tags under a namespace."""
        self.cleanup_expired(namespace)
        if namespace not in self._store:
            return []

        results = []
        target_set = set(tags)
        for entry in self._store[namespace]:
            if target_set.intersection(entry.tags):
                results.append(entry.value)
        return results

    def get_all_namespace_memory(self, namespace: str) -> List[Dict[str, Any]]:
        """Returns all current memory entries for a namespace."""
        self.cleanup_expired(namespace)
        if namespace not in self._store:
            return []
        return [{"key": e.key, "value": e.value, "timestamp": e.timestamp} for e in self._store[namespace]]

    def cleanup_expired(self, namespace: str) -> None:
        """Prunes expired TTL entries for a given namespace."""
        if namespace not in self._store:
            return

        now = datetime.now()
        non_expired = []
        for entry in self._store[namespace]:
            if entry.ttl is not None:
                if now - entry.timestamp > entry.ttl:
                    continue  # Expired
            non_expired.append(entry)
        self._store[namespace] = non_expired

    def clear(self) -> None:
        """Clears all stored agent memories."""
        self._store.clear()
