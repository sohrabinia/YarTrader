import os
import shutil
import unittest
from datetime import datetime
from src.Research.Brain.models import SimulatedDecision, PersistentDecisionStore

class TestPersistentDecisionStore(unittest.TestCase):
    """
    Verifies auditable SimulatedDecision attributes and PersistentDecisionStore SQLite transactions.
    """

    def setUp(self) -> None:
        self.test_db_dir = os.path.join("runtime_logs", "test_decisions")
        self.db_path = os.path.join(self.test_db_dir, "decisions_audit_test.db")
        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)
        self.store = PersistentDecisionStore(db_path=self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)

    def test_simulated_decision_schema_extensions(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        decision = SimulatedDecision(
            timestamp=now,
            symbol="XAUUSD",
            price=1800.0,
            decision_action="BUY",
            decision_id="dec-test-01",
            market_state={"trend": "BULLISH"},
            pattern_used="BASE_BREAKOUT_COMPRESSION",
            reasoning="London breakout verified",
            confidence=85.0,
            risk_score=2.5,
            unknown_factors="FOMC speech in 3 hours",
            outcome="SUCCESS"
        )

        d = decision.to_dict()
        self.assertEqual(d["decision_id"], "dec-test-01")
        self.assertEqual(d["market_state"]["trend"], "BULLISH")
        self.assertEqual(d["pattern_used"], "BASE_BREAKOUT_COMPRESSION")
        self.assertEqual(d["reasoning"], "London breakout verified")
        self.assertEqual(d["confidence"], 85.0)
        self.assertEqual(d["risk_score"], 2.5)
        self.assertEqual(d["unknown_factors"], "FOMC speech in 3 hours")
        self.assertEqual(d["outcome"], "SUCCESS")

        restored = SimulatedDecision.from_dict(d)
        self.assertEqual(restored.decision_id, "dec-test-01")
        self.assertEqual(restored.confidence, 85.0)
        self.assertEqual(restored.risk_score, 2.5)
        self.assertEqual(restored.outcome, "SUCCESS")

    def test_persistent_decision_store_sqlite(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        decision = SimulatedDecision(
            timestamp=now,
            symbol="XAUUSD",
            price=1800.0,
            decision_action="BUY",
            decision_id="dec-test-sqlite",
            market_state={"trend": "BULLISH"},
            pattern_used="BASE_BREAKOUT_COMPRESSION",
            reasoning="London breakout verified",
            confidence=85.0,
            risk_score=2.5,
            unknown_factors="FOMC speech in 3 hours",
            outcome="SUCCESS"
        )

        # Save to SQLite
        self.store.save_decision(decision)

        # Retrieve and assert
        retrieved = self.store.get_decision("dec-test-sqlite")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.decision_id, "dec-test-sqlite")
        self.assertEqual(retrieved.symbol, "XAUUSD")
        self.assertEqual(retrieved.price, 1800.0)
        self.assertEqual(retrieved.pattern_used, "BASE_BREAKOUT_COMPRESSION")
        self.assertEqual(retrieved.confidence, 85.0)
        self.assertEqual(retrieved.risk_score, 2.5)
        self.assertEqual(retrieved.outcome, "SUCCESS")

        # List all
        decisions_list = self.store.list_decisions()
        self.assertEqual(len(decisions_list), 1)
        self.assertEqual(decisions_list[0].decision_id, "dec-test-sqlite")
