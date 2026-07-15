import uuid
import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class ContextAuditRecord:
    """Audit log entry for tracking updates to AgentContext."""
    agent_id: str
    action: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentContext:
    """
    Shared, immutable, and versioned intelligence context passed between agents.
    Provides strict boundary safety and detailed auditing of all context modifications.
    """
    context_id: str
    version: int = 1
    data: Dict[str, Any] = field(default_factory=dict)
    audit_trail: List[ContextAuditRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Prevent initial safety leakages
        self._scan_object(self.data)

    def enrich(self, agent_id: str, key: str, value: Any, action: str = "enrich") -> "AgentContext":
        """
        Enriches context by returning a copy-on-write updated AgentContext instance.
        Maintains structural immutability of past context versions.
        """
        self._scan_object(key)
        self._scan_object(value)

        # Copy-on-write to maintain absolute immutability of other contexts with maximum performance
        new_data = dict(self.data)
        new_data[key] = copy.deepcopy(value)

        new_record = ContextAuditRecord(
            agent_id=agent_id,
            action=action,
            timestamp=datetime.now(),
            details={"key": key, "type": str(type(value))}
        )
        new_audit = list(self.audit_trail) + [new_record]

        return AgentContext(
            context_id=self.context_id,
            version=self.version + 1,
            data=new_data,
            audit_trail=new_audit
        )

    def _scan_object(self, obj: Any) -> None:
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}
        if isinstance(obj, str):
            lower_str = obj.lower()
            for keyword in forbidden_keywords:
                if keyword in lower_str:
                    raise ValidationException(
                        f"Safety Violation: AgentContext contains forbidden execution-related keyword '{keyword}' in data: '{obj}'."
                    )
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._scan_object(k)
                self._scan_object(v)
        elif isinstance(obj, (list, set, tuple)):
            for item in obj:
                self._scan_object(item)
        elif hasattr(obj, "__dict__"):
            self._scan_object(obj.__dict__)


class AgentContextBuilder:
    """Builder service for constructing standardized AgentContexts."""
    @staticmethod
    def create_empty(context_id: Optional[str] = None) -> AgentContext:
        """Creates a completely blank, tracked AgentContext."""
        return AgentContext(
            context_id=context_id or str(uuid.uuid4()),
            version=1,
            data={},
            audit_trail=[]
        )

    @staticmethod
    def create_with_market_data(asset: str, timeframe: str, context_id: Optional[str] = None) -> AgentContext:
        """Initializes a context with foundational market identifiers."""
        return AgentContext(
            context_id=context_id or str(uuid.uuid4()),
            version=1,
            data={"asset": asset, "timeframe": timeframe},
            audit_trail=[
                ContextAuditRecord(
                    agent_id="system",
                    action="initialize",
                    timestamp=datetime.now(),
                    details={"asset": asset, "timeframe": timeframe}
                )
            ]
        )
