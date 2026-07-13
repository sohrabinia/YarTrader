import unittest
from datetime import datetime, timedelta
import math

from src.Infrastructure.exceptions import ValidationException
from src.Data.Models.models import (
    HistoricalRecord,
    DatasetMetadata,
    HistoricalDataset,
    MarketDataBatch
)
from src.Data.Adapters.adapters import (
    HistoricalDataValidator,
    MarketDataLoader,
    DatasetRepository,
    HistoricalDataAdapter
)
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataPoint, MarketDataResponse

from src.Application.Pipeline import (
    IntelligencePipeline,
    PipelineContext,
    PipelineResult,
    PipelineConfig
)
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


# Define spy/mock classes for pipeline integration tests
class SpyResearchEngine(IResearchEngine):
    def __init__(self):
        self.received_request = None

    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        self.received_request = request
        return ResearchResult(
            Request=request,
            Findings={"status": "completed", "bars_count": request.Context.get("bars_count", 0)},
            ConfidenceScore=0.9,
            CreatedAt=datetime.now()
        )


class SpyStrategyEvaluator(IStrategyEvaluator):
    def __init__(self):
        self.received_candidate = None

    def evaluate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        self.received_candidate = candidate
        score = StrategyScore(
            OverallScore=0.8,
            Confidence=0.95,
            Criteria={EvaluationCriteria.STABILITY: 0.8}
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

    def analyze_risk(self, weights: dict, profile: RiskProfile) -> RiskAssessment:
        self.received_weights = weights
        metrics = PortfolioRisk(
            ExpectedVolatility=0.10,
            HistoricalDrawdown=0.04,
            VaR=0.02
        )
        return RiskAssessment(
            IsApproved=True,
            RiskProfileName=profile.RiskToleranceLevel,
            PortfolioRiskMetrics=metrics,
            AssessmentNotes="Approved risk",
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
            ConfidenceScore=0.9
        )
        return DecisionResult(
            DecisionId="dec-historical-test",
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


class TestHistoricalDataAdapter(unittest.TestCase):

    def setUp(self):
        self.loader = MarketDataLoader()
        self.repository = DatasetRepository()
        self.adapter = HistoricalDataAdapter(self.repository, self.loader)

    def test_load_valid_csv_dataset(self):
        """Test 1: Load valid CSV dataset. Verify success and correct structural representation."""
        csv_content = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T10:00:00,100.0,105.0,98.0,102.0,15000,AAPL\n"
            "2026-03-01T11:00:00,102.0,103.0,99.5,101.5,12000,AAPL\n"
        )

        records = self.loader.load_from_csv(csv_content, is_filepath=False, asset_id_override="AAPL")
        self.assertEqual(len(records), 2)

        # Check first record details
        rec1 = records[0]
        self.assertEqual(rec1.AssetId, "AAPL")
        self.assertEqual(rec1.Open, 100.0)
        self.assertEqual(rec1.High, 105.0)
        self.assertEqual(rec1.Low, 98.0)
        self.assertEqual(rec1.Close, 102.0)
        self.assertEqual(rec1.Volume, 15000.0)
        self.assertEqual(rec1.Timestamp, datetime.fromisoformat("2026-03-01T10:00:00"))

        # Verify property access
        self.assertEqual(rec1.asset_id, "AAPL")
        self.assertEqual(rec1.timestamp, datetime.fromisoformat("2026-03-01T10:00:00"))
        self.assertEqual(rec1.open, 100.0)
        self.assertEqual(rec1.high, 105.0)
        self.assertEqual(rec1.low, 98.0)
        self.assertEqual(rec1.close, 102.0)
        self.assertEqual(rec1.volume, 15000.0)

        # Validate complete dataset structure
        metadata = DatasetMetadata(
            DatasetId="AAPL-H1-Test",
            Name="AAPL Test Dataset",
            AssetId="AAPL",
            Timeframe="H1",
            Format="CSV",
            RecordCount=len(records)
        )
        dataset = HistoricalDataset(Metadata=metadata, Records=records)
        HistoricalDataValidator.validate_dataset(dataset)

        self.assertEqual(dataset.metadata, metadata)
        self.assertEqual(dataset.records, records)
        self.assertEqual(metadata.dataset_id, "AAPL-H1-Test")
        self.assertEqual(metadata.name, "AAPL Test Dataset")
        self.assertEqual(metadata.asset_id, "AAPL")
        self.assertEqual(metadata.timeframe, "H1")
        self.assertEqual(metadata.format, "CSV")
        self.assertEqual(metadata.record_count, 2)
        self.assertIsNone(metadata.file_path)
        self.assertIsNotNone(metadata.created_at)

    def test_load_json_dataset(self):
        """Test 2: Load JSON dataset. Verify correct parsing and model conversion."""
        json_content = """
        [
            {"timestamp": "2026-03-01T12:00:00", "open": 1.0850, "high": 1.0900, "low": 1.0820, "close": 1.0870, "volume": 50000, "asset_id": "EURUSD"},
            {"timestamp": "2026-03-01T13:00:00", "open": 1.0870, "high": 1.0920, "low": 1.0860, "close": 1.0890, "volume": 60000, "asset_id": "EURUSD"}
        ]
        """
        records = self.loader.load_from_json(json_content, is_filepath=False, asset_id_override="EURUSD")
        self.assertEqual(len(records), 2)

        rec = records[1]
        self.assertEqual(rec.AssetId, "EURUSD")
        self.assertEqual(rec.Open, 1.0870)
        self.assertEqual(rec.High, 1.0920)
        self.assertEqual(rec.Low, 1.0860)
        self.assertEqual(rec.Close, 1.0890)
        self.assertEqual(rec.Volume, 60000.0)
        self.assertEqual(rec.Timestamp, datetime.fromisoformat("2026-03-01T13:00:00"))

    def test_invalid_dataset(self):
        """Test 3: Invalid dataset. Verify clear and descriptive validation failures."""
        # Case A: Corrupted/Unparseable row in CSV
        corrupted_csv = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T10:00:00,100.0,corrupted_val,98.0,102.0,15000,AAPL\n"
        )
        with self.assertRaises(ValidationException) as context:
            self.loader.load_from_csv(corrupted_csv, is_filepath=False)
        self.assertIn("Non-numeric price/volume", str(context.exception))

        # Case B: Empty dataset
        with self.assertRaises(ValidationException) as context:
            self.loader.load_from_csv("", is_filepath=False)
        self.assertIn("empty", str(context.exception).lower())

        # Case C: Logical pricing mismatch (Low > High)
        invalid_pricing_csv = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T10:00:00,100.0,105.0,108.0,102.0,15000,AAPL\n"
        )
        records = self.loader.load_from_csv(invalid_pricing_csv, is_filepath=False, asset_id_override="AAPL")
        metadata = DatasetMetadata("D1", "AAPL", "AAPL", "H1", "CSV", len(records))
        dataset = HistoricalDataset(metadata, records)

        with self.assertRaises(ValidationException) as context:
            HistoricalDataValidator.validate_dataset(dataset)
        self.assertIn("cannot be higher than High price", str(context.exception))

        # Case D: Negative price
        negative_price_csv = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T10:00:00,-5.0,105.0,98.0,102.0,15000,AAPL\n"
        )
        records2 = self.loader.load_from_csv(negative_price_csv, is_filepath=False, asset_id_override="AAPL")
        dataset2 = HistoricalDataset(metadata, records2)
        with self.assertRaises(ValidationException) as context:
            HistoricalDataValidator.validate_dataset(dataset2)
        self.assertIn("must be non-negative", str(context.exception))

        # Case E: Missing headers in CSV
        missing_headers_csv = (
            "open,high,low,close,volume\n"
            "100.0,105.0,98.0,102.0,15000\n"
        )
        with self.assertRaises(ValidationException) as context:
            self.loader.load_from_csv(missing_headers_csv, is_filepath=False)
        self.assertIn("lacks a timestamp", str(context.exception))

        # Case F: Empty dataset validation
        empty_dataset = HistoricalDataset(metadata, [])
        with self.assertRaises(ValidationException) as context:
            HistoricalDataValidator.validate_dataset(empty_dataset)
        self.assertIn("must not be empty", str(context.exception))

    def test_pipeline_integration(self):
        """Test 4: Pipeline integration. Verify clean end-to-end simulation execution."""
        # 1. Setup mock/spy services
        research_engine = SpyResearchEngine()
        strategy_evaluator = SpyStrategyEvaluator()
        risk_engine = SpyRiskEngine()
        decision_engine = SpyDecisionEngine()
        learning_engine = SpyLearningEngine()
        config = PipelineConfig(SimulationMode=True, LookbackDays=2)

        # 2. Instantiate pipeline with our HistoricalDataAdapter
        pipeline = IntelligencePipeline(
            data_provider=self.adapter,
            research_engine=research_engine,
            strategy_evaluator=strategy_evaluator,
            risk_engine=risk_engine,
            decision_engine=decision_engine,
            learning_engine=learning_engine,
            config=config
        )

        # 3. Register a valid dataset
        csv_content = (
            "timestamp,open,high,low,close,volume,asset_id\n"
            "2026-03-01T00:00:00,100.0,105.0,98.0,102.0,15000,AAPL\n"
            "2026-03-02T00:00:00,102.0,106.0,101.0,105.0,16000,AAPL\n"
            "2026-03-03T00:00:00,105.0,110.0,104.0,109.0,17000,AAPL\n"
        )
        self.adapter.load_and_register_dataset(
            dataset_id="AAPL-DAILY-CSV",
            name="AAPL Daily",
            asset_id="AAPL",
            timeframe="D1",
            source=csv_content,
            format="CSV",
            is_filepath=False
        )

        # Retrieve and verify list_datasets & retrieve_market_data_batch
        datasets = self.repository.list_datasets()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].DatasetId, "AAPL-DAILY-CSV")

        batch = self.adapter.retrieve_market_data_batch("AAPL")
        self.assertEqual(batch.asset_id, "AAPL")
        self.assertEqual(len(batch.records), 3)

        # 4. Define active PipelineContext
        # Request data forAAPL looking back from March 3, 2026
        now = datetime.fromisoformat("2026-03-03T00:00:00")
        profile = RiskProfile("Conservative", 1.0, 0.95)
        context = PipelineContext(
            StartTime=now,
            Asset="AAPL",
            Timeframe="D1",
            TargetRiskProfile=profile,
            Metadata={"ActualOutcomeMetric": 0.08}
        )

        # 5. Execute pipeline
        result = pipeline.execute(context)

        # 6. Verify result parameters
        self.assertEqual(result.Context, context)
        self.assertEqual(result.MarketData.Request.Asset, "AAPL")

        # Lookback is 2 days, so request StartTime is March 1.
        # Data points should span March 1 00:00 to March 3 00:00.
        # The registered dataset points match these times, so we should get all 3 points.
        self.assertEqual(len(result.MarketData.DataPoints), 3)
        self.assertEqual(result.MarketData.DataPoints[0].Close, 102.0)
        self.assertEqual(result.MarketData.DataPoints[1].Close, 105.0)
        self.assertEqual(result.MarketData.DataPoints[2].Close, 109.0)

        # Ensure correct conversion to domain model properties
        self.assertEqual(result.MarketData.DataPoints[0].close, 102.0)
        self.assertEqual(result.MarketData.DataPoints[0].asset_id, "AAPL")

        # Verify downstream spy receipt
        self.assertEqual(research_engine.received_request.Asset, "AAPL")
        self.assertEqual(research_engine.received_request.Context.get("bars_count"), 3)
        self.assertEqual(strategy_evaluator.received_candidate.Name, "Pipeline Momentum Concept")
        self.assertIn("AAPL", risk_engine.received_weights)
        self.assertEqual(decision_engine.received_context.StrategyId, "cand-AAPL")
        self.assertEqual(learning_engine.received_feedback.ActualOutcomeMetric, 0.08)

    def test_safety_verification(self):
        """Test 5: Safety verification. Assert no trading execution logic exists and safety checks work."""
        # A. Verify no active trading/order methods or attributes exist in the Adapter or its components.
        forbidden_terms = [
            "buy", "sell", "order", "position", "trade", "execute_order", "place_order",
            "buy_price", "sell_price", "profit_execution", "account", "broker"
        ]

        adapter_attrs = dir(self.adapter)
        for term in forbidden_terms:
            for attr in adapter_attrs:
                # Ensure we don't have methods or fields named after execution terms
                self.assertFalse(
                    term in attr.lower(),
                    f"Safety Error: Forbidden trading/execution term '{term}' found in adapter attribute '{attr}'."
                )

        # B. Verify that when integrated with the pipeline, SimulationMode is strictly enforced.
        unsafe_config = PipelineConfig(SimulationMode=False)
        research_engine = SpyResearchEngine()
        strategy_evaluator = SpyStrategyEvaluator()
        risk_engine = SpyRiskEngine()
        decision_engine = SpyDecisionEngine()
        learning_engine = SpyLearningEngine()

        pipeline = IntelligencePipeline(
            data_provider=self.adapter,
            research_engine=research_engine,
            strategy_evaluator=strategy_evaluator,
            risk_engine=risk_engine,
            decision_engine=decision_engine,
            learning_engine=learning_engine,
            config=unsafe_config
        )

        now = datetime.now()
        profile = RiskProfile("High", 1.0, 0.95)
        context = PipelineContext(
            StartTime=now,
            Asset="AAPL",
            Timeframe="H1",
            TargetRiskProfile=profile
        )

        # Execute should fail with ValueError on SimulationMode=False
        with self.assertRaises(ValueError) as context_manager:
            pipeline.execute(context)
        self.assertIn("strictly restricted to simulation mode only", str(context_manager.exception))
