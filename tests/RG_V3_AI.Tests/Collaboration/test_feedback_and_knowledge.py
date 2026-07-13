import unittest
from src.Application.Agents.collaboration import (
    AgentSelfEvaluator,
    KnowledgeSharingProtocol,
    AdvancedAgentReliabilityFeedback
)
from src.Infrastructure.exceptions import ValidationException


class TestAgentSelfEvaluator(unittest.TestCase):
    """
    Tests for AgentSelfEvaluator. (8 tests)
    """

    def setUp(self) -> None:
        self.evaluator = AgentSelfEvaluator()

    def test_self_eval_1_complete_approved(self) -> None:
        payload = {
            "asset": "AAPL",
            "timestamp": "now",
            "findings": ["Bullish"],
            "score": 0.85,
            "IsApproved": True,
            "confidence": 0.90
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_completeness"], 1.0)
        self.assertEqual(res["self_confidence"], 0.90)
        self.assertEqual(res["self_score"], 0.94)

    def test_self_eval_2_incomplete_payload(self) -> None:
        # missing several keys
        payload = {
            "asset": "AAPL"
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_completeness"], 0.3333)

    def test_self_eval_3_default_confidence(self) -> None:
        payload = {
            "asset": "AAPL",
            "timestamp": "now",
            "findings": []
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_confidence"], 0.8)

    def test_self_eval_4_dict_confidence(self) -> None:
        payload = {
            "confidence": {"Confidence": 0.95}
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_confidence"], 0.95)

    def test_self_eval_5_empty_payload(self) -> None:
        res = self.evaluator.self_evaluate({})
        self.assertEqual(res["self_completeness"], 0.0)

    def test_self_eval_6_clamped_completeness(self) -> None:
        payload = {
            "asset": "AAPL",
            "timestamp": "now",
            "findings": [],
            "score": 0.8,
            "IsApproved": True,
            "extra_key": 1
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_completeness"], 1.0) # maxes out at 1.0

    def test_self_eval_7_low_score_low_confidence(self) -> None:
        payload = {
            "confidence": 0.20
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertLess(res["self_score"], 0.5)

    def test_self_eval_8_high_score_high_confidence(self) -> None:
        payload = {
            "asset": "AAPL",
            "timestamp": "now",
            "findings": [],
            "score": 0.9,
            "IsApproved": True,
            "confidence": 0.95
        }
        res = self.evaluator.self_evaluate(payload)
        self.assertEqual(res["self_score"], 0.97)


class TestKnowledgeSharingProtocol(unittest.TestCase):
    """
    Tests for KnowledgeSharingProtocol, verifying pub-sub and leakage scans. (10 tests)
    """

    def setUp(self) -> None:
        self.protocol = KnowledgeSharingProtocol()

    def test_knowledge_1_share_and_query(self) -> None:
        self.protocol.share_knowledge("agent-a", "ma_crossover", {"value": 1.25}, tags=["indicator", "ma"])
        items = self.protocol.query_knowledge("ma_crossover")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].sender_id, "agent-a")
        self.assertEqual(items[0].value["value"], 1.25)

    def test_knowledge_2_query_unregistered_returns_empty(self) -> None:
        self.assertEqual(len(self.protocol.query_knowledge("unknown")), 0)

    def test_knowledge_3_query_by_tag(self) -> None:
        self.protocol.share_knowledge("agent-a", "k1", {}, tags=["indicator"])
        self.protocol.share_knowledge("agent-b", "k2", {}, tags=["trend"])
        self.protocol.share_knowledge("agent-c", "k3", {}, tags=["INDICATOR"])

        matched = self.protocol.query_by_tag("indicator")
        self.assertEqual(len(matched), 2)

    def test_knowledge_4_query_by_tag_no_match(self) -> None:
        self.assertEqual(len(self.protocol.query_by_tag("unknown")), 0)

    def test_knowledge_5_missing_sender_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.protocol.share_knowledge("", "k", {})

    def test_knowledge_6_missing_key_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.protocol.share_knowledge("sender", "", {})

    def test_knowledge_7_leakage_scan_rejects_forbidden_string(self) -> None:
        with self.assertRaises(ValidationException) as ex:
            self.protocol.share_knowledge("agent", "key", "place_order_now")
        self.assertIn("Safety Violation", str(ex.exception))

    def test_knowledge_8_leakage_scan_rejects_nested_dict(self) -> None:
        with self.assertRaises(ValidationException):
            self.protocol.share_knowledge("agent", "key", {"broker_payload": {"action": "trade"}})

    def test_knowledge_9_multiple_shares_same_key(self) -> None:
        self.protocol.share_knowledge("agent-a", "key", {"v": 1})
        self.protocol.share_knowledge("agent-b", "key", {"v": 2})
        items = self.protocol.query_knowledge("key")
        self.assertEqual(len(items), 2)

    def test_knowledge_10_tags_normalization(self) -> None:
        self.protocol.share_knowledge("agent", "key", {}, tags=["TAG"])
        items = self.protocol.query_knowledge("key")
        self.assertIn("tag", items[0].tags)


class TestAdvancedAgentReliabilityFeedback(unittest.TestCase):
    """
    Tests for AdvancedAgentReliabilityFeedback. (8 tests)
    """

    def setUp(self) -> None:
        self.feedback = AdvancedAgentReliabilityFeedback()

    def test_reliability_1_initial_scores(self) -> None:
        self.assertEqual(self.feedback.get_reliability_score("agent-research"), 0.90)
        self.assertEqual(self.feedback.get_reliability_score("agent-risk"), 0.95)

    def test_reliability_2_unregistered_agent_returns_default(self) -> None:
        self.assertEqual(self.feedback.get_reliability_score("unknown"), 0.80)

    def test_reliability_3_perfect_prediction_increases_reliability(self) -> None:
        # initial research reliability is 0.90
        # actual: 0.1, expected: 0.1 -> error 0.0 -> accuracy 1.0 (greater than 0.90)
        # new score = 0.90 + 0.15 * (1.0 - 0.90) = 0.90 + 0.015 = 0.915
        new_score = self.feedback.process_outcome_feedback("agent-research", 0.1, 0.1)
        self.assertEqual(new_score, 0.915)
        self.assertEqual(self.feedback.get_reliability_score("agent-research"), 0.915)

    def test_reliability_4_poor_prediction_decreases_reliability(self) -> None:
        # accuracy = 0.20 (lower than 0.90)
        new_score = self.feedback.process_outcome_feedback("agent-research", 0.9, 0.1)
        self.assertLess(new_score, 0.90)

    def test_reliability_5_unregistered_agent_feedback_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.feedback.process_outcome_feedback("unknown", 0.5, 0.5)

    def test_reliability_6_clamped_at_min_05(self) -> None:
        # Force outcome feedback to drop score repeatedly
        for _ in range(20):
            self.feedback.process_outcome_feedback("agent-research", 1.0, 0.0) # Accuracy = 0.0
        self.assertEqual(self.feedback.get_reliability_score("agent-research"), 0.50)

    def test_reliability_7_clamped_at_max_10(self) -> None:
        # Force outcome feedback to increase score repeatedly
        for _ in range(20):
            self.feedback.process_outcome_feedback("agent-research", 0.5, 0.5) # Accuracy = 1.0
        self.assertAlmostEqual(self.feedback.get_reliability_score("agent-research"), 1.0, places=2)

    def test_reliability_8_partial_drift(self) -> None:
        score_1 = self.feedback.process_outcome_feedback("agent-research", 0.5, 0.4) # Accuracy = 0.9
        # accuracy = current reliability, so no change
        self.assertEqual(score_1, 0.90)
