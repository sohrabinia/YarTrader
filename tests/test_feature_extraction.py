import unittest
from datetime import datetime, timedelta
import math

from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest, MarketDataResponse
from src.Data.Adapters.adapters import HistoricalDataAdapter, DatasetRepository, MarketDataLoader
from src.Research.Features.models import FeatureDefinition, FeatureValue, MarketFeatureSet
from src.Research.Features.calculators import (
    PriceFeatureCalculator,
    VolatilityFeatureCalculator,
    TrendFeatureCalculator,
    StatisticalFeatureCalculator
)
from src.Research.Features.pipeline import FeaturePipeline
from src.Research.Features.registry import FeatureRegistry
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine, ResearchProcessor
from src.Research.MarketAnalysis.Models.models import ResearchRequest

from src.Application.Pipeline import (
    IntelligencePipeline,
    PipelineContext,
    PipelineConfig
)
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionState, DecisionReason


# Mock spies for testing
class SpyStrategyEvaluator(IStrategyEvaluator):
    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        score = StrategyScore(OverallScore=0.75, Confidence=0.88, Criteria={})
        return StrategyEvaluation(StrategyId=candidate.Id, Score=score, EvaluationNotes="", EvaluatedAt=datetime.now())


class SpyRiskEngine(IRiskEngine):
    def analyze_risk(self, weights: dict, profile: RiskProfile) -> RiskAssessment:
        metrics = PortfolioRisk(ExpectedVolatility=0.15, HistoricalDrawdown=0.05, VaR=0.02)
        return RiskAssessment(IsApproved=True, RiskProfileName=profile.RiskToleranceLevel, PortfolioRiskMetrics=metrics, AssessmentNotes="", AssessedAt=datetime.now())


class SpyDecisionEngine(IDecisionEngine):
    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        reason = DecisionReason(AnalysisSummary="Pass", RiskAuditStatus="PASSED", ConfidenceScore=0.9)
        return DecisionResult(DecisionId="dec-id", Context=context, State=DecisionState.APPROVED, Reason=reason, CreatedAt=datetime.now())


