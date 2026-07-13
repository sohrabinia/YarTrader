import unittest
import time
from datetime import datetime
from src.Decision.Intelligence.Agents.models import AgentMemory

class TestAgentMemory(unittest.TestCase):
    """
    Validates agent memory storage, query retrieval, memory isolation,
    and automatic record expiration (TTL) rules.
    """

    def setUp(self) -> None:
        self.memory = AgentMemory()

    def test_memory_storage_and_retrieval(self) -> None:
        """Test successful storage and historical query retrieval."""
        self.memory.store_memory("ResearchAgent", "insight_key", "bullish_trend")

        histories = self.memory.retrieve_memory("ResearchAgent", "insight_key")
        self.assertEqual(len(histories), 1)
        self.assertEqual(histories[0], "bullish_trend")

    def test_memory_isolation(self) -> None:
        """Test that agents cannot access or overwrite other agents' private memory storage."""
        self.memory.store_memory("ResearchAgent", "private_insight", "research_findings")
        self.memory.store_memory("RiskAgent", "private_insight", "risk_findings")

        res_hist = self.memory.retrieve_memory("ResearchAgent", "private_insight")
        risk_hist = self.memory.retrieve_memory("RiskAgent", "private_insight")

        # Isolation preserved
        self.assertEqual(res_hist, ["research_findings"])
        self.assertEqual(risk_hist, ["risk_findings"])

    def test_memory_expiration_rules(self) -> None:
        """Test memory automatic record expiration (TTL) rules."""
        # Store with 0 second TTL (expired immediately)
        self.memory.store_memory("ResearchAgent", "temp_key", "temp_value", ttl_seconds=-1)

        # Store with normal active key
        self.memory.store_memory("ResearchAgent", "active_key", "active_value", ttl_seconds=10)

        temp_results = self.memory.retrieve_memory("ResearchAgent", "temp_key")
        active_results = self.memory.retrieve_memory("ResearchAgent", "active_key")

        # Expired is empty, active is retrieved
        self.assertEqual(len(temp_results), 0)
        self.assertEqual(active_results, ["active_value"])
