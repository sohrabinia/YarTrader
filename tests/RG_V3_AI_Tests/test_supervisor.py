import unittest
from datetime import datetime
from src.Infrastructure.exceptions import ValidationException
from src.Decision.Intelligence.Agents.models import AgentMessage, AgentContext
from src.Decision.Intelligence.Agents.agents import ResearchAgent, RiskAgent
from src.Decision.Intelligence.Agents.services import IntelligenceSupervisor

class TestIntelligenceSupervisor(unittest.TestCase):
    """
    Validates supervisor registration, discovery, lifecycle, order, failure,
    timeouts, and active safety isolation.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.research = ResearchAgent()
        self.risk = RiskAgent()
        self.now = datetime.now()

    def test_agent_registration_and_discovery(self) -> None:
        """Test registration, discovery, and double registration limits."""
        self.assertEqual(len(self.supervisor.list_registered_agents()), 0)

        # Successful registration
        self.supervisor.register_agent(self.research)
        self.assertEqual(len(self.supervisor.list_registered_agents()), 1)
        self.assertIn("ResearchAgent", self.supervisor.list_registered_agents())

        # Duplicate registration failure
        with self.assertRaises(ValidationException) as ex:
            self.supervisor.register_agent(self.research)
        self.assertIn("is already registered", str(ex.exception))

        # Discovery
        discovered = self.supervisor.discover_agent("ResearchAgent")
        self.assertEqual(discovered.Name, "ResearchAgent")

        # Discovery of non-registered agent
        with self.assertRaises(ValidationException) as ex_dis:
            self.supervisor.discover_agent("RiskAgent")
        self.assertIn("not found", str(ex_dis.exception))

    def test_agent_lifecycle_tracking(self) -> None:
        """Test agent lifecycles update during and after executions."""
        self.supervisor.register_agent(self.research)
        self.assertEqual(self.supervisor.get_agent_lifecycle("ResearchAgent"), "Idle")

        context = AgentContext("ctx-loop")
        msg = AgentMessage("msg-loop", "Orchestrator", "ResearchAgent", {"asset": "AAPL"})

        # Execute safely
        response = self.supervisor.execute_agent_safely("ResearchAgent", msg, context)
        self.assertIsNotNone(response)

        # Back to Idle after success
        self.assertEqual(self.supervisor.get_agent_lifecycle("ResearchAgent"), "Idle")

    def test_agent_failure_and_isolation(self) -> None:
        """Test agent execution exceptions are caught safely and isolated by the supervisor."""
        self.supervisor.register_agent(self.research)

        # Send garbage context to trigger general python exception during message process
        msg_bad = AgentMessage("msg-bad", "Orchestrator", "ResearchAgent", None) # payload is None, will fail inside process_message
        context = AgentContext("ctx-bad")

        # Safe execution caught and logged, does not crash orchestrator
        response = self.supervisor.execute_agent_safely("ResearchAgent", msg_bad, context)
        self.assertIsNone(response)

        # State correctly transitioned to Failed
        self.assertEqual(self.supervisor.get_agent_lifecycle("ResearchAgent"), "Failed")
        failures = self.supervisor.get_agent_failures("ResearchAgent")
        self.assertEqual(len(failures), 1)
        self.assertIn("NoneType", failures[0]["error"])

    def test_agent_timeout_handling(self) -> None:
        """Test agent execution timeout handling is caught safely by the supervisor."""
        self.supervisor.register_agent(self.research)

        # Request long execution delay via payload
        msg_timeout = AgentMessage("msg-t", "Orchestrator", "ResearchAgent", {"asset": "AAPL", "simulate_agent_delay": 5.0})
        context = AgentContext("ctx-t")

        # Safe execution limits timeout, does not crash orchestrator
        response = self.supervisor.execute_agent_safely("ResearchAgent", msg_timeout, context, timeout_seconds=1.0)
        self.assertIsNone(response)

        self.assertEqual(self.supervisor.get_agent_lifecycle("ResearchAgent"), "Failed")
        failures = self.supervisor.get_agent_failures("ResearchAgent")
        self.assertEqual(len(failures), 1)
        self.assertIn("exceeded timeout limit", failures[0]["error"])

    def test_agent_response_leakage_blocking(self) -> None:
        """Test that the supervisor blocked any keyword leakages inside agent response payloads."""
        class MaliciousAgent(ResearchAgent):
            @property
            def Name(self) -> str:
                return "MaliciousAgent"
            def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
                # Bypasses internal agent keyword scans by mutating payload after creation,
                # but gets caught by the supervisor's active output validator.
                payload = {"unsafe_field": "safe_init"}
                msg = AgentMessage("msg-leak", self.Name, message.Sender, payload)
                payload["unsafe_field"] = "execute_trade now!"
                return msg

        malicious = MaliciousAgent()
        self.supervisor.register_agent(malicious)

        context = AgentContext("ctx-leak")
        msg = AgentMessage("msg-init", "Orchestrator", "MaliciousAgent", {"asset": "AAPL"})

        # Supervisor detects leak keyword "execute" inside response and raises validation safety exception
        response = self.supervisor.execute_agent_safely("MaliciousAgent", msg, context)
        self.assertIsNone(response)
        self.assertEqual(self.supervisor.get_agent_lifecycle("MaliciousAgent"), "Failed")
        failures = self.supervisor.get_agent_failures("MaliciousAgent")
        self.assertEqual(len(failures), 1)
        self.assertIn("blocked forbidden leakage keyword", failures[0]["error"])
