import unittest
from datetime import datetime, timedelta

from src.Infrastructure.exceptions import ValidationException
from src.Learning.Optimization import (
    LearningFeedbackRecord,
    FeedbackAnalysis,
    LearningPerformanceRecord,
    LearningQualityMetrics,
    OptimizationReport,
    FeedbackAnalyzer,
    PerformanceTracker,
    ImprovementEngine,
    LearningMemory,
    OptimizationReportBuilder,
    LearningProcessor
)
from src.Decision.Models.models import DecisionState
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Decision.Intelligence import DecisionEngine
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext, PipelineConfig
from src.Risk.Models.models import RiskProfile


class TestLearningOptimization(unittest.TestCase):
    """
    Unit and integration test suite for Phase 19: Learning & Optimization Intelligence Foundation.
    """

    def setUp(self) -> None:
        self.processor = LearningProcessor()
        self.now = datetime.now()

        # Build standard reusable inputs
        self.feedback_good = LearningFeedbackRecord(
            DecisionReference="dec-111",
            AnalysisContext={"risk_approved": True, "insights_count": 3},
            ExpectedQuality=0.85,
            ObservedResult=0.82,  # Close to expected -> strength
            ConfidenceInformation=0.90,
            Timestamp=self.now,
            Metadata={"asset": "AAPL"}
        )

        self.feedback_poor = LearningFeedbackRecord(
            DecisionReference="dec-222",
            AnalysisContext={"risk_approved": False, "insights_count": 0},
            ExpectedQuality=0.90,
            ObservedResult=0.30,  # Extreme deviation -> weakness
            ConfidenceInformation=0.95,
            Timestamp=self.now,
            Metadata={"asset": "AAPL"}
        )

    def test_1_feedback_processing(self) -> None:
        """Test 1: Feedback processing. Expected: Feedback analyzed successfully."""
        analysis = self.processor.analyzer.analyze_feedback(self.feedback_good)

        self.assertIsNotNone(analysis)
        self.assertIsInstance(analysis, FeedbackAnalysis)
        self.assertIn("High confidence tracking accuracy.", analysis.Strengths)
        self.assertEqual(len(analysis.Weaknesses), 0)

    def test_2_performance_tracking(self) -> None:
        """Test 2: Performance tracking. Expected: Performance record created."""
        tracker = PerformanceTracker()
        tracker.log_metric("DecisionConsistency", 0.95, self.now)

        record = tracker.get_record("DecisionConsistency")
        self.assertIsNotNone(record)
        self.assertIsInstance(record, LearningPerformanceRecord)
        self.assertEqual(len(record.HistoricalValues), 1)
        self.assertIn(self.now, record.HistoricalValues)
        self.assertEqual(record.HistoricalValues[self.now], 0.95)

    def test_3_improvement_generation(self) -> None:
        """Test 3: Improvement generation. Expected: Suggestions generated."""
        analyzer = FeedbackAnalyzer()
        tracker = PerformanceTracker()
        engine = ImprovementEngine()

        # Process poor feedback containing risk and confidence issues
        analysis = analyzer.analyze_feedback(self.feedback_poor)
        suggestions = engine.generate_suggestions([analysis], tracker)

        self.assertGreater(len(suggestions), 0)
        # Ensure we got suggestions for specific issues found
        reasons = [s.Reasoning.lower() for s in suggestions]
        self.assertTrue(any("unstable" in r or "uncertainty" in r or "noise" in r for r in reasons))

    def test_4_historical_comparison(self) -> None:
        """Test 4: Historical comparison. Expected: Quality trends calculated."""
        tracker = PerformanceTracker()
        t1 = self.now - timedelta(days=2)
        t2 = self.now - timedelta(days=1)
        t3 = self.now

        tracker.log_metric("DecisionConsistency", 0.70, t1)
        tracker.log_metric("DecisionConsistency", 0.85, t2)
        tracker.log_metric("DecisionConsistency", 0.92, t3)

        trends = tracker.calculate_trends("DecisionConsistency")
        self.assertEqual(len(trends), 3)
        self.assertEqual(trends, [0.70, 0.85, 0.92])  # Chronological order

    def test_5_learning_memory(self) -> None:
        """Test 5: Learning memory. Expected: Records stored and retrieved."""
        memory = LearningMemory()
        memory.save_feedback(self.feedback_good)

        history = memory.get_feedback_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].DecisionReference, "dec-111")

    def test_6_optimization_report(self) -> None:
        """Test 6: Optimization report. Expected: Complete report generated."""
        self.processor.memory.clear()
        self.processor.process_feedback_record(self.feedback_good)

        report = self.processor.generate_optimization_report()

        self.assertIsNotNone(report)
        self.assertIsInstance(report, OptimizationReport)
        self.assertTrue(report.ReportId.startswith("opt-"))
        self.assertIsNotNone(report.IntelligenceQualityMetrics)
        self.assertTrue(0.0 <= report.IntelligenceQualityMetrics.OverallIntelligenceQuality <= 1.0)

    def test_7_invalid_feedback(self) -> None:
        """Test 7: Invalid feedback. Expected: Safe validation failure."""
        analyzer = FeedbackAnalyzer()

        # ExpectedQuality out of range
        invalid_record = LearningFeedbackRecord(
            DecisionReference="dec-invalid",
            AnalysisContext={},
            ExpectedQuality=1.5,  # Invalid (> 1.0)
            ObservedResult=0.5,
            ConfidenceInformation=0.80
        )

        with self.assertRaises(ValidationException) as ex:
            analyzer.analyze_feedback(invalid_record)
        self.assertIn("ExpectedQuality must be within range", str(ex.exception))

        # Empty DecisionReference
        invalid_ref_record = LearningFeedbackRecord(
            DecisionReference="",  # Empty
            AnalysisContext={},
            ExpectedQuality=0.8,
            ObservedResult=0.5,
            ConfidenceInformation=0.80
        )

        with self.assertRaises(ValidationException) as ex_ref:
            self.processor.process_feedback_record(invalid_ref_record)
        self.assertIn("DecisionReference cannot be empty", str(ex_ref.exception))

    def test_8_pipeline_integration(self) -> None:
        """Test 8: Pipeline integration. Expected: Decision -> Learning flow works."""
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

        profile = RiskProfile("Moderate", 1.0, 0.90)
        context = PipelineContext(
            StartTime=self.now,
            Asset="MSFT",
            Timeframe="H4",
            TargetRiskProfile=profile,
            Metadata={"ActualOutcomeMetric": 0.15}
        )

        result = pipeline.execute_advanced(context)

        # Check that result contains optimization report and feedback
        self.assertIsNotNone(result.OptimizationReport)
        self.assertIsInstance(result.OptimizationReport, OptimizationReport)
        self.assertEqual(result.Feedback.DecisionId, result.DecisionReport.ReportId)

    def test_9_simulation_safety(self) -> None:
        """Test 9: Simulation safety. Expected: Learning layer cannot execute actions."""
        # Confirm that any keyword violation in feedback record context fails immediately
        with self.assertRaises(ValidationException) as ex:
            LearningFeedbackRecord(
                DecisionReference="dec-unsafe",
                AnalysisContext={"trade_command": "place_order_now"},  # Forbidden
                ExpectedQuality=0.8,
                ObservedResult=0.5,
                ConfidenceInformation=0.80
            )
        self.assertIn("Safety Violation", str(ex.exception))

    def test_10_full_intelligence_feedback_loop(self) -> None:
        """Test 10: Full intelligence feedback loop. Expected: Decision -> Feedback -> Analysis -> Improvement works."""
        # 1. Start with a Decision
        decision_id = "dec-loop-999"

        # 2. Feed back the observed results to the processor
        record = LearningFeedbackRecord(
            DecisionReference=decision_id,
            AnalysisContext={"risk_approved": True, "insights_count": 0},  # No insights -> weak research
            ExpectedQuality=0.90,
            ObservedResult=0.20,  # poor performance compared to expected -> weak confidence
            ConfidenceInformation=0.90,
            Timestamp=self.now,
            Metadata={"asset": "AAPL"}
        )

        analysis = self.processor.process_feedback_record(record)

        # 3. Analyze feedback
        self.assertIn("Confidence overestimation detected.", analysis.Weaknesses)
        self.assertIn("Zero/Insufficient research observations.", analysis.Weaknesses)

        # 4. Generate recommendations and optimize
        report = self.processor.generate_optimization_report()

        self.assertIsNotNone(report)
        self.assertEqual(len(report.ImprovementSuggestions), 2)
        targets = [s.TargetParameter for s in report.ImprovementSuggestions]
        self.assertIn("ResearchConfidenceValidationLevel", targets)
        self.assertIn("FeatureExtractionLookback", targets)
