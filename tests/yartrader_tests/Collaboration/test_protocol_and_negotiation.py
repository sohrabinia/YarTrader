import unittest
from datetime import datetime
from typing import Any, Dict, List
from src.Application.Agents.collaboration import (
    CollaborationProtocol,
    NegotiationFramework,
    NegotiationProposal,
    CollectiveIntelligenceEvaluator
)
from src.Application.Agents.communication import IntelligenceMessage, MessageRouter
from src.Application.Agents.context import AgentContextBuilder


class MockAgent:
    def __init__(self, agent_id: str, payload_to_return: dict, message_type_to_return: str) -> None:
        self.agent_id = agent_id
        self.payload = payload_to_return
        self.msg_type = message_type_to_return

    def process(self, context: Any, message: Any) -> IntelligenceMessage:
        return IntelligenceMessage(
            message_id=f"msg-{self.agent_id}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type=self.msg_type,
            payload=self.payload
        )


class TestCollaborationProtocol(unittest.TestCase):
    """
    Tests for CollaborationProtocol, verifying routing, message passing,
    and sequence execution. (10 tests)
    """

    def setUp(self) -> None:
        self.router = MessageRouter()
        self.protocol = CollaborationProtocol(self.router)
        self.context = AgentContextBuilder.create_with_market_data("AAPL", "H4")

    def test_protocol_1_dispatch_single_agent(self) -> None:
        agent = MockAgent("agent-research", {"findings": ["Bullish momentum"]}, "ResearchReport")
        responses = self.protocol.dispatch_collaborative_round([agent], self.context, {"asset": "AAPL"})
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].sender_id, "agent-research")
        self.assertEqual(responses[0].payload["findings"], ["Bullish momentum"])

    def test_protocol_2_dispatch_multiple_agents(self) -> None:
        a1 = MockAgent("agent-research", {"findings": ["Bullish"]}, "ResearchReport")
        a2 = MockAgent("agent-strategy", {"OverallScore": 0.85}, "StrategyEvaluation")
        responses = self.protocol.dispatch_collaborative_round([a1, a2], self.context, {"asset": "AAPL"})
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].sender_id, "agent-research")
        self.assertEqual(responses[1].sender_id, "agent-strategy")

    def test_protocol_3_degrades_gracefully_on_exception(self) -> None:
        class CrashingAgent:
            def __init__(self) -> None:
                self.agent_id = "agent-crasher"
            def process(self, c, m):
                raise RuntimeError("Crashing on purpose!")

        a1 = CrashingAgent()
        a2 = MockAgent("agent-research", {"findings": []}, "ResearchReport")
        responses = self.protocol.dispatch_collaborative_round([a1, a2], self.context, {})
        # Should bypass CrashingAgent and complete round with MockAgent
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].sender_id, "agent-research")

    def test_protocol_4_skips_invalid_agent_interface(self) -> None:
        class NonCompliantAgent:
            pass  # Missing process method

        responses = self.protocol.dispatch_collaborative_round([NonCompliantAgent()], self.context, {})
        self.assertEqual(len(responses), 0)

    def test_protocol_5_message_types_matching(self) -> None:
        agent = MockAgent("agent-research", {}, "CustomType")
        responses = self.protocol.dispatch_collaborative_round([agent], self.context, {})
        self.assertEqual(responses[0].message_type, "CustomType")

    def test_protocol_6_sequential_order_preserved(self) -> None:
        a1 = MockAgent("a1", {}, "Type")
        a2 = MockAgent("a2", {}, "Type")
        responses = self.protocol.dispatch_collaborative_round([a1, a2], self.context, {})
        self.assertEqual(responses[0].sender_id, "a1")
        self.assertEqual(responses[1].sender_id, "a2")

    def test_protocol_7_empty_agents_list(self) -> None:
        responses = self.protocol.dispatch_collaborative_round([], self.context, {})
        self.assertEqual(len(responses), 0)

    def test_protocol_8_router_rejection_of_duplicates_bypassed_or_logged(self) -> None:
        # MessageRouter seen ids is checked
        agent = MockAgent("a1", {}, "Type")
        # Send first round: success
        self.protocol.dispatch_collaborative_round([agent], self.context, {})
        # Send second round with same agent (its msg-id is "msg-a1" static): Router throws duplicate, which protocol catches/bypasses
        responses = self.protocol.dispatch_collaborative_round([agent], self.context, {})
        # Since it throws Duplicate exception inside router, protocol catches it and continues safely
        self.assertEqual(len(responses), 0)

    def test_protocol_9_payload_integrity(self) -> None:
        agent = MockAgent("a1", {"v": 10}, "Type")
        responses = self.protocol.dispatch_collaborative_round([agent], self.context, {})
        self.assertEqual(responses[0].payload["v"], 10)

    def test_protocol_10_empty_payload(self) -> None:
        agent = MockAgent("a1", {}, "Type")
        responses = self.protocol.dispatch_collaborative_round([agent], self.context, {})
        self.assertEqual(responses[0].payload, {})


