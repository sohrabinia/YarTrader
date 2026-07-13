import unittest
from datetime import datetime
from src.Application.Agents.collaboration import (
    AgentCapabilityRegistry,
    AgentGoalManager,
    AgentPriorityEngine,
    DynamicAgentSelector,
    AgentGoal
)
from src.Infrastructure.exceptions import ValidationException


class TestCoreCollaborationRegistry(unittest.TestCase):
    """
    Unit tests for AgentCapabilityRegistry, verifying capability registrations,
    tag/focus area queries, and validation. (10 tests)
    """

    def setUp(self) -> None:
        self.registry = AgentCapabilityRegistry()

    def test_registry_1_valid_registration(self) -> None:
        self.registry.register_capabilities("agent-research", ["market observation", "features"], ["macro", "crypto"])
        caps = self.registry.get_capabilities("agent-research")
        self.assertIsNotNone(caps)
        self.assertIn("market observation", caps.capabilities)
        self.assertIn("macro", caps.focus_areas)

    def test_registry_2_case_insensitivity(self) -> None:
        self.registry.register_capabilities("agent-risk", ["Risk Analysis"], ["Macro"])
        caps = self.registry.get_capabilities("agent-risk")
        self.assertIn("risk analysis", caps.capabilities)
        self.assertIn("macro", caps.focus_areas)

    def test_registry_3_missing_agent_id_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.registry.register_capabilities("", ["capabilities"], [])

    def test_registry_4_get_unregistered_returns_none(self) -> None:
        self.assertIsNone(self.registry.get_capabilities("unknown"))

    def test_registry_5_find_agents_by_capability_matches(self) -> None:
        self.registry.register_capabilities("agent-a", ["scoring", "ranking"], [])
        self.registry.register_capabilities("agent-b", ["scoring", "filtering"], [])
        matched = self.registry.find_agents_by_capability("scoring")
        self.assertEqual(len(matched), 2)
        self.assertIn("agent-a", matched)
        self.assertIn("agent-b", matched)

    def test_registry_6_find_agents_by_capability_no_match(self) -> None:
        matched = self.registry.find_agents_by_capability("unregistered-capability")
        self.assertEqual(len(matched), 0)

    def test_registry_7_find_agents_by_focus_area_matches(self) -> None:
        self.registry.register_capabilities("agent-a", [], ["equities"])
        self.registry.register_capabilities("agent-b", [], ["crypto"])
        self.registry.register_capabilities("agent-c", [], ["equities"])
        matched = self.registry.find_agents_by_focus_area("equities")
        self.assertEqual(len(matched), 2)
        self.assertIn("agent-a", matched)
        self.assertIn("agent-c", matched)

    def test_registry_8_find_agents_by_focus_area_case_insensitive(self) -> None:
        self.registry.register_capabilities("agent-a", [], ["Equities"])
        matched = self.registry.find_agents_by_focus_area("EQUITIES")
        self.assertEqual(len(matched), 1)

    def test_registry_9_find_agents_by_focus_no_match(self) -> None:
        matched = self.registry.find_agents_by_focus_area("forex")
        self.assertEqual(len(matched), 0)

    def test_registry_10_overwrite_capabilities(self) -> None:
        self.registry.register_capabilities("agent-a", ["cap1"], ["focus1"])
        self.registry.register_capabilities("agent-a", ["cap2"], ["focus2"])
        caps = self.registry.get_capabilities("agent-a")
        self.assertIn("cap2", caps.capabilities)
        self.assertNotIn("cap1", caps.capabilities)


