import unittest
import time
from datetime import datetime, timedelta
from src.Application.Agents.memory import AgentMemory, MemoryEntry
from src.Infrastructure.exceptions import ValidationException


class TestAgentMemory(unittest.TestCase):
    """
    Verifies that AgentMemory stores, isolates, retrieves, and expires structured intelligence entries.
    Does not run any machine learning.
    """

    def setUp(self) -> None:
        self.memory = AgentMemory(max_size=3)

    def test_memory_storage_and_retrieval(self) -> None:
        """Test basic storage and retrieval under different namespaces (isolation)."""
        # Store in ResearchAgent namespace
        self.memory.store("research", "rsi", 65.2, tags=["tech", "rsi"])
        # Store in RiskAgent namespace
        self.memory.store("risk", "rsi", 30.0, tags=["risk", "rsi"])

        # Isolation checks: retrieval is correct for each namespace
        self.assertEqual(self.memory.retrieve("research", "rsi"), 65.2)
        self.assertEqual(self.memory.retrieve("risk", "rsi"), 30.0)

        # Non-existent key
        self.assertIsNone(self.memory.retrieve("research", "macd"))

    def test_fifo_size_expiration(self) -> None:
        """Test FIFO size-limit eviction when exceeding max_size (3)."""
        self.memory.store("research", "k1", 1)
        self.memory.store("research", "k2", 2)
        self.memory.store("research", "k3", 3)

        # Storage has exactly 3 elements
        all_mem = self.memory.get_all_namespace_memory("research")
        self.assertEqual(len(all_mem), 3)

        # Store 4th element: k1 should be evicted (oldest)
        self.memory.store("research", "k4", 4)
        self.assertIsNone(self.memory.retrieve("research", "k1"))
        self.assertEqual(self.memory.retrieve("research", "k2"), 2)
        self.assertEqual(self.memory.retrieve("research", "k4"), 4)

    def test_ttl_expiration(self) -> None:
        """Test: Entries are pruned or return None when TTL seconds elapse."""
        # Store with 0.1 second TTL limit
        self.memory.store("research", "temp_key", "temp_val", ttl_seconds=1)

        # Immediate retrieval works
        self.assertEqual(self.memory.retrieve("research", "temp_key"), "temp_val")

        # Create a mock entry with expired timestamp directly to avoid sleeping
        self.memory.clear()
        self.memory.store("research", "expired_key", "expired_val", ttl_seconds=1)

        # Manually alter the timestamp to simulate past insertion
        entries = self.memory._store["research"]
        entries[0].timestamp = datetime.now() - timedelta(seconds=2)

        # Retrieval should now return None and purge the expired entry
        self.assertIsNone(self.memory.retrieve("research", "expired_key"))
        self.assertEqual(len(self.memory.get_all_namespace_memory("research")), 0)

    def test_query_by_tags(self) -> None:
        """Test: Querying entries matching list of tags."""
        self.memory.store("research", "key1", "val1", tags=["trend", "bullish"])
        self.memory.store("research", "key2", "val2", tags=["volatility", "high"])
        self.memory.store("research", "key3", "val3", tags=["trend", "bearish"])

        trend_vals = self.memory.query_by_tags("research", ["trend"])
        self.assertEqual(len(trend_vals), 2)
        self.assertIn("val1", trend_vals)
        self.assertIn("val3", trend_vals)
        self.assertNotIn("val2", trend_vals)