class TestNegotiationFramework(unittest.TestCase):
    """
    Tests for NegotiationFramework, verifying compromised weight outputs. (8 tests)
    """

    def setUp(self) -> None:
        self.framework = NegotiationFramework()

    def test_negotiation_1_single_proposal(self) -> None:
        prop = NegotiationProposal("agent-strategy", "AAPL", 0.85, 0.90)
        priorities = {"agent-strategy": 0.80}
        result = self.framework.negotiate_compromise([prop], priorities)
        self.assertEqual(result["AAPL"], 0.85)

    def test_negotiation_2_even_proposals_even_priorities(self) -> None:
        p1 = NegotiationProposal("agent-a", "AAPL", 0.80, 1.0)
        p2 = NegotiationProposal("agent-b", "AAPL", 0.60, 1.0)
        priorities = {"agent-a": 0.5, "agent-b": 0.5}
        result = self.framework.negotiate_compromise([p1, p2], priorities)
        # Weight average = (0.8*0.5*1.0 + 0.6*0.5*1.0) / (0.5*1.0 + 0.5*1.0) = 0.70
        self.assertEqual(result["AAPL"], 0.70)

    def test_negotiation_3_uneven_priorities(self) -> None:
        p1 = NegotiationProposal("agent-a", "AAPL", 0.80, 1.0)
        p2 = NegotiationProposal("agent-b", "AAPL", 0.50, 1.0)
        # Agent B has high priority
        priorities = {"agent-a": 0.2, "agent-b": 0.8}
        result = self.framework.negotiate_compromise([p1, p2], priorities)
        # Weighted average = (0.8*0.2 + 0.5*0.8) / (0.2 + 0.8) = 0.16 + 0.40 = 0.56
        self.assertAlmostEqual(result["AAPL"], 0.56)

    def test_negotiation_4_uneven_confidence(self) -> None:
        p1 = NegotiationProposal("agent-a", "AAPL", 0.80, 0.90)
        p2 = NegotiationProposal("agent-b", "AAPL", 0.50, 0.10)
        priorities = {"agent-a": 0.5, "agent-b": 0.5}
        result = self.framework.negotiate_compromise([p1, p2], priorities)
        # (0.8*0.45 + 0.5*0.05) / (0.45 + 0.05) = (0.36 + 0.025) / 0.50 = 0.77
        self.assertAlmostEqual(result["AAPL"], 0.77)

    def test_negotiation_5_multiple_assets(self) -> None:
        p1 = NegotiationProposal("agent-a", "AAPL", 0.80, 1.0)
        p2 = NegotiationProposal("agent-b", "MSFT", 0.40, 1.0)
        priorities = {"agent-a": 0.5, "agent-b": 0.5}
        result = self.framework.negotiate_compromise([p1, p2], priorities)
        self.assertEqual(result["AAPL"], 0.80)
        self.assertEqual(result["MSFT"], 0.40)

    def test_negotiation_6_empty_proposals(self) -> None:
        result = self.framework.negotiate_compromise([], {})
        self.assertEqual(result, {})

    def test_negotiation_7_zero_confidence_bypassed(self) -> None:
        p1 = NegotiationProposal("agent-a", "AAPL", 0.80, 0.0)
        p2 = NegotiationProposal("agent-b", "AAPL", 0.50, 1.0)
        priorities = {"agent-a": 0.5, "agent-b": 0.5}
        result = self.framework.negotiate_compromise([p1, p2], priorities)
        # Agent A has 0.0 confidence, so only Agent B counts
        self.assertEqual(result["AAPL"], 0.50)

    def test_negotiation_8_missing_priority_uses_default(self) -> None:
        p1 = NegotiationProposal("agent-unregistered", "AAPL", 0.60, 1.0)
        result = self.framework.negotiate_compromise([p1], {})
        self.assertEqual(result["AAPL"], 0.60)


