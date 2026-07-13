import unittest
from datetime import datetime
from src.Infrastructure.exceptions import ValidationException
from src.Decision.Intelligence.Agents.models import AgentMessage, AgentContext

class TestAgentCommunication(unittest.TestCase):
    """
    Validates message schemas, validation triggers, duplication checks,
    and end-to-end traceability of agent messages.
    """

    def setUp(self) -> None:
        self.now = datetime.now()

    def test_message_schema_validation(self) -> None:
        """Test successful creation and schema validation checks."""
        msg = AgentMessage(
            MessageId="msg-valid",
            Sender="SenderAgent",
            Recipient="RecipientAgent",
            Payload={"key": "value"},
            Timestamp=self.now,
            CorrelationId="corr-123"
        )
        self.assertEqual(msg.MessageId, "msg-valid")
        self.assertEqual(msg.Sender, "SenderAgent")
        self.assertEqual(msg.Recipient, "RecipientAgent")
        self.assertEqual(msg.Payload, {"key": "value"})
        self.assertEqual(msg.CorrelationId, "corr-123")

    def test_missing_message_parameters_failure(self) -> None:
        """Test missing message schema properties trigger validation failure."""
        # Empty MessageId
        with self.assertRaises(ValidationException) as ex:
            AgentMessage("", "Sender", "Recipient", {})
        self.assertIn("MessageId cannot be empty", str(ex.exception))

        # Empty Sender
        with self.assertRaises(ValidationException) as ex_send:
            AgentMessage("msg-1", " ", "Recipient", {})
        self.assertIn("Sender cannot be empty", str(ex_send.exception))

        # Empty Recipient
        with self.assertRaises(ValidationException) as ex_rec:
            AgentMessage("msg-1", "Sender", "", {})
        self.assertIn("Recipient cannot be empty", str(ex_rec.exception))

    def test_forbidden_keyword_rejection(self) -> None:
        """Test that forbidden trading keywords inside message payload are strictly blocked."""
        # Forbidden word 'broker'
        with self.assertRaises(ValidationException) as ex:
            AgentMessage("msg-unsafe", "Sender", "Recipient", {"broker_key": "active"})
        self.assertIn("Safety Violation", str(ex.exception))

        # Forbidden word 'place_order'
        with self.assertRaises(ValidationException) as ex_ord:
            AgentMessage("msg-unsafe", "Sender", "Recipient", {"action": "place_order"})
        self.assertIn("Safety Violation", str(ex_ord.exception))

    def test_duplicate_message_handling(self) -> None:
        """Test message replication tracking across message arrays."""
        processed_ids = set()

        msg1 = AgentMessage("msg-dup-1", "A", "B", {"val": 1})
        msg2 = AgentMessage("msg-dup-1", "A", "B", {"val": 1}) # duplicate ID

        processed_ids.add(msg1.MessageId)

        # Check duplicate
        self.assertTrue(msg2.MessageId in processed_ids)

    def test_message_traceability(self) -> None:
        """Test message correlations across communication hops."""
        msg1 = AgentMessage("msg-hop-1", "Orchestrator", "ResearchAgent", {"data": 12})
        msg2 = AgentMessage("msg-hop-2", "ResearchAgent", "StrategyAgent", {"data": 15}, CorrelationId=msg1.MessageId)

        self.assertEqual(msg2.CorrelationId, msg1.MessageId)
