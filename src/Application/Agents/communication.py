import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class TraceRecord:
    """Trace trail entry tracking message flow."""
    agent_id: str
    timestamp: datetime
    action: str = "forward"


@dataclass(frozen=True)
class IntelligenceMessage:
    """
    Standardized, schema-validated message class for agent-to-agent and
    supervisor communication. Incorporates end-to-end traceability.
    """
    message_id: str
    sender_id: str
    recipient_id: str
    timestamp: datetime
    message_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    trace_trail: List[TraceRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Enforces schema validation and rejects invalid formats."""
        if not self.message_id or not isinstance(self.message_id, str):
            raise ValidationException("Message Validation Error: message_id must be a non-empty string.")
        if not self.sender_id or not isinstance(self.sender_id, str):
            raise ValidationException("Message Validation Error: sender_id must be a non-empty string.")
        if not self.recipient_id or not isinstance(self.recipient_id, str):
            raise ValidationException("Message Validation Error: recipient_id must be a non-empty string.")
        if not isinstance(self.timestamp, datetime):
            raise ValidationException("Message Validation Error: timestamp must be a valid datetime instance.")
        if not self.message_type or not isinstance(self.message_type, str):
            raise ValidationException("Message Validation Error: message_type must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise ValidationException("Message Validation Error: payload must be a dictionary.")

        # Forbidden keywords safety scan
        self._scan_object(self.payload)

    def _scan_object(self, obj: Any) -> None:
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}
        if isinstance(obj, str):
            lower_str = obj.lower()
            for keyword in forbidden_keywords:
                if keyword in lower_str:
                    raise ValidationException(
                        f"Safety Violation: IntelligenceMessage payload contains forbidden trading keyword '{keyword}'."
                    )
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._scan_object(k)
                self._scan_object(v)
        elif isinstance(obj, (list, set, tuple)):
            for item in obj:
                self._scan_object(item)

    def route_to(self, new_recipient: str, forwarding_agent: str) -> "IntelligenceMessage":
        """Routes message to a new agent, appending to trace_trail."""
        new_trace = TraceRecord(agent_id=forwarding_agent, timestamp=datetime.now(), action="forward")
        return IntelligenceMessage(
            message_id=self.message_id,
            sender_id=forwarding_agent,
            recipient_id=new_recipient,
            timestamp=datetime.now(),
            message_type=self.message_type,
            payload=copy.deepcopy(self.payload),
            trace_trail=self.trace_trail + [new_trace]
        )


class MessageRouter:
    """Manages routing of agent messages and enforces message de-duplication rules."""
    def __init__(self) -> None:
        self._seen_message_ids: Set[str] = set()

    def process_and_route(self, message: IntelligenceMessage, recipient_agent: Any) -> IntelligenceMessage:
        """Checks for duplicates, tracks history, and delivers the message."""
        if message.message_id in self._seen_message_ids:
            raise ValidationException(f"Message Rejection: Duplicate message detected for ID '{message.message_id}'.")

        self._seen_message_ids.add(message.message_id)
        # Verify recipient agent is active/valid
        if not hasattr(recipient_agent, "process"):
            raise ValidationException(f"Message Rejection: Recipient agent does not implement processing interface.")

        # Deep copy to maintain absolute isolation
        return message
