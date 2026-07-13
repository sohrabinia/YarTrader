import unittest
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent,
    BaseAgent
)
from src.Application.Agents.context import AgentContextBuilder
from src.Application.Agents.communication import IntelligenceMessage


class BadAgent(BaseAgent):
    """An agent designed to fail during processing."""
    def __init__(self) -> None:
        super().__init__("agent-research", "Failing Research Agent", "Fails always")

    def process(self, context: Any, message: Any) -> Any:
        raise RuntimeError("Simulated agent process crash!")


class SlowAgent(BaseAgent):
    """An agent designed to exceed timeout limits."""
    def __init__(self) -> None:
        super().__init__("agent-strategy", "Slow Strategy Agent", "Sleeps on the job")

    def process(self, context: Any, message: Any) -> Any:
        time.sleep(0.15)  # Sleep briefly to simulate slow work
        return IntelligenceMessage(
            message_id="msg-slow",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="StrategyEvaluation",
            payload={"score": {"OverallScore": 0.5}}
        )


class TestIntelligenceSupervisor(unittest.TestCase):
    """
    Comprehensive tests for IntelligenceSupervisor verifying lifecycle,
    registration, execution ordering, timeout handling, and failure safety.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.context = AgentContextBuilder.create_with_market_data("EURUSD", "M15")

    def test_agent_registration_and_discovery(self) -> None:
        """Test registration, discovery, and list functionalities."""
        agent = ResearchAgent()
        self.supervisor.register_agent(agent)

        discovered = self.supervisor.get_agent(agent.agent_id)
        self.assertEqual(discovered, agent)
        self.assertEqual(self.supervisor.get_agent_status(agent.agent_id), "ACTIVE")

        agents_list = self.supervisor.list_agents()
        self.assertIn(agent, agents_list)

    def test_execution_ordering_and_complete_pipeline(self) -> None:
        """Test: Orchestration runs in correct order and enriches context successfully."""
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())

        final_context = self.supervisor.orchestrate(self.context)

        # Context version should have advanced 5 times (initial 1 + 5 agents = 6)
        self.assertEqual(final_context.version, 6)

        # Check all agent reports exist in final context payload
        self.assertIn("ResearchReport", final_context.data)
        self.assertIn("StrategyEvaluation", final_context.data)
        self.assertIn("RiskAssessment", final_context.data)
        self.assertIn("ComplianceAudit", final_context.data)
        self.assertIn("LearningFeedback", final_context.data)

    def test_agent_failure_handling(self) -> None:
        """Test: When an agent crashes, supervisor logs it and pipeline continues safely."""
        # Register standard agents except ResearchAgent is a failing one
        self.supervisor.register_agent(BadAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())

        final_context = self.supervisor.orchestrate(self.context)

        # Check failing agent status
        self.assertEqual(self.supervisor.get_agent_status("agent-research"), "FAILED")

        # The failing agent report should be missing from the data
        self.assertNotIn("ResearchReport", final_context.data)

        # But supervisor recorded the failure
        self.assertIn("error_agent-research", final_context.data)
        err_details = final_context.data["error_agent-research"]
        self.assertEqual(err_details["error_type"], "Failure")
        self.assertIn("Simulated agent process crash!", err_details["details"])

        # Strategy Analyst still executed successfully
        self.assertIn("StrategyEvaluation", final_context.data)
        self.assertEqual(self.supervisor.get_agent_status("agent-strategy"), "ACTIVE")

    def test_agent_timeout_handling(self) -> None:
        """Test: When an agent times out, supervisor records the state and degrades gracefully."""
        self.supervisor.register_agent(ResearchAgent())
        # Slow strategy agent with very low timeout limit (0.05 seconds)
        self.supervisor.register_agent(SlowAgent(), timeout_seconds=0.05)

        final_context = self.supervisor.orchestrate(self.context)

        # Check slow agent status
        self.assertEqual(self.supervisor.get_agent_status("agent-strategy"), "TIMED_OUT")

        # The strategy report should be missing
        self.assertNotIn("StrategyEvaluation", final_context.data)

        # Timeout recorded
        self.assertIn("error_agent-strategy", final_context.data)
        self.assertEqual(final_context.data["error_agent-strategy"]["error_type"], "Timeout")

        # Research agent still ran successfully
        self.assertIn("ResearchReport", final_context.data)
