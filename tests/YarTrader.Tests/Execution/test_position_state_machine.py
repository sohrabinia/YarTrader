import pytest
from src.Execution.Services.position_state_machine import PositionStateMachine, PositionState
from src.Infrastructure.exceptions import ValidationException


def test_position_state_machine_valid_lifecycle():
    psm = PositionStateMachine(position_id="POS-101", symbol="BITCOIN")
    assert psm.current_state == PositionState.CREATED

    # Transitions
    psm.transition_to(PositionState.OPEN)
    assert psm.current_state == PositionState.OPEN

    psm.transition_to(PositionState.MONITORING)
    assert psm.current_state == PositionState.MONITORING

    psm.transition_to(PositionState.CLOSED)
    assert psm.current_state == PositionState.CLOSED

    psm.transition_to(PositionState.RECONCILED)
    assert psm.current_state == PositionState.RECONCILED

    psm.transition_to(PositionState.LEARNED)
    assert psm.current_state == PositionState.LEARNED

    assert psm.history == ["CREATED", "OPEN", "MONITORING", "CLOSED", "RECONCILED", "LEARNED"]


def test_position_state_machine_invalid_jump_fails_closed():
    psm = PositionStateMachine(position_id="POS-202", symbol="EURUSD")

    # Invalid jump from CREATED directly to RECONCILED
    with pytest.raises(ValidationException) as exc_info:
        psm.transition_to(PositionState.RECONCILED)

    assert "SRE Position Lifecycle Violation" in str(exc_info.value)
