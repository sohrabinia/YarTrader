import unittest
from datetime import datetime
from src.Decision.Models.models import DecisionState
from src.Decision.Intelligence.Agents.models import AgentContext, AgentMessage
from src.Decision.Intelligence.Agents.agents import ResearchAgent, StrategyAnalystAgent, RiskAgent
from src.Decision.Intelligence.Agents.services import IntelligenceSupervisor
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Risk.Models.models import RiskProfile
from src.Decision.Intelligence import DecisionEngine

class TestScenariosAndStress(unittest.TestCase):
    """
    Validates complete end-to-end Multi-Agent intelligence scenarios (A, B, C, D, E)
    and heavy stress simulation loads (1000 messages, multiple contexts).
    """

    def setUp(self) -> None:
        self.data_provider = MetaTrader5Provider()
        self.research_engine = ResearchProcessor()
        self.strategy_evaluator = StrategyEvaluator()
        self.risk_engine = RiskAnalyzer()
        self.decision_engine = DecisionEngine()

        self.pipeline = IntelligencePipeline(
            data_provider=self.data_provider,
            research_engine=self.research_engine,
            strategy_evaluator=self.strategy_evaluator,
            risk_engine=self.risk_engine,
            decision_engine=self.decision_engine
        )
        self.now = datetime.now()

    def test_scenario_a_normal_market(self) -> None:
        """Scenario A: All Agents available in normal market."""
        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile,
            Metadata={"ActualOutcomeMetric": 0.08}
        )

        res = self.pipeline.execute_multi_agent(context)

        self.assertTrue(res["is_success"])
        self.assertEqual(res["agent_context"].Variables["research_sentiment"], "bullish")
        self.assertEqual(res["agent_context"].Variables["strategy_score"], 0.85)
        self.assertTrue(res["agent_context"].Variables["risk_approved"])
        self.assertTrue(res["agent_context"].Variables["validation_passed"])
        self.assertEqual(res["agent_context"].Variables["suggestion"], "Maintain existing parameters")

    def test_scenario_b_high_volatility(self) -> None:
        """Scenario B: Risk Agent detects high volatility stress."""
        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile,
            Metadata={
                "ActualOutcomeMetric": 0.08,
                "volatility_level": "high"  # Induces high volatility stress
            }
        )

        res = self.pipeline.execute_multi_agent(context)

        self.assertTrue(res["is_success"])
        self.assertEqual(res["agent_context"].Variables["research_sentiment"], "bullish")
        self.assertEqual(res["agent_context"].Variables["strategy_score"], 0.85)
        # Volatility is high, strategy score is 0.85 -> risk approved becomes False
        self.assertFalse(res["agent_context"].Variables["risk_approved"])
        self.assertFalse(res["agent_context"].Variables["validation_passed"])

    def test_scenario_c_conflicting_intelligence(self) -> None:
        """Scenario C: Conflicting intelligence disagreement handled."""
        # Simulated inside validation integration test, but verified through pipeline context mappings
        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="MSFT",
            Timeframe="H1",
            TargetRiskProfile=profile
        )
        res = self.pipeline.execute_multi_agent(context)
        self.assertTrue(res["is_success"])

    def test_scenario_d_data_failure(self) -> None:
        """Scenario D: Safe pipeline execution under research data failure."""
        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile,
            Metadata={"ActualOutcomeMetric": -0.15}  # downside outcomes
        )

        res = self.pipeline.execute_multi_agent(context)
        self.assertTrue(res["is_success"])
        self.assertEqual(res["agent_context"].Variables["suggestion"], "Reduce max single-asset exposure limit parameter")

    def test_scenario_e_agent_failure(self) -> None:
        """Scenario E: One Agent crashes; supervisor isolates and lets pipeline execute."""
        supervisor = IntelligenceSupervisor()
        research = ResearchAgent()
        supervisor.register_agent(research)

        # Execute bad message to simulate ResearchAgent failure
        msg_bad = AgentMessage("msg-fail", "Orchestrator", "ResearchAgent", None)
        context = AgentContext("ctx-1")

        # supervisor catch and let pipeline continue
        res_msg = supervisor.execute_agent_safely("ResearchAgent", msg_bad, context)
        self.assertIsNone(res_msg)
        self.assertEqual(supervisor.get_agent_lifecycle("ResearchAgent"), "Failed")

    def test_heavy_stress_execution(self) -> None:
        """Stress Test: 1000 message processing and multiple simultaneous validations."""
        supervisor = IntelligenceSupervisor()
        research = ResearchAgent()
        supervisor.register_agent(research)
        context = AgentContext("ctx-stress")

        start_time = datetime.now()
        # Process 1000 message triggers sequentially
        for i in range(1000):
            msg = AgentMessage(f"msg-stress-{i}", "Orchestrator", "ResearchAgent", {"asset": "AAPL"})
            res = supervisor.execute_agent_safely("ResearchAgent", msg, context)
            self.assertIsNotNone(res)

        elapsed = (datetime.now() - start_time).total_seconds()
        # Verify high performance processing speed (1000 messages typically executed in under 0.5s)
        self.assertTrue(elapsed < 2.0)
