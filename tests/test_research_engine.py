import unittest
from datetime import datetime, timedelta

from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Data.Adapters.adapters import HistoricalDataAdapter, DatasetRepository, MarketDataLoader
from src.Research.Features.models import FeatureValue, MarketFeatureSet
from src.Research.Features.pipeline import FeaturePipeline
from src.Research.Engine.models import PatternObservation, ResearchReport
from src.Research.Engine.services import (
    ObservationAnalyzer,
    PatternDetector,
    InsightGenerator,
    ResearchReportBuilder,
    ResearchEngine
)
from src.Research.MarketAnalysis.Models.models import ResearchRequest
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine

from src.Application.Pipeline import (
    IntelligencePipeline,
    PipelineContext,
    PipelineConfig
)
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionState, DecisionReason


# Mock/Spies for Pipeline integration
class SpyStrategyEvaluator(IStrategyEvaluator):
    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        score = StrategyScore(OverallScore=0.82, Confidence=0.91, Criteria={})
        return StrategyEvaluation(StrategyId=candidate.Id, Score=score, EvaluationNotes="Evolved notes", EvaluatedAt=datetime.now())


class SpyRiskEngine(IRiskEngine):
    def analyze_risk(self, weights: dict, profile: RiskProfile) -> RiskAssessment:
        metrics = PortfolioRisk(ExpectedVolatility=0.12, HistoricalDrawdown=0.04, VaR=0.01)
        return RiskAssessment(IsApproved=True, RiskProfileName=profile.RiskToleranceLevel, PortfolioRiskMetrics=metrics, AssessmentNotes="Risk OK", AssessedAt=datetime.now())


class SpyDecisionEngine(IDecisionEngine):
    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        reason = DecisionReason(AnalysisSummary="Decision analysis", RiskAuditStatus="PASSED", ConfidenceScore=0.93)
        return DecisionResult(DecisionId="dec-evolved", Context=context, State=DecisionState.APPROVED, Reason=reason, CreatedAt=datetime.now())