class TestFeatureExtraction(unittest.TestCase):

    def setUp(self):
        # Create standard synthetic market data points for AAPL
        self.base_time = datetime(2026, 3, 1, 9, 0, 0)
        self.data_points = [
            MarketDataPoint("AAPL", self.base_time + timedelta(hours=0), 100.0, 102.0, 99.0, 101.0, 10000.0),
            MarketDataPoint("AAPL", self.base_time + timedelta(hours=1), 101.0, 103.0, 100.0, 102.0, 11000.0),
            MarketDataPoint("AAPL", self.base_time + timedelta(hours=2), 102.0, 105.0, 101.0, 104.0, 12000.0),
            MarketDataPoint("AAPL", self.base_time + timedelta(hours=3), 104.0, 106.0, 103.5, 105.5, 13000.0),
            MarketDataPoint("AAPL", self.base_time + timedelta(hours=4), 105.5, 108.0, 105.0, 107.0, 14000.0),
        ]

    def test_basic_feature_calculation(self):
        """Test 1: Basic feature calculation and MarketFeatureSet generation."""
        registry = FeatureRegistry()
        pipeline = FeaturePipeline(registry)

        feature_set = pipeline.execute(self.data_points)

        self.assertEqual(feature_set.AssetId, "AAPL")
        self.assertEqual(feature_set.StartTime, self.base_time)
        self.assertEqual(feature_set.EndTime, self.base_time + timedelta(hours=4))
        self.assertIn("price_change", feature_set.Features)
        self.assertIn("percentage_return", feature_set.Features)
        self.assertIn("price_range", feature_set.Features)

        # Confirm exact calculations
        # price_change: 107.0 - 101.0 = 6.0
        self.assertAlmostEqual(feature_set.Features["price_change"].Value, 6.0)
        # percentage_return: (107.0 - 101.0) / 101.0 = 0.05940594
        self.assertAlmostEqual(feature_set.Features["percentage_return"].Value, 6.0 / 101.0)
        # price_range: max_high (108.0) - min_low (99.0) = 9.0
        self.assertAlmostEqual(feature_set.Features["price_range"].Value, 9.0)

    def test_volatility_calculation(self):
        """Test 2: Volatility calculations including range expansion and state classification."""
        calc = VolatilityFeatureCalculator()
        values = calc.calculate(self.data_points)

        # Index them by name
        val_map = {v.FeatureName: v for v in values}

        self.assertIn("rolling_volatility", val_map)
        self.assertIn("range_expansion", val_map)
        self.assertIn("volatility_state", val_map)

        # Rolling volatility should be a valid non-negative float
        vol = val_map["rolling_volatility"].Value
        self.assertTrue(vol >= 0.0)

        # Range expansion should be correctly calculated
        # ranges: [3, 3, 4, 2.5, 3]. avg = 15.5 / 5 = 3.1
        # latest_range: 108.0 - 105.0 = 3.0
        # range_expansion = 3.0 / 3.1 = 0.96774
        self.assertAlmostEqual(val_map["range_expansion"].Value, 3.0 / 3.1)

        # Volatility state check
        state = val_map["volatility_state"].Value
        self.assertIn(state, ["low", "medium", "high"])

    def test_invalid_data_handling(self):
        """Test 3: Graceful handling of invalid or empty datasets (safe failure)."""
        calc = PriceFeatureCalculator()

        with self.assertRaises(ValidationException) as context:
            calc.calculate([])
        self.assertIn("empty data", str(context.exception).lower())

        pipeline = FeaturePipeline()
        with self.assertRaises(ValidationException) as context:
            pipeline.execute([])
        self.assertIn("empty data", str(context.exception).lower())

    def test_pipeline_integration(self):
        """Test 4: Integration of FeatureExtractionResearchEngine with the IntelligencePipeline."""
        # Setup HistoricalDataAdapter with standard registered dataset
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
            dataset_id="AAPL-TEST-CSV",
            name="AAPL",
            asset_id="AAPL",
            timeframe="H1",
            source=csv_content,
            format="CSV",
            is_filepath=False
        )

        # Instantiate FeatureExtractionResearchEngine with the adapter
        feature_research_engine = FeatureExtractionResearchEngine(data_provider=adapter)

        # Create intelligence pipeline
        pipeline = IntelligencePipeline(
            data_provider=adapter,
            research_engine=feature_research_engine,
            strategy_evaluator=SpyStrategyEvaluator(),
            risk_engine=SpyRiskEngine(),
            decision_engine=SpyDecisionEngine()
        )

        # Context
        context = PipelineContext(
            StartTime=datetime(2026, 3, 1, 13, 0, 0),
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=RiskProfile("Moderate", 1.0, 0.90)
        )

        # Run pipeline
        result = pipeline.execute(context)

        # Confirm features correctly reached the research result findings
        self.assertIn("feature_set", result.Research.Findings)
        self.assertIn("observation_summary", result.Research.Findings)

        obs_summary = result.Research.Findings["observation_summary"]
        self.assertEqual(obs_summary["price_change"], 6.0)
        self.assertEqual(obs_summary["trend_strength_classification"], "strong_bullish")

    def test_simulation_safety(self):
        """Test 5: Safety verification. Assert no trading execution properties or BUY/SELL triggers exist."""
        forbidden_terms = [
            "buy_signal", "sell_signal", "place_order", "execute_trade", "broker_connection",
            "position_tracker", "order_generator", "buy_price", "sell_price"
        ]

        # Scan code files for forbidden execution attributes
        calculators_dir = dir(PriceFeatureCalculator) + dir(VolatilityFeatureCalculator) + dir(TrendFeatureCalculator)
        pipeline_dir = dir(FeaturePipeline) + dir(FeatureRegistry)

        all_attrs = calculators_dir + pipeline_dir
        for attr in all_attrs:
            for term in forbidden_terms:
                self.assertFalse(
                    term in attr.lower(),
                    f"Safety Violation: Forbidden trading execution term '{term}' found in feature extraction attributes."
                )
