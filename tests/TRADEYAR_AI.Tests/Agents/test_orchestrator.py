import unittest
from src.Application.Agents import AIAgentOrchestrator, SDDLOrchestrator
from src.Infrastructure.exceptions import ValidationException

class TestOrchestratorSequences(unittest.TestCase):
    """
    Verifies AIAgentOrchestrator and SDDLOrchestrator execution pipelines,
    ensuring strict human review checkgates, validation constraints, and feedback loops.
    """

    def setUp(self) -> None:
        self.orchestrator = AIAgentOrchestrator()
        self.sddl = SDDLOrchestrator()

    def test_ai_agent_orchestrator_successful_flow(self) -> None:
        # 1. Goal Intake
        task_id = self.orchestrator.submit_goal("Optimize XAUUSD breakout strategy", "XAUUSD")
        self.assertIsNotNone(task_id)

        # 2. Task Router
        routed = self.orchestrator.route_task(task_id, "Optimize XAUUSD breakout strategy")
        self.assertEqual(routed["target_agent"], "StrategyAgent")

        # 3. Planner
        plan = self.orchestrator.generate_plan(task_id, routed)
        self.assertEqual(len(plan), 4)

        # 4. Specialized Agent execution
        proposed = self.orchestrator.execute_specialized_agent(task_id, plan)
        self.assertEqual(proposed["status"], "PROPOSED")

        # 5. Validation Agent
        validated = self.orchestrator.validate_proposed_changes(task_id, proposed)
        self.assertTrue(validated["is_valid"])

        # 6. Attempt memory commit before human approval (must fail / block)
        committed_pre = self.orchestrator.commit_to_memory(task_id, validated)
        self.assertFalse(committed_pre)

        # 7. Approve task via Human Approval Gate
        self.orchestrator.approve_task(task_id)

        # 8. Memory Update commit (must succeed)
        committed_post = self.orchestrator.commit_to_memory(task_id, validated)
        self.assertTrue(committed_post)

    def test_ai_agent_orchestrator_validation_rejection_on_execution_leakage(self) -> None:
        task_id = self.orchestrator.submit_goal("Generate high quality research", "XAUUSD")

        # Inject forbidden term 'place_order' to simulate active execution leakage
        malicious_propose = {
            "task_id": task_id,
            "agent_output": "I will execute_trade and place_order now.",
            "status": "PROPOSED"
        }

        with self.assertRaises(ValidationException) as ex:
            self.orchestrator.validate_proposed_changes(task_id, malicious_propose)

        self.assertIn("Safety Rejection", str(ex.exception))

    def test_sddl_sandboxed_loop_iteration(self) -> None:
        iteration = self.sddl.run_sddl_iteration("Re-evaluate pattern similar outcomes", "XAUUSD")
        self.assertIsNotNone(iteration["iteration_id"])
        self.assertEqual(iteration["asset"], "XAUUSD")
        self.assertEqual(iteration["action"]["task"], "Re-evaluate pattern similar outcomes")
        self.assertEqual(iteration["result"]["status"], "COMPLETED")
        self.assertEqual(iteration["evaluation"]["adherence_score"], 1.0)
        self.assertEqual(len(self.sddl.loop_history), 1)
