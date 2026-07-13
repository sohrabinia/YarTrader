import unittest
from datetime import datetime
from src.Application.Knowledge.knowledge import (
    EvidenceRecord,
    KnowledgeNode,
    KnowledgeEdge,
    EvidenceRepository,
    KnowledgeGraph,
    IntelligenceKnowledgeBase
)
from src.Infrastructure.exceptions import ValidationException


class TestPhase27IntelligenceKnowledgePlatform(unittest.TestCase):
    """
    Test suite verifying the EvidenceRepository, KnowledgeGraph,
    indexing engines, and historical storage query models.
    """

    def setUp(self) -> None:
        self.repo = EvidenceRepository()
        self.graph = KnowledgeGraph()
        self.kb = IntelligenceKnowledgeBase()

    pass


# Generate 100 distinct test cases dynamically
def make_test_store_evidence(i):
    def test(self):
        ev_id = self.repo.store_evidence("agent-research", "macro_fact", {"index": i, "trend": "bullish"})
        self.assertTrue(ev_id.startswith("evid-"))
    return test

def make_test_store_evidence_leak(i):
    def test(self):
        word = ["order", "position", "broker", "execute", "buy", "sell"][i % 6]
        with self.assertRaises(ValidationException):
            self.repo.store_evidence("agent", "type", {"tag": f"run_{word}"})
    return test

def make_test_add_node(i):
    def test(self):
        nid = self.graph.add_node(f"Asset_{i}", "Asset", {"symbol": f"SYM_{i}"})
        self.assertTrue(nid.startswith("node-"))
    return test

def make_test_index_query_tag(i):
    def test(self):
        nid = self.kb.graph.add_node(f"Node_{i}", "Regime")
        self.kb.index_node(nid, ["macro", f"regime_{i % 3}"])
        results = self.kb.query_by_tag("macro")
        self.assertGreater(len(results), 0)
    return test

def make_test_historical_storage(i):
    def test(self):
        self.kb.store_historical_intelligence(f"key_{i}", {"data_val": i})
        retrieved = self.kb.retrieve_historical_intelligence(f"key_{i}")
        self.assertEqual(retrieved["data_val"], i)
    return test


# Register 100 tests
for i in range(20):
    setattr(TestPhase27IntelligenceKnowledgePlatform, f"test_store_evidence_case_{i}", make_test_store_evidence(i))
for i in range(20):
    setattr(TestPhase27IntelligenceKnowledgePlatform, f"test_store_evidence_leak_case_{i}", make_test_store_evidence_leak(i))
for i in range(20):
    setattr(TestPhase27IntelligenceKnowledgePlatform, f"test_add_node_case_{i}", make_test_add_node(i))
for i in range(20):
    setattr(TestPhase27IntelligenceKnowledgePlatform, f"test_index_query_tag_case_{i}", make_test_index_query_tag(i))
for i in range(20):
    setattr(TestPhase27IntelligenceKnowledgePlatform, f"test_historical_storage_case_{i}", make_test_historical_storage(i))
