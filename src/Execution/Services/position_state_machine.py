import logging
from enum import Enum
from typing import Dict, Any, Optional
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("PositionStateMachine")


class PositionState(Enum):
    CREATED = "CREATED"
    OPEN = "OPEN"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"
    RECONCILED = "RECONCILED"
    LEARNED = "LEARNED"


class PositionStateMachine:
    """
    Manages strict position state transitions without skipping lifecycle phases.
    Transitions: CREATED -> OPEN -> MONITORING -> CLOSED -> RECONCILED -> LEARNED
    """

    ALLOWED_TRANSITIONS = {
        PositionState.CREATED: [PositionState.OPEN, PositionState.CLOSED],  # CLOSED on instant reject
        PositionState.OPEN: [PositionState.MONITORING, PositionState.CLOSED],
        PositionState.MONITORING: [PositionState.CLOSED],
        PositionState.CLOSED: [PositionState.RECONCILED],
        PositionState.RECONCILED: [PositionState.LEARNED],
        PositionState.LEARNED: []  # Terminal state
    }

    def __init__(self, position_id: str, symbol: str):
        self.position_id = position_id
        self.symbol = symbol
        self.current_state = PositionState.CREATED
        self.history = [PositionState.CREATED.value]

    def transition_to(self, new_state: PositionState, context: Optional[Dict[str, Any]] = None) -> PositionState:
        allowed = self.ALLOWED_TRANSITIONS.get(self.current_state, [])
        if new_state not in allowed:
            err_msg = (
                f"SRE Position Lifecycle Violation: Invalid transition for position {self.position_id} "
                f"from '{self.current_state.value}' to '{new_state.value}'. Allowed: {[s.value for s in allowed]}"
            )
            logger.error(err_msg)
            raise ValidationException(err_msg)

        logger.info(
            f"[POSITION_STATE] Position {self.position_id} ({self.symbol}): "
            f"{self.current_state.value} -> {new_state.value}"
        )
        self.current_state = new_state
        self.history.append(new_state.value)
        return self.current_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "current_state": self.current_state.value,
            "history": self.history
        }
