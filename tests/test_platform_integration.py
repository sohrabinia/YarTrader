import unittest
from datetime import datetime, timedelta
from src.Core.entities import RiskParameters
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Data.MarketData.Normalization.normalization import MarketDataNormalizer
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Data.MarketData.Normalization.quality_checker import DataQualityChecker
from src.Data.HistoricalData.Repository.repository import HistoricalDataRepository
from src.Research.MarketAnalysis.Services.services import MarketAnalysisEngine, ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator, StrategyEvaluationFramework
from src.Strategy.Models.models import StrategyCandidate, StrategyDefinition
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Risk.Models.models import RiskProfile
from src.Risk.Services.services import RiskAnalyzer, RiskAssessmentFramework
from src.Decision.Models.models import DecisionContext, DecisionState, DecisionReason, DecisionResult
from src.Decision.Engine.engine import DecisionEngine, DecisionReasoningFramework
from src.Learning.Services.services import LearningFramework
from src.Application.pipeline import PipelineContext, IntelligencePipeline
from src.Infrastructure.health import PlatformHealthChecker

class TestPlatformIntegration(unittest.TestCase):
    def test_end_to_end_intelligence_pipeline(self):
        """Task 2: Verify the complete IntelligencePipeline flow."""
        # Setup mock dependencies
        data_provider = MetaTrader5Provider()
        research_engine = ResearchProcessor()
        strategy_evaluator = StrategyEvaluator()
        risk_engine = RiskAnalyzer()
        decision_engine = DecisionEngine()

        pipeline = IntelligencePipeline(
            data_provider=data_provider,
            research_engine=research_engine,
            strategy_evaluator=strategy_evaluator,
            risk_engine=risk_engine,
            decision_engine=decision_engine
        )

        now = datetime.now()
        profile = RiskProfile("Low", 1.0, 0.20)
        context = PipelineContext(
            StartTime=now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile
        )

        result = pipeline.execute(context)
        self.assertIsNotNone(result)
        self.assertEqual(result.Context.Asset, "AAPL")
        self.assertEqual(result.Decision.State, DecisionState.APPROVED)
        self.assertTrue(result.Risk.IsApproved)

    def test_advanced_research_market_analysis_engine(self):
        """Task 3: Verify advanced MarketAnalysisEngine generation of observations and history."""
        engine = MarketAnalysisEngine()
        now = datetime.now()
        pts = [
            MarketDataPoint("AAPL", now - timedelta(days=2), 150.0, 155.0, 149.0, 152.0, 10000.0),
            MarketDataPoint("AAPL", now - timedelta(days=1), 152.0, 158.0, 151.0, 157.0, 12000.0),
        ]
        observations = engine.generate_observations_from_data("AAPL", pts)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].Asset, "AAPL")
        self.assertEqual(observations[0].Observations["bars_evaluated"], 2)
        self.assertTrue(observations[0].Observations["period_pct_change"] > 0)

    def test_strategy_evaluation_framework(self):
        """Task 4: Verify StrategyEvaluationFramework comparison and history."""
        framework = StrategyEvaluationFramework()
        now = datetime.now()

        # Create definitions
        def1 = StrategyDefinition("S1", "Mean Reversion", "Mean Reversion", now, "1.0", "Approved")
        def2 = StrategyDefinition("S2", "Momentum Rating", "Momentum Rating", now, "1.0", "Approved")
        framework.register_concept(def1)
        framework.register_concept(def2)
        self.assertEqual(len(framework.list_registered_concepts()), 2)

        # Compare candidates
        cand1 = StrategyCandidate("C1", "Mean Reversion", "Desc", {}, now, "Pending")
        cand2 = StrategyCandidate("C2", "Momentum Rating", "Desc", {}, now, "Pending")
        best = framework.compare_candidates([cand1, cand2])
        self.assertIsNotNone(best)

        # Record evaluation to history
        framework.evaluate_and_record(cand1)
        framework.evaluate_and_record(cand1)
        history = framework.get_evaluation_history("C1")
        self.assertEqual(len(history), 2)

    def test_risk_assessment_framework(self):
        """Task 5: Verify RiskAssessmentFramework audit history."""
        framework = RiskAssessmentFramework()
        profile = RiskProfile("Moderate", 1.2, 0.25)

        report = framework.perform_portfolio_audit({"AAPL": 0.20, "MSFT": 0.15}, profile)
        self.assertTrue(report.IsApproved)
        self.assertEqual(len(framework.list_assessment_history()), 1)
        self.assertEqual(framework.audit_leverage_exposure({"AAPL": 0.20, "MSFT": 0.15}), 0.35)

    def test_decision_reasoning_framework(self):
        """Task 6: Verify DecisionReasoningFramework multi-factor integration and override."""
        framework = DecisionReasoningFramework()
        now = datetime.now()

        # Setup inputs
        req = ResearchRequest("AAPL", now - timedelta(days=1), now, {})
        res_result = ResearchResult(req, {"price_trend": "bullish"}, 0.90, now)

        score = StrategyScore(0.85, 0.90, {EvaluationCriteria.STABILITY: 0.85})
        strat_eval = StrategyEvaluation("cand-AAPL", score, "Bullish momentum", now)

        # Test safe risk
        metrics = PortfolioRisk(0.12, 0.05, 0.03)
        risk_assess_pass = RiskAssessment(True, "Low", metrics, "Safe allocation", now)
        decision_pass = framework.reason_and_decide(res_result, strat_eval, risk_assess_pass)
        self.assertEqual(decision_pass.State, DecisionState.APPROVED)
        self.assertIn("Strategy score: 0.85", decision_pass.Reason.AnalysisSummary)

        # Test unsafe risk (should override decision to Rejected)
        risk_assess_fail = RiskAssessment(False, "Low", metrics, "Fails asset limits", now)
        decision_fail = framework.reason_and_decide(res_result, strat_eval, risk_assess_fail)
        self.assertEqual(decision_fail.State, DecisionState.REJECTED)
        self.assertIn("OVERRIDDEN to REJECTED due to failed Risk audit", decision_fail.Reason.AnalysisSummary)

    def test_learning_framework(self):
        """Task 7: Verify LearningFramework collected outcomes and optimization loops."""
        framework = LearningFramework()

        # Feed some outcomes
        framework.feed_decision_outcome("dec-123", 0.08)
        framework.feed_decision_outcome("dec-124", 0.05)
        self.assertEqual(len(framework.Collector.get_all_feedback()), 2)

        # Get suggested parameters
        suggestions = framework.retrieve_optimization_improvements()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].TargetParameter, "MaxSingleAssetExposure")
        self.assertEqual(suggestions[0].SuggestedValue, 0.25)  # standard exposure

        # Feed some high negative outcomes
        framework.feed_decision_outcome("dec-125", -0.10)
        framework.feed_decision_outcome("dec-126", -0.15)
        suggestions_neg = framework.retrieve_optimization_improvements()
        self.assertEqual(suggestions_neg[0].SuggestedValue, 0.15)  # reduced exposure

    def test_health_checks(self):
        """Task 8: Verify PlatformHealthChecker diagnostics."""
        report = PlatformHealthChecker.run_full_diagnostics()
        self.assertEqual(report["status"], "Healthy")
        self.assertEqual(report["dependencies"]["src.Application"], "OK")