class TestCollectiveIntelligenceEvaluator(unittest.TestCase):
    """
    Tests for CollectiveIntelligenceEvaluator. (8 tests)
    """

    def setUp(self) -> None:
        self.evaluator = CollectiveIntelligenceEvaluator()

    def test_evaluator_1_complete_framework(self) -> None:
        context_data = {
            "ResearchReport": {"findings": ["Market is Bullish"]},
            "StrategyEvaluation": {"score": {"OverallScore": 0.85}},
            "RiskAssessment": {},
            "ComplianceAudit": {},
            "LearningFeedback": {}
        }
        contribs = ["agent-research", "agent-strategy", "agent-risk", "agent-validation", "agent-learning"]
        metrics = self.evaluator.evaluate_collective_metrics(context_data, contribs)
        self.assertEqual(metrics["coverage"], 1.0)
        self.assertEqual(metrics["synergy"], 1.0)
        self.assertEqual(metrics["consensus"], 0.85)

    def test_evaluator_2_low_coverage(self) -> None:
        context_data = {}
        contribs = ["agent-research"]
        metrics = self.evaluator.evaluate_collective_metrics(context_data, contribs)
        self.assertEqual(metrics["coverage"], 0.20)
        self.assertEqual(metrics["synergy"], 0.50)

    def test_evaluator_3_mid_synergy(self) -> None:
        context_data = {
            "ResearchReport": {},
            "StrategyEvaluation": {}
        }
        metrics = self.evaluator.evaluate_collective_metrics(context_data, [])
        self.assertEqual(metrics["synergy"], 0.70)

    def test_evaluator_4_consensus_disagreement_bullish_vs_low_strategy(self) -> None:
        context_data = {
            "ResearchReport": {"findings": ["Market is bullish momentum"]},
            "StrategyEvaluation": {"score": {"OverallScore": 0.25}}
        }
        metrics = self.evaluator.evaluate_collective_metrics(context_data, [])
        self.assertEqual(metrics["consensus"], 0.35)

    def test_evaluator_5_consensus_disagreement_bearish_vs_high_strategy(self) -> None:
        context_data = {
            "ResearchReport": {"findings": ["Stable conditions"]}, # not bullish
            "StrategyEvaluation": {"score": {"OverallScore": 0.85}}
        }
        metrics = self.evaluator.evaluate_collective_metrics(context_data, [])
        self.assertEqual(metrics["consensus"], 0.40)

    def test_evaluator_6_synergy_boosted_by_risk(self) -> None:
        context_data = {"RiskAssessment": {}}
        metrics = self.evaluator.evaluate_collective_metrics(context_data, [])
        self.assertEqual(metrics["synergy"], 0.65)

    def test_evaluator_7_synergy_boosted_by_compliance(self) -> None:
        context_data = {"ComplianceAudit": {}}
        metrics = self.evaluator.evaluate_collective_metrics(context_data, [])
        self.assertEqual(metrics["synergy"], 0.60)

    def test_evaluator_8_consensus_default_no_info(self) -> None:
        metrics = self.evaluator.evaluate_collective_metrics({}, [])
        self.assertEqual(metrics["consensus"], 0.85)
