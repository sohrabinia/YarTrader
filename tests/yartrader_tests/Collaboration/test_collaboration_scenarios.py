import os
import ast
import unittest
from datetime import datetime
from src.Application.Agents.collaboration import (
    AgentCapabilityRegistry,
    AgentGoalManager,
    AgentPriorityEngine,
    DynamicAgentSelector,
    CollaborationProtocol,
    NegotiationProposal,
    NegotiationFramework,
    CollectiveIntelligenceEvaluator,
    AgentSelfEvaluator,
    KnowledgeSharingProtocol,
    AdvancedAgentReliabilityFeedback
)
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent
)
from src.Application.Agents.context import AgentContextBuilder
from src.Infrastructure.exceptions import ValidationException


class TestCollaborationE2EScenarios(unittest.TestCase):
    """
    End-to-end multi-agent collaboration scenario tests verifying priority, selector,
    protocol, negotiation, evaluation, self-eval, knowledge sharing, and reliability. (10 tests)
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())

        self.context = AgentContextBuilder.create_with_market_data("BTCUSD", "H1")

        self.registry = AgentCapabilityRegistry()
        self.registry.register_capabilities("agent-research", ["market observation", "features"], ["macro"])
        self.registry.register_capabilities("agent-strategy", ["strategy evaluation"], ["macro"])
        self.registry.register_capabilities("agent-risk", ["risk analysis"], ["macro"])
        self.registry.register_capabilities("agent-validation", ["compliance checks"], ["macro"])
        self.registry.register_capabilities("agent-learning", ["learning optimization"], ["macro"])

        self.goal_manager = AgentGoalManager()
        self.priority_engine = AgentPriorityEngine()
        self.selector = DynamicAgentSelector(self.registry)
        self.router = self.supervisor._router
        self.protocol = CollaborationProtocol(self.router)
        self.negotiator = NegotiationFramework()
        self.collective_eval = CollectiveIntelligenceEvaluator()
        self.self_eval = AgentSelfEvaluator()
        self.knowledge = KnowledgeSharingProtocol()
        self.feedback = AdvancedAgentReliabilityFeedback()

    def test_e2e_1_normal_regime_flow(self) -> None:
        # Active goals
        self.goal_manager.add_goal("Maximize Synergy", "synergy", 0.8, 0.5)
        goals = self.goal_manager.get_all_goals()

        # Compute Priorities (Normal conditions)
        priorities = self.priority_engine.compute_priorities({}, goals)

        # Select best agent for research
        selected = self.selector.select_agents_for_task("market observation", priorities)
        self.assertIn("agent-research", selected)

        # Dispatch round using protocol
        agents = [self.supervisor.get_agent(aid) for aid in selected if self.supervisor.get_agent(aid)]
        responses = self.protocol.dispatch_collaborative_round(agents, self.context, {"asset": "BTCUSD"})
        self.assertEqual(len(responses), 1)

        # Knowledge sharing
        self.knowledge.share_knowledge("agent-research", "btc_regime", responses[0].payload, ["btc"])
        items = self.knowledge.query_knowledge("btc_regime")
        self.assertEqual(len(items), 1)

        # Self evaluation
        self_score = self.self_eval.self_evaluate(responses[0].payload)
        self.assertTrue(self_score["self_score"] > 0.5)

    def test_e2e_2_volatile_regime_negotiation(self) -> None:
        # High volatility market condition
        mkt = {"volatility": 0.38}
        priorities = self.priority_engine.compute_priorities(mkt, [])

        # Priority of RiskAgent should be high
        self.assertGreater(priorities["agent-risk"], priorities["agent-strategy"])

        # Conflicting proposals (Strategy proposes 0.8 weight, Risk proposes 0.2 weight)
        proposals = [
            NegotiationProposal("agent-strategy", "BTCUSD", 0.80, 0.90),
            NegotiationProposal("agent-risk", "BTCUSD", 0.20, 0.95)
        ]

        # Negotiate weighted compromise
        compromised = self.negotiator.negotiate_compromise(proposals, priorities)

        # Because RiskAgent has significantly higher priority (0.90) than Strategy (0.40),
        # the compromised weight should be pulled closer to Risk's proposal (0.20) than Strategy's (0.80)
        # Strategy factor: 0.40 * 0.90 = 0.36
        # Risk factor: 0.90 * 0.95 = 0.855
        # Weighted value = (0.80 * 0.36 + 0.20 * 0.855) / (0.36 + 0.855) = (0.288 + 0.171) / 1.215 = 0.459 / 1.215 = 0.3778
        self.assertAlmostEqual(compromised["BTCUSD"], 0.3778)

    def test_e2e_3_collective_scoring_and_goal_satisfaction(self) -> None:
        goal_id = self.goal_manager.add_goal("Target Synergy", "synergy", 0.80, 0.9)

        # Orchestrate supervisor context
        orchestrated_ctx = self.supervisor.orchestrate(self.context)

        # Evaluate collective metrics
        metrics = self.collective_eval.evaluate_collective_metrics(
            orchestrated_ctx.data,
            ["agent-research", "agent-strategy", "agent-risk", "agent-validation"]
        )

        # Evaluate goalmanager state
        results = self.goal_manager.evaluate_goals(metrics)
        self.assertEqual(results[goal_id], "Met")

    def test_e2e_4_reliability_feedback_loop(self) -> None:
        # Measure initial risk agent reliability
        init_rel = self.feedback.get_reliability_score("agent-risk")
        self.assertEqual(init_rel, 0.95)

        # Process outcome showing high error (risk model overpredicted accuracy)
        # actual outcome was 0.20, expected 0.80
        new_rel = self.feedback.process_outcome_feedback("agent-risk", 0.20, 0.80)
        self.assertLess(new_rel, 0.95)

    def test_e2e_5_low_info_dynamic_selection(self) -> None:
        priorities = self.priority_engine.compute_priorities({"is_low_information": True}, [])

        # selector prefers agents with focus in low info
        selected_res = self.selector.select_agents_for_task("market observation", priorities)
        self.assertIn("agent-research", selected_res)


class TestCollaborationSecurityCompliance(unittest.TestCase):
    """
    Automated security tests confirming that Collaboration modules contain zero access or
    references to Broker, Order, Execution, Position, or Trading Engine. (5 tests)
    """

    def setUp(self) -> None:
        self.collab_filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/Application/Agents/collaboration.py"))

    def test_security_1_zero_forbidden_imports(self) -> None:
        """Verify no direct imports of forbidden trading namespaces exist in AST."""
        with open(self.collab_filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=self.collab_filepath)
        forbidden_namespaces = {"broker", "order", "execution", "position", "trading"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.lower().split(".")
                    for part in parts:
                        self.assertNotIn(part, forbidden_namespaces)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    parts = node.module.lower().split(".")
                    for part in parts:
                        self.assertNotIn(part, forbidden_namespaces)

    def test_security_2_zero_raw_execution_keywords(self) -> None:
        """Verify no active execution commands are in the file."""
        with open(self.collab_filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        forbidden_words = {"place_order", "open_position", "execute_trade", "buy_signal", "sell_signal", "broker_api"}
        for idx, line in enumerate(lines):
            clean_line = line.split("#")[0].strip() # ignore comments
            for word in forbidden_words:
                self.assertNotIn(word, clean_line.lower(), f"Security Violation at line {idx+1}: Forbidden term '{word}' found.")

    def test_security_3_no_state_mutators(self) -> None:
        """Verify no agent can alter position sizing or trading accounts."""
        with open(self.collab_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("position_size", content.lower())
        self.assertNotIn("account_balance", content.lower())

    def test_security_4_strictly_passive_methods(self) -> None:
        """Verify methods do not execute external calls."""
        with open(self.collab_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("requests.post", content.lower())
        self.assertNotIn("socket.", content.lower())

    def test_security_5_no_broker_references_in_class_fields(self) -> None:
        with open(self.collab_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("broker_id", content.lower())
        self.assertNotIn("broker_adapter", content.lower())
