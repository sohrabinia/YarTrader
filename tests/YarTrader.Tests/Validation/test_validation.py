import unittest
from datetime import datetime
from src.Application.Agents.concrete_agents import ValidationAgent
from src.Application.Agents.context import AgentContextBuilder
from src.Application.Agents.communication import IntelligenceMessage
from src.Infrastructure.exceptions import ValidationException


class TestValidationAgent(unittest.TestCase):
    """
    Verifies ValidationAgent behavior, compliance audits, quality checks,
    and exclusion of any decision modification.
    """

    def setUp(self) -> None:
        self.agent = ValidationAgent()
        self.context = AgentContextBuilder.create_with_market_data("ETHUSD", "D1")

    def test_compliance_and_quality_audit(self) -> None:
        """Test: Compliance run outputs proper health and compliance status."""
        msg = IntelligenceMessage(
            message_id="msg-val-task",
            sender_id="supervisor",
            recipient_id=self.agent.agent_id,
            timestamp=datetime.now(),
            message_type="ExecuteTask",
            payload={"asset": "ETHUSD"}
        )

        output = self.agent.process(self.context, msg)

        self.assertEqual(output.message_type, "ComplianceAudit")
        payload = output.payload
        self.assertTrue(payload["compliance_checked"])
        self.assertGreaterEqual(payload["data_quality_score"], 0.90)
        self.assertEqual(payload["system_health_status"], "Healthy")

    def test_forbidden_decision_modification_rejection(self) -> None:
        """Test: ValidationAgent rejects tasks directing it to modify decisions."""
        forbidden_msg = IntelligenceMessage(
            message_id="msg-forbidden-mod",
            sender_id="supervisor",
            recipient_id=self.agent.agent_id,
            timestamp=datetime.now(),
            message_type="ExecuteTask",
            payload={"directive": "change_state_override"}
        )

        with self.assertRaises(ValidationException) as ex:
            self.agent.process(self.context, forbidden_msg)
        self.assertIn("Isolation Violation", str(ex.exception))
