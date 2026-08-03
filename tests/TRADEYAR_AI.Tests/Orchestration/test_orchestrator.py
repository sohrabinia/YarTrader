import pytest
from src.Intelligence.Orchestration.orchestrator import AIAgentOrchestrator

def test_ai_agent_orchestrator_e2e():
    """Verifies AIAgentOrchestrator Registry, Planning, Routing and passive Execution."""
    orchestrator = AIAgentOrchestrator()

    # 1. Assert Registry possesses default specialized agents
    agents = orchestrator.registry.get_all_agents()
    assert len(agents) == 4
    assert any(a.agent_id == "agent-research" for a in agents)
    assert any(a.agent_id == "agent-risk" for a in agents)

    # 2. Assert Routing based on capabilities
    routed_id = orchestrator.router.route_task("extract_pattern")
    assert routed_id == "agent-research"

    # 3. Assert Planning & Passive Execution of Goals
    res_research = orchestrator.process_goal("research patterns on XAUUSD")
    assert res_research["is_read_only_advisory"] is True
    assert len(res_research["plan_steps"]) == 2
    assert res_research["plan_steps"][0]["agent_id"] == "agent-research"
    assert res_research["execution_results"][0]["status"] == "COMPLETED"

    res_risk = orchestrator.process_goal("check high drawdown risk limits")
    assert len(res_risk["plan_steps"]) == 1
    assert res_risk["plan_steps"][0]["agent_id"] == "agent-risk"
    assert res_risk["execution_results"][0]["status"] == "COMPLETED"
