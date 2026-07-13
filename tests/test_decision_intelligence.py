import unittest
from datetime import datetime, timedelta

from src.Infrastructure.exceptions import ValidationException
from src.Decision.Models.models import DecisionState
from src.Decision.Intelligence import (
    DecisionEngine,
    DecisionIntelligenceContext,
    DecisionContextBuilder,
    DecisionAnalyzer,
    DecisionQualityEvaluator,
    DecisionConflictResolver,
    DecisionEvidenceCollector,
    DecisionReportBuilder,
    DecisionValidator,
    DecisionHistoryStore
)
from src.Research.MarketAnalysis.Models.models import MarketInsight, ResearchRequest, ResearchResult
from src.Research.Engine.models import PatternObservation
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk

from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext, PipelineConfig


class TestDecisionIntelligence(unittest.TestCase):
    """
    Comprehensive test suite verifying the Advanced Decision Intelligence Layer (Phase 18).
    """

    def setUp(self) -> None:
        self.engine = DecisionEngine()
        self.builder = DecisionContextBuilder()
        self.analyzer = DecisionAnalyzer()
        self.evaluator = DecisionQualityEvaluator()
        self.conflict_resolver = DecisionConflictResolver()
        self.collector = DecisionEvidenceCollector()
        self.report_builder = DecisionReportBuilder()
        self.validator = DecisionValidator()
        self.history_store = DecisionHistoryStore()
        self.now = datetime.now()

        # Build reusable items
        self.insight_bullish = MarketInsight(
            Category="Trend",
            Description="Strong upward bullish momentum",
            Confidence=0.90,
            CreatedAt=self.now
        )
        self.pattern_bullish = PatternObservation(
            PatternName="Double Bottom",
            Description="Detected double bottom",
            Confidence=0.85,
            Timestamp=self.now,
            MatchedFeatures=["price"]
        )
        self.strategy_eval_high = StrategyEvaluation(
            StrategyId="strat-A",
            Score=StrategyScore(OverallScore=0.85, Confidence=0.90, Criteria={}),
            EvaluationNotes="Strong score",
            EvaluatedAt=self.now
        )
        self.risk_pass = RiskAssessment(
            IsApproved=True,
            RiskProfileName="Moderate",
            PortfolioRiskMetrics=PortfolioRisk(0.12, 0.05, 0.02),
            AssessmentNotes="Meets exposure limits",
            AssessedAt=self.now
        )

    def test_1_complete_decision_generation(self) -> None:
        """Test 1: Complete decision generation. Expected: Decision result created."""
        context = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=self.risk_pass,
            market_context={"trend": "bullish"},
            metadata={"asset": "AAPL"}
        )

        report = self.engine.evaluate_intelligence_context(context)

        self.assertIsNotNone(report)
        self.assertEqual(report.State, DecisionState.APPROVED)
        self.assertEqual(report.Context.Metadata.get("asset"), "AAPL")
        self.assertTrue(report.Confidence > 0.0)
        self.assertIsNotNone(report.QualityScore)
        self.assertFalse(report.ConflictAnalysis.ConflictDetected)

    def test_2_research_and_strategy_alignment(self) -> None:
        """Test 2: Research and strategy alignment. Expected: Higher confidence."""
        # Aligned: Positive research and high strategy score
        context_aligned = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=self.risk_pass,
            metadata={"asset": "AAPL"}
        )
        report_aligned = self.engine.evaluate_intelligence_context(context_aligned)

        # Misaligned: Positive research but low strategy score
        strategy_eval_low = StrategyEvaluation(
            StrategyId="strat-A",
            Score=StrategyScore(OverallScore=0.25, Confidence=0.90, Criteria={}),
            EvaluationNotes="Weak score",
            EvaluatedAt=self.now
        )
        context_misaligned = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=strategy_eval_low,
            risk_assessment=self.risk_pass,
            metadata={"asset": "AAPL"}
        )
        report_misaligned = self.engine.evaluate_intelligence_context(context_misaligned)

        # Aligned confidence should be strictly greater than misaligned confidence
        self.assertGreater(report_aligned.Confidence, report_misaligned.Confidence)

    def test_3_research_and_risk_conflict(self) -> None:
        """Test 3: Research and risk conflict. Expected: Conflict detected."""
        risk_fail = RiskAssessment(
            IsApproved=False,
            RiskProfileName="Moderate",
            PortfolioRiskMetrics=PortfolioRisk(0.35, 0.25, 0.15),
            AssessmentNotes="Fails exposure limits",
            AssessedAt=self.now
        )

        context = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=risk_fail,
            metadata={"asset": "AAPL"}
        )

        report = self.engine.evaluate_intelligence_context(context)

        # Expect REJECTED state since risk is rejected, and ConflictDetected should be True
        self.assertEqual(report.State, DecisionState.REJECTED)
        self.assertTrue(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.ConflictAnalysis.ConflictType, "Strategy_vs_Risk")

    def test_4_insufficient_evidence(self) -> None:
        """Test 4: Insufficient evidence. Expected: ReviewRequired state."""
        # Create context with empty research insights and strategy evaluations
        context = self.builder.build_context(
            research_output=[],
            strategy_evaluation=[],
            risk_assessment=self.risk_pass,
            market_context={"period": "daily"},
            metadata={"asset": "AAPL"}
        )

        report = self.engine.evaluate_intelligence_context(context)

        # Expect ReviewRequired state due to insufficient evidence
        self.assertEqual(report.State, DecisionState.REVIEW_REQUIRED)

    def test_5_missing_context(self) -> None:
        """Test 5: Missing context. Expected: Validation failure."""
        # Completely empty context
        empty_context = DecisionIntelligenceContext()

        with self.assertRaises(ValidationException) as ex:
            self.engine.evaluate_intelligence_context(empty_context)
        self.assertIn("Validation Error", str(ex.exception))

    def test_6_decision_quality_scoring(self) -> None:
        """Test 6: Decision quality scoring. Expected: Stable score."""
        context = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=self.risk_pass,
            metadata={"asset": "AAPL"}
        )

        report1 = self.engine.evaluate_intelligence_context(context)
        report2 = self.engine.evaluate_intelligence_context(context)

        # Scores should be identical and within [0, 1] range
        self.assertEqual(report1.QualityScore.OverallScore, report2.QualityScore.OverallScore)
        self.assertTrue(0.0 <= report1.QualityScore.OverallScore <= 1.0)
        self.assertTrue(0.0 <= report1.QualityScore.EvidenceQuality <= 1.0)
        self.assertTrue(0.0 <= report1.QualityScore.Consistency <= 1.0)
        self.assertTrue(0.0 <= report1.QualityScore.Reliability <= 1.0)

    def test_7_evidence_collection(self) -> None:
        """Test 7: Evidence collection. Expected: Complete evidence trail."""
        context = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=self.risk_pass,
            metadata={"asset": "AAPL", "features": ["high_volatility", "momentum"]}
        )

        report = self.engine.evaluate_intelligence_context(context)

        trail = report.EvidenceTrail
        self.assertIsNotNone(trail)
        self.assertEqual(len(trail.ResearchEvidence), 1)
        self.assertEqual(len(trail.StrategyEvidence), 1)
        self.assertEqual(len(trail.RiskEvidence), 1)
        self.assertEqual(trail.FeatureEvidence, ["high_volatility", "momentum"])

    def test_8_decision_history(self) -> None:
        """Test 8: Decision history. Expected: Record created."""
        context = self.builder.build_context(
            research_output=[self.insight_bullish],
            strategy_evaluation=self.strategy_eval_high,
            risk_assessment=self.risk_pass,
            metadata={"asset": "AAPL"}
        )

        self.engine.history_store.clear()
        self.assertEqual(len(self.engine.history_store.get_history()), 0)

        report = self.engine.evaluate_intelligence_context(context)

        # Record should be added to history
        history = self.engine.history_store.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].DecisionState, DecisionState.APPROVED)
        self.assertEqual(history[0].Confidence, report.Confidence)

    def test_9_simulation_safety(self) -> None:
        """Test 9: Simulation safety. Expected: Decision layer cannot execute actions."""
        # Ensure context checks for forbidden keywords and throws ValidationException
        with self.assertRaises(ValidationException) as ex:
            DecisionIntelligenceContext(
                Metadata={"broker_api_key": "abc", "orders": "place_order_here"}
            )
        self.assertIn("Safety Violation", str(ex.exception))

    def test_10_full_intelligence_chain(self) -> None:
        """Test 10: Full intelligence chain. Expected: Complete successful flow."""
        data_provider = MetaTrader5Provider()
        research_engine = ResearchProcessor()
        strategy_evaluator = StrategyEvaluator()
        risk_engine = RiskAnalyzer()
        decision_engine = self.engine  # Advanced engine

        pipeline = IntelligencePipeline(
            data_provider=data_provider,
            research_engine=research_engine,
            strategy_evaluator=strategy_evaluator,
            risk_engine=risk_engine,
            decision_engine=decision_engine
        )

        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="MSFT",
            Timeframe="H4",
            TargetRiskProfile=profile
        )

        # Run execute_advanced end-to-end
        result = pipeline.execute_advanced(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.Context.Asset, "MSFT")
        self.assertEqual(result.DecisionReport.State, DecisionState.APPROVED)
        self.assertTrue(result.Risk.IsApproved)
        self.assertTrue(result.DecisionReport.Confidence > 0.0)
        self.assertIsNotNone(result.Feedback)
