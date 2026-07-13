import unittest
from datetime import datetime
from src.Application.Agents.communication import IntelligenceMessage, MessageRouter, TraceRecord
from src.Infrastructure.exceptions import ValidationException


class TestAgentCommunication(unittest.TestCase):
    """
    Verifies agent-to-agent communication, message schemas, duplicate checking,
    and end-to-end trace trails.
    """

    def setUp(self) -> None:
        self.router = MessageRouter()
        self.now = datetime.now()

    def test_valid_message_creation(self) -> None:
        """Test: Valid message compiles and validates correctly."""
        msg = IntelligenceMessage(
            message_id="msg-valid",
            sender_id="sender-agent",
            recipient_id="recipient-agent",
            timestamp=self.now,
            message_type="ResearchReport",
            payload={"indicator": "RSI", "value": 45.5}
        )
        self.assertEqual(msg.message_id, "msg-valid")
        self.assertEqual(msg.payload["indicator"], "RSI")

    def test_missing_and_invalid_schema_rejection(self) -> None:
        """Test: Schema rejects missing or malformed fields."""
        # Empty message_id
        with self.assertRaises(ValidationException):
            IntelligenceMessage(
                message_id="",
                sender_id="sender",
                recipient_id="recipient",
                timestamp=self.now,
                message_type="Test"
            )

        # Invalid type for timestamp
        with self.assertRaises(ValidationException):
            IntelligenceMessage(
                message_id="msg-1",
                sender_id="sender",
                recipient_id="recipient",
                timestamp="invalid-date-string",
                message_type="Test"
            )

        # Invalid type for payload
        with self.assertRaises(ValidationException):
            IntelligenceMessage(
                message_id="msg-1",
                sender_id="sender",
                recipient_id="recipient",
                timestamp=self.now,
                message_type="Test",
                payload="not-a-dict"
            )

    def test_duplicate_message_handling(self) -> None:
        """Test: Router rejects duplicate message IDs."""
        msg = IntelligenceMessage(
            message_id="msg-unique-id",
            sender_id="sender",
            recipient_id="recipient",
            timestamp=self.now,
            message_type="Test",
            payload={}
        )

        class MockAgent:
            def process(self, c, m): pass

        agent = MockAgent()

        # First route: Success
        routed = self.router.process_and_route(msg, agent)
        self.assertEqual(routed, msg)

        # Second route with same ID: Fails
        with self.assertRaises(ValidationException) as ex:
            self.router.process_and_route(msg, agent)
        self.assertIn("Duplicate message detected", str(ex.exception))

    def test_message_routing_and_traceability(self) -> None:
        """Test: Routing appends correct records to trace trail."""
        msg = IntelligenceMessage(
            message_id="msg-trace",
            sender_id="agent-a",
            recipient_id="agent-b",
            timestamp=self.now,
            message_type="ForwardTest",
            payload={"data": 123}
        )

        # Route from agent-b to agent-c
        routed_b_to_c = msg.route_to("agent-c", "agent-b")
        self.assertEqual(routed_b_to_c.sender_id, "agent-b")
        self.assertEqual(routed_b_to_c.recipient_id, "agent-c")
        self.assertEqual(len(routed_b_to_c.trace_trail), 1)
        self.assertEqual(routed_b_to_c.trace_trail[0].agent_id, "agent-b")

        # Route from agent-c to agent-d
        routed_c_to_d = routed_b_to_c.route_to("agent-d", "agent-c")
        self.assertEqual(len(routed_c_to_d.trace_trail), 2)
        self.assertEqual(routed_c_to_d.trace_trail[1].agent_id, "agent-c")