class TestResearchEngine(unittest.TestCase):

    def setUp(self):
        self.base_time = datetime(2026, 3, 1, 12, 0, 0)
        self.analyzer = ObservationAnalyzer()
        self.detector = PatternDetector()
        self.generator = InsightGenerator()
        self.builder = ResearchReportBuilder()
        self.engine = ResearchEngine(self.analyzer, self.detector, self.generator, self.builder)

        # Create a mock MarketFeatureSet
        self.feature_set = MarketFeatureSet(
            AssetId="BTCUSD",
            StartTime=self.base_time,
            EndTime=self.base_time + timedelta(hours=4),
            Features={
                "rolling_volatility": FeatureValue("rolling_volatility", 0.35, self.base_time),
                "volatility_state": FeatureValue("volatility_state", "high", self.base_time),
                "trend_strength_classification": FeatureValue("trend_strength_classification", "strong_bullish", self.base_time),
                "percentage_return": FeatureValue("percentage_return", 0.08, self.base_time),
                "range_expansion": FeatureValue("range_expansion", 1.35, self.base_time)
            }
        )

    def test_feature_set_analysis(self):
        """Test 1: Feature set analysis and observation generation."""
        observations = self.analyzer.analyze_features(self.feature_set)

        self.assertTrue(len(observations) >= 3)
        conditions = {obs.Observations.get("condition") for obs in observations}

        self.assertIn("Increasing Volatility State", conditions)
        self.assertIn("Stable Trend Behavior", conditions)
        self.assertIn("Market Transition Condition", conditions)

        # Verify property values
        for obs in observations:
            self.assertEqual(obs.Asset, "BTCUSD")
            self.assertEqual(obs.asset, "BTCUSD")
            self.assertEqual(obs.Source, "ObservationAnalyzer")

    def test_pattern_detection(self):
        """Test 2: Pattern detection and PatternObservation generation."""
        observations = self.analyzer.analyze_features(self.feature_set)
        patterns = self.detector.detect_patterns(observations, self.feature_set)

        self.assertTrue(len(patterns) >= 2)
        pattern_names = {p.PatternName for p in patterns}

        # Volatility expansion breakout pattern matches conditions: Increasing Volatility State and Market Transition Condition
        self.assertIn("Volatility Expansion Breakthrough Pattern", pattern_names)
        self.assertIn("Strong Directional Momentum Pattern", pattern_names)

        # Check a specific pattern structure
        breakout = [p for p in patterns if p.PatternName == "Volatility Expansion Breakthrough Pattern"][0]
        self.assertEqual(breakout.confidence, 0.85)
        self.assertEqual(breakout.MatchedFeatures, ["rolling_volatility", "range_expansion"])
        self.assertTrue(breakout.Metadata.get("regime_shift"))

    def test_insight_generation(self):
        """Test 3: Insight generation from patterns and observations."""
        observations = self.analyzer.analyze_features(self.feature_set)
        patterns = self.detector.detect_patterns(observations, self.feature_set)
        insights = self.generator.generate_insights(observations, patterns)

        self.assertTrue(len(insights) >= 2)
        categories = {ins.Category for ins in insights}

        self.assertIn("VolatilityState", categories)
        self.assertIn("TrendAnalysis", categories)

        vol_insight = [ins for ins in insights if ins.Category == "VolatilityState"][0]
        self.assertEqual(vol_insight.Confidence, 0.85)
        self.assertIn("breakout", vol_insight.Description.lower())

    def test_research_report_generation(self):
        """Test 4: Complete research report construction by ResearchReportBuilder."""
        observations = self.analyzer.analyze_features(self.feature_set)
        patterns = self.detector.detect_patterns(observations, self.feature_set)
        insights = self.generator.generate_insights(observations, patterns)

        report = self.builder.build_report(
            asset_id="BTCUSD",
            start_time=self.base_time,
            end_time=self.base_time + timedelta(hours=4),
            observations=observations,
            patterns=patterns,
            insights=insights,
            metadata={"source_data": "Synthetic In-Memory Feed"}
        )

        self.assertTrue(report.ReportId.startswith("rpt-BTCUSD-"))
        self.assertEqual(report.AssetId, "BTCUSD")
        self.assertEqual(report.asset_id, "BTCUSD")
        self.assertEqual(report.StartTime, self.base_time)
        self.assertEqual(report.EndTime, self.base_time + timedelta(hours=4))
        self.assertEqual(report.Observations, observations)
        self.assertEqual(report.Patterns, patterns)
        self.assertEqual(report.Insights, insights)
        self.assertEqual(report.Metadata.get("source_data"), "Synthetic In-Memory Feed")
        self.assertIsNotNone(report.GeneratedAt)

    def test_end_to_end_pipeline_integration(self):
        """Test 5: Evolve pipeline integration. Features successfully reach Research layer and produce report."""
        repo = DatasetRepository()
        loader = MarketDataLoader()
        adapter = HistoricalDataAdapter(repo, loader)

        csv_content = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T09:00:00,100.0,102.0,99.0,101.0,10000.0,AAPL\n"
            "2026-03-01T10:00:00,101.0,103.0,100.0,102.0,11000.0,AAPL\n"
            "2026-03-01T11:00:00,102.0,105.0,101.0,104.0,12000.0,AAPL\n"
            "2026-03-01T12:00:00,104.0,106.0,103.5,105.5,13000.0,AAPL\n"
            "2026-03-01T13:00:00,105.5,108.0,105.0,107.0,14000.0,AAPL\n"
        )
        adapter.load_and_register_dataset(
            dataset_id="AAPL-E2E",
            name="AAPL",
            asset_id="AAPL",
            timeframe="H1",
            source=csv_content,
            format="CSV",
            is_filepath=False
        )

        # Set up pipeline where feature extraction research engine wraps our new evolved ResearchEngine
        feature_pipeline = FeaturePipeline()
        base_research_engine = self.engine
        research_engine = FeatureExtractionResearchEngine(
            data_provider=adapter,
            base_engine=base_research_engine,
            feature_pipeline=feature_pipeline
        )

        pipeline = IntelligencePipeline(
            data_provider=adapter,
            research_engine=research_engine,
            strategy_evaluator=SpyStrategyEvaluator(),
            risk_engine=SpyRiskEngine(),
            decision_engine=SpyDecisionEngine()
        )

        # Request
        context = PipelineContext(
            StartTime=datetime(2026, 3, 1, 13, 0, 0),
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=RiskProfile("Aggressive", 1.0, 0.95)
        )

        # Run pipeline
        result = pipeline.execute(context)

        # Confirm that report structure has successfully compiled inside the research findings
        findings = result.Research.Findings
        self.assertEqual(findings["asset_id"], "AAPL")
        self.assertIn("report_id", findings)
        self.assertTrue(findings["observations_count"] >= 1)
        self.assertTrue(findings["patterns_count"] >= 1)
        self.assertTrue(findings["insights_count"] >= 1)

        # Verify specific patterns detected
        patterns_list = [p["name"] for p in findings["patterns"]]
        self.assertIn("Strong Directional Momentum Pattern", patterns_list)

        # Verify confidence score is correctly computed
        self.assertTrue(result.Research.ConfidenceScore > 0.0)

    def test_simulation_safety(self):
        """Test 6: Safety verification. Assert no order execution hooks or trade signals can be emitted."""
        forbidden_terms = [
            "buy_signal", "sell_signal", "execute_order", "place_order", "broker_connection",
            "position_tracker", "order_generator", "buy_price", "sell_price"
        ]

        engine_attrs = dir(self.engine) + dir(self.analyzer) + dir(self.detector) + dir(self.generator) + dir(self.builder)
        for attr in engine_attrs:
            for term in forbidden_terms:
                self.assertFalse(
                    term in attr.lower(),
                    f"Safety Violation: Forbidden trading term '{term}' found in Research Engine attributes."
                )

    def test_invalid_input_handling(self):
        """Test 7: Safe failure on invalid/missing feature sets."""
        request = ResearchRequest(
            Asset="AAPL",
            StartTime=self.base_time,
            EndTime=self.base_time + timedelta(hours=4),
            Context={}  # Empty context (missing market_feature_set)
        )

        with self.assertRaises(ValidationException) as context:
            self.engine.analyze_market(request)
        self.assertIn("MarketFeatureSet is missing", str(context.exception))
