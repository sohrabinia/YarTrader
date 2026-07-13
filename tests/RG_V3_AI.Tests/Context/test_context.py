import unittest
import copy
from datetime import datetime
from src.Application.Agents.context import AgentContext, AgentContextBuilder, ContextAuditRecord
from src.Infrastructure.exceptions import ValidationException


class TestAgentContext(unittest.TestCase):
    """
    Verifies AgentContext creation, versioning, copy-on-write enrichment,
    immutability, and full audit logs.
    """

    def test_context_creation(self) -> None:
        """Test: Creating a fresh or market-data context."""
        ctx_empty = AgentContextBuilder.create_empty()
        self.assertEqual(ctx_empty.version, 1)
        self.assertEqual(ctx_empty.data, {})
        self.assertEqual(len(ctx_empty.audit_trail), 0)

        ctx_mkt = AgentContextBuilder.create_with_market_data("AAPL", "H4")
        self.assertEqual(ctx_mkt.version, 1)
        self.assertEqual(ctx_mkt.data["asset"], "AAPL")
        self.assertEqual(ctx_mkt.data["timeframe"], "H4")
        self.assertEqual(len(ctx_mkt.audit_trail), 1)
        self.assertEqual(ctx_mkt.audit_trail[0].agent_id, "system")

    def test_context_enrichment_and_versioning(self) -> None:
        """Test: Enriching returns a copy-on-write new version, leaving past versions intact."""
        ctx1 = AgentContextBuilder.create_with_market_data("MSFT", "D1")

        # Enrich version 1 -> version 2
        ctx2 = ctx1.enrich(agent_id="agent-research", key="rsi_value", value=68.5)

        self.assertEqual(ctx1.version, 1)
        self.assertNotIn("rsi_value", ctx1.data)

        self.assertEqual(ctx2.version, 2)
        self.assertEqual(ctx2.data["rsi_value"], 68.5)
        self.assertEqual(len(ctx2.audit_trail), 2)
        self.assertEqual(ctx2.audit_trail[1].agent_id, "agent-research")

    def test_context_immutability(self) -> None:
        """Test: Direct mutations are prevented by frozen class, and nested copies are safe."""
        ctx = AgentContextBuilder.create_empty()

        # Cannot assign properties directly
        with self.assertRaises(Exception):
            ctx.version = 5  # Should fail since dataclass is frozen

        # Deep copy ensures dict mutations do not leakage back
        nested_dict = {"levels": [1.1, 1.2]}
        ctx2 = ctx.enrich("agent", "nested", nested_dict)

        # Mutate the original dictionary
        nested_dict["levels"].append(1.3)

        # Enriched context should remain unaffected
        self.assertEqual(ctx2.data["nested"]["levels"], [1.1, 1.2])

    def test_context_safety_validation(self) -> None:
        """Test: Rejecting forbidden keywords on enrichment."""
        ctx = AgentContextBuilder.create_empty()

        # Cannot enrich with forbidden trading keywords
        with self.assertRaises(ValidationException) as ex:
            ctx.enrich("agent", "action", "execute_now")
        self.assertIn("Safety Violation", str(ex.exception))

        with self.assertRaises(ValidationException) as ex:
            ctx.enrich("agent", "action", {"broker_key": "123"})
        self.assertIn("Safety Violation", str(ex.exception))