class TestCoreCollaborationGoalManager(unittest.TestCase):
    """
    Unit tests for AgentGoalManager, verifying goal registration,
    evaluation progress tracking, and validation boundaries. (10 tests)
    """

    def setUp(self) -> None:
        self.manager = AgentGoalManager()

    def test_goals_1_add_valid_goal(self) -> None:
        goal_id = self.manager.add_goal("Risk Reduction", "portfolio_risk", 0.15, 0.8)
        self.assertTrue(goal_id.startswith("goal-"))
        goal = self.manager.get_goal(goal_id)
        self.assertIsNotNone(goal)
        self.assertEqual(goal.name, "Risk Reduction")
        self.assertEqual(goal.status, "Active")

    def test_goals_2_missing_name_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.manager.add_goal("", "metric", 0.5, 0.5)

    def test_goals_3_missing_metric_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.manager.add_goal("name", "", 0.5, 0.5)

    def test_goals_4_invalid_weight_low_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.manager.add_goal("name", "metric", 0.5, -0.1)

    def test_goals_5_invalid_weight_high_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.manager.add_goal("name", "metric", 0.5, 1.1)

    def test_goals_6_get_unregistered_returns_none(self) -> None:
        self.assertIsNone(self.manager.get_goal("unknown"))

    def test_goals_7_evaluate_goals_satisfies_threshold(self) -> None:
        g1 = self.manager.add_goal("High Accuracy", "accuracy_score", 0.80, 0.9)
        g2 = self.manager.add_goal("Low Risk", "risk_index", 0.20, 0.7)

        # Accuracy is 0.85 (>= 0.80 -> Met)
        # Risk is 0.10 (< 0.20 -> Unmet because target is to be below or above? Let's check: evaluate_goals status is Met if metric >= threshold)
        # So we test metric >= threshold
        results = self.manager.evaluate_goals({"accuracy_score": 0.85, "risk_index": 0.25})
        self.assertEqual(results[g1], "Met")
        self.assertEqual(results[g2], "Met")

    def test_goals_8_evaluate_goals_fails_threshold(self) -> None:
        g1 = self.manager.add_goal("High Accuracy", "accuracy_score", 0.80, 0.9)
        results = self.manager.evaluate_goals({"accuracy_score": 0.75})
        self.assertEqual(results[g1], "Unmet")
        goal = self.manager.get_goal(g1)
        self.assertEqual(goal.status, "Unmet")

    def test_goals_9_list_goals_complete(self) -> None:
        self.manager.add_goal("g1", "m1", 0.1, 0.1)
        self.manager.add_goal("g2", "m2", 0.2, 0.2)
        goals = self.manager.get_all_goals()
        self.assertEqual(len(goals), 2)

    def test_goals_10_multiple_evaluations(self) -> None:
        g = self.manager.add_goal("g", "m", 0.5, 0.5)
        self.assertEqual(self.manager.evaluate_goals({"m": 0.4})[g], "Unmet")
        self.assertEqual(self.manager.evaluate_goals({"m": 0.6})[g], "Met")


class TestCoreCollaborationPrioritySelector(unittest.TestCase):
    """
    Unit tests for AgentPriorityEngine and DynamicAgentSelector. (8 tests)
    """

    def setUp(self) -> None:
        self.engine = AgentPriorityEngine()
        self.registry = AgentCapabilityRegistry()
        self.selector = DynamicAgentSelector(self.registry)

    def test_priority_1_normal_regime(self) -> None:
        priorities = self.engine.compute_priorities({}, [])
        # All default to around 0.5
        self.assertEqual(priorities["agent-risk"], 0.5)
        self.assertEqual(priorities["agent-strategy"], 0.5)

    def test_priority_2_high_volatility(self) -> None:
        priorities = self.engine.compute_priorities({"volatility": 0.35}, [])
        # Volatility > 0.25 boosts risk agent priority to 0.9
        self.assertAlmostEqual(priorities["agent-risk"], 0.9)
        self.assertAlmostEqual(priorities["agent-strategy"], 0.4)

    def test_priority_3_strong_trend(self) -> None:
        priorities = self.engine.compute_priorities({"trend_strength": 0.85}, [])
        # trend strength boosts strategy agent priority to 0.8
        self.assertAlmostEqual(priorities["agent-strategy"], 0.8)

    def test_priority_4_low_information(self) -> None:
        priorities = self.engine.compute_priorities({"is_low_information": True}, [])
        # low info boosts research (0.8) and learning (0.8)
        self.assertAlmostEqual(priorities["agent-research"], 0.8)
        self.assertAlmostEqual(priorities["agent-learning"], 0.8)

    def test_priority_5_active_goals_boosting(self) -> None:
        goals = [
            AgentGoal("g1", "Accuracy Goal", "accuracy_score", 0.8, 0.8, "Unmet"),
            AgentGoal("g2", "Risk Goal", "risk_index", 0.1, 0.5, "Active")
        ]
        priorities = self.engine.compute_priorities({}, goals)
        # boosts research because of "accuracy" and risk because of "risk"
        self.assertGreater(priorities["agent-research"], 0.5)
        self.assertGreater(priorities["agent-risk"], 0.5)

    def test_selector_1_selects_correct_agents(self) -> None:
        self.registry.register_capabilities("agent-research", ["market-data"], [])
        self.registry.register_capabilities("agent-risk", ["exposure-audit"], [])

        priorities = {"agent-research": 0.8, "agent-risk": 0.2}

        # Select for market-data
        sel = self.selector.select_agents_for_task("market-data", priorities, min_priority_threshold=0.3)
        self.assertEqual(len(sel), 1)
        self.assertEqual(sel[0], "agent-research")

    def test_selector_2_filters_below_threshold(self) -> None:
        self.registry.register_capabilities("agent-research", ["market-data"], [])
        priorities = {"agent-research": 0.2}
        sel = self.selector.select_agents_for_task("market-data", priorities, min_priority_threshold=0.3)
        self.assertEqual(len(sel), 0)

    def test_selector_3_sorts_by_priority(self) -> None:
        self.registry.register_capabilities("agent-a", ["scoring"], [])
        self.registry.register_capabilities("agent-b", ["scoring"], [])
        priorities = {"agent-a": 0.4, "agent-b": 0.9}
        sel = self.selector.select_agents_for_task("scoring", priorities)
        self.assertEqual(sel, ["agent-b", "agent-a"])
