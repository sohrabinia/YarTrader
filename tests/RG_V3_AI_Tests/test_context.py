import unittest
from datetime import datetime
from src.Infrastructure.exceptions import ValidationException
from src.Decision.Intelligence.Agents.models import AgentContext

class TestAgentContext(unittest.TestCase):
    """
    Validates creation, versioning, enrichment, audit trails, and strict
    safety keyword scanning inside shared intelligence contexts.
    """

    def setUp(self) -> None:
        self.now = datetime.now()

    def test_context_creation_and_immutability(self) -> None:
        """Test successful creation, default properties, and frozen immutability."""
        ctx = AgentContext(
            ContextId="ctx-abc",
            Variables={"trend": "neutral"},
            Version=1,
            Metadata={"asset": "AAPL"}
        )
        self.assertEqual(ctx.ContextId, "ctx-abc")
        self.assertEqual(ctx.Variables["trend"], "neutral")
        self.assertEqual(ctx.Version, 1)

        # Immutability check: cannot set properties direct on a frozen dataclass
        with self.assertRaises(Exception):
            ctx.Version = 2

    def test_context_enrichment_and_versioning(self) -> None:
        """Test context enrichment creates a new version incremented instance with audits."""
        ctx_v1 = AgentContext("ctx-1", {"trend": "neutral"}, Version=1)

        ctx_v2 = ctx_v1.enrich("ResearchAgent", "research_sentiment", "bullish")

        # Original context must remain completely unchanged
        self.assertEqual(ctx_v1.Version, 1)
        self.assertEqual(ctx_v1.Variables.get("research_sentiment"), None)

        # Enriched context must have incremented version and new variable
        self.assertEqual(ctx_v2.Version, 2)
        self.assertEqual(ctx_v2.Variables["research_sentiment"], "bullish")
        self.assertEqual(len(ctx_v2.AuditTrail), 1)
        self.assertIn("Enriched key 'research_sentiment' by agent 'ResearchAgent'", ctx_v2.AuditTrail[0])

    def test_context_safety_keyword_rejection(self) -> None:
        """Test that forbidden trading keywords inside context are strictly blocked during creation."""
        # Forbidden word 'execute'
        with self.assertRaises(ValidationException) as ex:
            AgentContext("ctx-unsafe", {"command": "execute_trade"})
        self.assertIn("Safety Violation", str(ex.exception))

        # Forbidden word 'order'
        with self.assertRaises(ValidationException) as ex_ord:
            AgentContext("ctx-unsafe", {"meta": "create_order_failed"})
        self.assertIn("Safety Violation", str(ex_ord.exception))

    def test_context_enrichment_safety_rejection(self) -> None:
        """Test that forbidden keywords are strictly blocked during enrichment operations."""
        ctx = AgentContext("ctx-init", {"trend": "neutral"})

        # Enriching with 'position' keyword
        with self.assertRaises(ValidationException) as ex:
            ctx.enrich("ResearchAgent", "notes", "open position details")
        self.assertIn("Safety Violation", str(ex.exception))
