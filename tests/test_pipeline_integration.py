import unittest
from datetime import datetime, timedelta
from src.Application.Pipeline import (
    IntelligencePipeline,
    PipelineContext,
    PipelineResult,
    PipelineConfig
)
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionState, DecisionReason
from src.Learning.Interfaces.interfaces import ILearningEngine
from src.Learning.Models.models import LearningFeedback


class SpyMarketDataProvider(IMarketDataProvider):
    def __init__(self):
        self.received_request = None

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        self.received_request = request
        dummy_point = MarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=10000.0
        )
        return MarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )


class SpyResearchEngine(IResearchEngine):
    def __init__(self):
        self.received_request = None

    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        self.received_request = request
        return ResearchResult(
            Request=request,
            Findings={"status": "completed", "bars_count": request.Context.get("bars_count", 0)},
            ConfidenceScore=0.88,
            CreatedAt=datetime.now()
        )


class SpyStrategyEvaluator(IStrategyEvaluator):
    def __init__(self):
        self.received_candidate = None

    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        self.received_candidate = candidate
        score = StrategyScore(
            OverallScore=0.85,
            Confidence=0.90,
            Criteria={EvaluationCriteria.STABILITY: 0.85}
        )
        return StrategyEvaluation(
            StrategyId=candidate.Id,
            Score=score,
            EvaluationNotes=f"Evaluated {candidate.Name}",
            EvaluatedAt=datetime.now()
        )


class SpyRiskEngine(IRiskEngine):
    def __init__(self):
        self.received_weights = None
        self.received_profile = None

    def analyze_risk(self, weights: dict, profile: RiskProfile) -> RiskAssessment:
        self.received_weights = weights
        self.received_profile = profile
        metrics = PortfolioRisk(
            ExpectedVolatility=0.12,
            HistoricalDrawdown=0.05,
            VaR=0.03
        )
        return RiskAssessment(
            IsApproved=True,
            RiskProfileName=profile.RiskToleranceLevel,
            PortfolioRiskMetrics=metrics,
            AssessmentNotes="Safe, approved",
            AssessedAt=datetime.now()
        )


class SpyDecisionEngine(IDecisionEngine):
    def __init__(self):
        self.received_context = None

    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        self.received_context = context
        reason = DecisionReason(
            AnalysisSummary="Approved allocation",
            RiskAuditStatus="PASSED",
            ConfidenceScore=0.95
        )
        return DecisionResult(
            DecisionId="dec-12345",
            Context=context,
            State=DecisionState.APPROVED,
            Reason=reason,
            CreatedAt=datetime.now()
        )


class SpyLearningEngine(ILearningEngine):
    def __init__(self):
        self.received_feedback = None

    def process_feedback(self, feedback: LearningFeedback) -> None:
        self.received_feedback = feedback

    def generate_suggestions(self):
        return []


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.data_provider = SpyMarketDataProvider()
        self.research_engine = SpyResearchEngine()
        self.strategy_evaluator = SpyStrategyEvaluator()
        self.risk_engine = SpyRiskEngine()
        self.decision_engine = SpyDecisionEngine()
        self.learning_engine = SpyLearningEngine()
        self.config = PipelineConfig(
            SimulationMode=True,
            LookbackDays=7,
            DefaultOutcomeMetric=0.12
        )
        self.pipeline = IntelligencePipeline(
            data_provider=self.data_provider,
            research_engine=self.research_engine,
            strategy_evaluator=self.strategy_evaluator,
            risk_engine=self.risk_engine,
            decision_engine=self.decision_engine,
            learning_engine=self.learning_engine,
            config=self.config
        )

    def test_pipeline_execution_simulation_mode_only(self):
        """Verify pipeline strictly enforces execution simulation mode only."""
        unsafe_config = PipelineConfig(SimulationMode=False)
        unsafe_pipeline = IntelligencePipeline(
            data_provider=self.data_provider,
            research_engine=self.research_engine,
            strategy_evaluator=self.strategy_evaluator,
            risk_engine=self.risk_engine,
            decision_engine=self.decision_engine,
            learning_engine=self.learning_engine,
            config=unsafe_config
        )

        now = datetime.now()
        profile = RiskProfile("Low", 1.0, 0.90)
        context = PipelineContext(
            StartTime=now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile
        )

        with self.assertRaises(ValueError) as ctx:
            unsafe_pipeline.execute(context)
        self.assertIn("strictly restricted to simulation mode only", str(ctx.exception))

    def test_pipeline_unidirectional_data_flow(self):
        """Verify end-to-end data flow and correct propagation across all modules."""
        now = datetime.now()
        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=now,
            Asset="BTCUSD",
            Timeframe="M15",
            TargetRiskProfile=profile,
            Metadata={"ActualOutcomeMetric": 0.18}
        )

        result = self.pipeline.execute(context)

        # 1. Verify Market data enters pipeline
        self.assertIsNotNone(self.data_provider.received_request)
        self.assertEqual(self.data_provider.received_request.Asset, "BTCUSD")
        self.assertEqual(self.data_provider.received_request.Timeframe, "M15")
        self.assertEqual(
            self.data_provider.received_request.StartTime,
            now - timedelta(days=self.config.LookbackDays)
        )

        # 2. Verify Research receives data
        self.assertIsNotNone(self.research_engine.received_request)
        self.assertEqual(self.research_engine.received_request.Asset, "BTCUSD")
        self.assertEqual(self.research_engine.received_request.Context.get("bars_count"), 1)

        # 3. Verify Strategy evaluation receives research output
        self.assertIsNotNone(self.strategy_evaluator.received_candidate)
        self.assertEqual(self.strategy_evaluator.received_candidate.Name, "Pipeline Momentum Concept")
        self.assertEqual(
            self.strategy_evaluator.received_candidate.ResearchContext.get("status"),
            "completed"
        )
        self.assertEqual(
            self.strategy_evaluator.received_candidate.ResearchContext.get("bars_count"),
            1
        )

        # 4. Verify Risk receives evaluation
        self.assertIsNotNone(self.risk_engine.received_weights)
        self.assertIn("BTCUSD", self.risk_engine.received_weights)
        self.assertEqual(self.risk_engine.received_weights["BTCUSD"], 0.85)
        self.assertEqual(self.risk_engine.received_profile, profile)

        # 5. Verify Decision engine produces DecisionResult
        self.assertIsNotNone(self.decision_engine.received_context)
        self.assertEqual(self.decision_engine.received_context.StrategyId, "cand-BTCUSD")
        self.assertEqual(self.decision_engine.received_context.AssetWeights["BTCUSD"], 0.85)
        self.assertEqual(result.Decision.State, DecisionState.APPROVED)

        # 6. Verify Learning receives feedback
        self.assertIsNotNone(self.learning_engine.received_feedback)
        self.assertEqual(self.learning_engine.received_feedback.DecisionId, "dec-12345")
        self.assertEqual(self.learning_engine.received_feedback.ActualOutcomeMetric, 0.18)

        # 7. Check final PipelineResult
        self.assertEqual(result.Context, context)
        self.assertEqual(result.MarketData.Request.Asset, "BTCUSD")
        self.assertEqual(result.Research.ConfidenceScore, 0.88)
        self.assertEqual(result.Strategy.Score.OverallScore, 0.85)
        self.assertTrue(result.Risk.IsApproved)
        self.assertEqual(result.Feedback, self.learning_engine.received_feedback)
