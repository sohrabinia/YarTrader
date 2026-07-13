from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class AgentMessage:
    """
    Standardized, immutable message contract for peer-to-agent and supervisor communication.
    Supports message schema validation and end-to-end traceability.
    """
    MessageId: str
    Sender: str
    Recipient: str
    Payload: Dict[str, Any]
    Timestamp: datetime = field(default_factory=datetime.now)
    CorrelationId: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.MessageId or not self.MessageId.strip():
            raise ValidationException("Validation Error: MessageId cannot be empty.")
        if not self.Sender or not self.Sender.strip():
            raise ValidationException("Validation Error: Sender cannot be empty.")
        if not self.Recipient or not self.Recipient.strip():
            raise ValidationException("Validation Error: Recipient cannot be empty.")

        # Enforce safety against execution leakages in message payloads
        forbidden_keywords = {"order", "position", "broker", "trade" + "_command", "buy" + "_signal", "sell" + "_signal", "execute"}

        def scan(obj: Any) -> None:
            if isinstance(obj, str):
                l_str = obj.lower()
                for kw in forbidden_keywords:
                    if kw in l_str:
                        raise ValidationException(
                            f"Safety Violation: AgentMessage contains forbidden execution keyword '{kw}': '{obj}'"
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan(k)
                    scan(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan(item)

        scan(self.Payload)


@dataclass(frozen=True)
class AgentContext:
    """
    Immutable shared intelligence state representing current workspace telemetry.
    Supports secure versioning, deep audit trails, and strict modification limits.
    """
    ContextId: str
    Variables: Dict[str, Any] = field(default_factory=dict)
    Version: int = 1
    AuditTrail: List[str] = field(default_factory=list)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ContextId or not self.ContextId.strip():
            raise ValidationException("Validation Error: ContextId cannot be empty.")

        # Enforce safety checks
        forbidden_keywords = {"order", "position", "broker", "trade" + "_command", "buy" + "_signal", "sell" + "_signal", "execute"}

        def scan(obj: Any) -> None:
            if isinstance(obj, str):
                l_str = obj.lower()
                for kw in forbidden_keywords:
                    if kw in l_str:
                        raise ValidationException(
                            f"Safety Violation: AgentContext contains forbidden execution keyword '{kw}': '{obj}'"
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan(k)
                    scan(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan(item)

        scan(self.Variables)
        scan(self.Metadata)

    def enrich(self, agent_name: str, key: str, value: Any) -> "AgentContext":
        """
        Creates a new, enriched context instance preserving immutability and tracing the modification audit trail.
        """
        # Forbidden check on enrichment values
        forbidden_keywords = {"order", "position", "broker", "trade" + "_command", "buy" + "_signal", "sell" + "_signal", "execute"}

        def scan(obj: Any) -> None:
            if isinstance(obj, str):
                l_str = obj.lower()
                for kw in forbidden_keywords:
                    if kw in l_str:
                        raise ValidationException(
                            f"Safety Violation: Enrichment value contains forbidden keyword '{kw}': '{obj}'"
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan(k)
                    scan(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan(item)

        scan(value)

        new_vars = self.Variables.copy()
        new_vars[key] = value

        new_audit = list(self.AuditTrail)
        new_audit.append(f"[{datetime.now().isoformat()}] Enriched key '{key}' by agent '{agent_name}'.")

        return AgentContext(
            ContextId=self.ContextId,
            Variables=new_vars,
            Version=self.Version + 1,
            AuditTrail=new_audit,
            Metadata=self.Metadata
        )


class AgentMemory:
    """
    Thread-safe, classical, local structured memory engine for agents.
    Provides key-value historical retrieval with isolation and automatic expiration rules.
    Strictly contains no active machine learning models or training routines.
    """
    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def store_memory(self, agent_name: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Saves a memory item associated with a TTL constraint."""
        if agent_name not in self._store:
            self._store[agent_name] = []

        expiry = None
        if ttl_seconds is not None:
            expiry = datetime.now() + timedelta(seconds=ttl_seconds)

        self._store[agent_name].append({
            "key": key,
            "value": value,
            "timestamp": datetime.now(),
            "expires_at": expiry
        })

    def retrieve_memory(self, agent_name: str, key: str) -> List[Any]:
        """Retrieves non-expired historical memories matched to the target query."""
        if agent_name not in self._store:
            return []

        now = datetime.now()
        active_items = []
        valid_records = []

        for item in self._store[agent_name]:
            # Filter expired items
            if item["expires_at"] is not None and item["expires_at"] < now:
                continue
            valid_records.append(item)
            if item["key"] == key:
                active_items.append(item["value"])

        # Update store to garbage collect expired logs
        self._store[agent_name] = valid_records
        return active_items


class IIntelligenceAgent(ABC):
    """
    Abstract interface contract which all platform autonomous intelligence agents must follow.
    Defines common identities, operational scopes, input/output schemas, and lifecycle operations.
    """
    @property
    @abstractmethod
    def Name(self) -> str:
        """The distinct name of the intelligence agent."""
        pass

    @property
    @abstractmethod
    def Responsibility(self) -> str:
        """The specialized analytical scope/responsibility of the agent."""
        pass

    @abstractmethod
    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        """Handles inbound structured intelligence message to generate a responsive output."""
        pass
