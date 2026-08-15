import pytest
from src.Intelligence.SDDL.sddl import SDDLOrchestrator

def test_sddl_unauthorized_fails():
    """Verifies that SDDLOrchestrator rejects autonomous executions with PermissionError."""
    orchestrator = SDDLOrchestrator()

    with pytest.raises(PermissionError) as exc_info:
        # Attempt execution without approval flags
        orchestrator.run_sddl_cycle("Decompose patterns on XAUUSD", is_human_approved=False)

    assert "blocked" in str(exc_info.value)
    assert "human approval" in str(exc_info.value)


def test_sddl_authorized_succeeds():
    """Verifies that SDDLOrchestrator executes successfully when explicit human approval is provided."""
    orchestrator = SDDLOrchestrator()

    record = orchestrator.run_sddl_cycle(
        high_level_goal="Analyze patterns and check memory leaks",
        human_approval_signature="operator-signature-jwt-v3",
        is_human_approved=True
    )

    # Assert correct execution
    assert record["goal"] == "Analyze patterns and check memory leaks"
    assert record["authorized_by"] == "operator-signature-jwt-v3"
    assert record["is_read_only_compliance"] is True

    # Assert correct decomposition and trace
    assert len(record["decomposed_subtasks"]) == 3
    assert record["decomposed_subtasks"][0]["agent"] == "agent-research"
    assert record["execution_trace"][0]["status"] == "COMPLETED"
    assert record["sandbox_evaluation"]["quality_score"] == 1.0
