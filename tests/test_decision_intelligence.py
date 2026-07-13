import unittest
from datetime import datetime, timedelta
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Decision.Intelligence.builder import DecisionContextBuilder
from src.Decision.Intelligence.analyzer import DecisionAnalyzer, DecisionAnalysis
from src.Decision.Intelligence.evaluator import DecisionQualityEvaluator, DecisionQualityScore
from src.Decision.Intelligence.resolver import DecisionConflictResolver, ConflictResolutionResult
from src.Decision.Intelligence.evidence import DecisionEvidenceCollector, DecisionEvidenceTrail
from src.Decision.Intelligence.report import DecisionReportBuilder, DecisionIntelligenceReport
from src.Decision.Intelligence.history import DecisionHistoryRecord, DecisionValidator
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Models.models import DecisionResult
from src.Research.MarketAnalysis.Models.models import MarketInsight
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Risk.Models.models import RiskAssessment, PortfolioRisk, RiskProfile
from src.Infrastructure.exceptions import ValidationException

class TestDecisionIntelligence(unittest.TestCase):
    """
    Unit and integration tests for Phase 18 Advanced Decision Intelligence Layer.
    """

    def setUp(self) -> None:
        self.engine = DecisionEngine()
        self.builder = DecisionContextBuilder()
        self.analyzer = DecisionAnalyzer()
        self.evaluator = DecisionQualityEvaluator()
        self.resolver = DecisionConflictResolver()
        self.collector = DecisionEvidenceCollector()
        self.report_builder = DecisionReportBuilder()
        self.validator = DecisionValidator()

        self.now = datetime.now()

        # Healthy mock elements
        self.mock_insight = MarketInsight(Category="Trend", Description="Bullish Trend", Confidence=0.88, CreatedAt=self.now)
        self.mock_strategy_eval = StrategyEvaluation(
            StrategyId="strat-001",
            Score=StrategyScore(OverallScore=0.85, Confidence=0.90, Criteria={}),
            EvaluationNotes="Highly aligned",
            EvaluatedAt=self.now
        )
        self.mock_risk_assess = RiskAssessment(
            IsApproved=True,
            RiskProfileName="Moderate",
            PortfolioRiskMetrics=PortfolioRisk(ExpectedVolatility=0.15, HistoricalDrawdown=0.08, VaR=0.04),
            AssessmentNotes="Safe",
            AssessedAt=self.now
        )

        self.context = (
            self.builder
            .with_research([self.mock_insight])
            .with_strategy([self.mock_strategy_eval])
            .with_risk([self.mock_risk_assess])
            .with_market_context({"volatility": 0.18, "trend": "bullish"})
            .with_historical_evidence({"success_rate": 0.7})
            .with_metadata({"asset": "BTC", "strategy_id": "strat-001"})
            .build()
        )

    def test_complete_decision_generation(self) -> None:
        """Test 1: Complete decision generation. Expected: Decision result created."""
        result = self.engine.evaluate_advanced_decision(self.context)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, DecisionResult)
        self.assertEqual(result.State, "Approved")
        self.assertTrue(result.Reason.ConfidenceScore > 0.0)

    def test_research_and_strategy_alignment(self) -> None:
        """Test 2: Research and strategy alignment. Expected: Higher confidence."""
        # 1. Aligned high confidence scenario
        aligned_ctx = (
            DecisionContextBuilder()
            .with_research([MarketInsight(Category="Trend", Description="Bullish", Confidence=0.95, CreatedAt=self.now)])
            .with_strategy([StrategyEvaluation(StrategyId="s1", Score=StrategyScore(0.92, 0.95, {}), EvaluationNotes="Best", EvaluatedAt=self.now)])
            .with_risk([self.mock_risk_assess])
            .build()
        )
        res_aligned = self.engine.evaluate_advanced_decision(aligned_ctx)

        # 2. Lower confidence scenario
        low_ctx = (
            DecisionContextBuilder()
            .with_research([MarketInsight(Category="Trend", Description="Choppy", Confidence=0.50, CreatedAt=self.now)])
            .with_strategy([StrategyEvaluation(StrategyId="s1", Score=StrategyScore(0.55, 0.50, {}), EvaluationNotes="Weak", EvaluatedAt=self.now)])
            .with_risk([self.mock_risk_assess])
            .build()
        )
        res_low = self.engine.evaluate_advanced_decision(low_ctx)

        self.assertGreater(res_aligned.Reason.ConfidenceScore, res_low.Reason.ConfidenceScore)

    def test_research_and_risk_conflict(self) -> None:
        """Test 3: Research and risk conflict. Expected: Conflict detected."""
        conflict_ctx = (
            DecisionContextBuilder()
            .with_research([MarketInsight(Category="Trend", Description="Bullish Trend", Confidence=0.9, CreatedAt=self.now)])
            .with_strategy([StrategyEvaluation(StrategyId="strat-001", Score=StrategyScore(OverallScore=0.88, Confidence=0.9, Criteria={}), EvaluationNotes="Ok", EvaluatedAt=self.now)])
            .with_risk([RiskAssessment(IsApproved=False, RiskProfileName="Moderate", PortfolioRiskMetrics=PortfolioRisk(0.3, 0.2, 0.1), AssessmentNotes="Risk violation", AssessedAt=self.now)])
            .build()
        )

        result = self.engine.evaluate_advanced_decision(conflict_ctx)
        self.assertEqual(result.State, "Rejected")

        # Check resolver output directly
        conflicts = self.resolver.resolve_conflicts(conflict_ctx)
        self.assertEqual(conflicts.ConflictType, "StrategyRiskConflict")
        self.assertTrue(conflicts.ConfidenceImpact < 0.0)

    def test_insufficient_evidence(self) -> None:
        """Test 4: Insufficient evidence. Expected: ReviewRequired or InsufficientData state."""
        # Risk assessment is missing, resulting in ReviewRequired
        insufficient_ctx = (
            DecisionContextBuilder()
            .with_research([self.mock_insight])
            .with_strategy([self.mock_strategy_eval])
            .build()
        )

        result = self.engine.evaluate_advanced_decision(insufficient_ctx)
        self.assertEqual(result.State, "ReviewRequired")

    def test_missing_context(self) -> None:
        """Test 5: Missing context. Expected: Validation failure."""
        empty_ctx = (
            DecisionContextBuilder()
            .build()
        )

        with self.assertRaises(ValidationException):
            self.validator.validate_context(empty_ctx)

    def test_decision_quality_scoring(self) -> None:
        """Test 6: Decision quality scoring. Expected: Stable score."""
        quality_1 = self.evaluator.evaluate_quality(self.context)
        quality_2 = self.evaluator.evaluate_quality(self.context)

        self.assertEqual(quality_1.EvidenceQuality, quality_2.EvidenceQuality)
        self.assertEqual(quality_1.ConsistencyScore, quality_2.ConsistencyScore)
        self.assertEqual(quality_1.ReliabilityScore, quality_2.ReliabilityScore)
        self.assertEqual(quality_1.OverallQualityScore, quality_2.OverallQualityScore)

    def test_evidence_collection(self) -> None:
        """Test 7: Evidence collection. Expected: Complete evidence trail."""
        trail = self.collector.collect_evidence(self.context)

        self.assertIsNotNone(trail)
        self.assertIsInstance(trail, DecisionEvidenceTrail)
        self.assertEqual(len(trail.ResearchEvidence), 1)
        self.assertEqual(len(trail.StrategyEvidence), 1)
        self.assertEqual(len(trail.RiskEvidence), 1)
        self.assertTrue(len(trail.TraceabilityId) > 0)

    def test_decision_history(self) -> None:
        """Test 8: Decision history. Expected: Record created."""
        result = self.engine.evaluate_advanced_decision(self.context)
        history_records = self.engine.get_history()

        self.assertTrue(len(history_records) > 0)
        record = history_records[-1]
        self.assertIsInstance(record, DecisionHistoryRecord)
        self.assertEqual(record.Result.DecisionId, result.DecisionId)

    def test_simulation_safety(self) -> None:
        """Test 9: Simulation safety. Expected: Decision layer cannot execute actions (detects execution words and fails)."""
        # Attempt to pass active trading keywords in metadata
        with self.assertRaises(ValidationException) as ex:
            DecisionIntelligenceContext(
                ResearchInsights=[],
                PatternObservations=[],
                StrategyEvaluations=[],
                RiskAssessments=[],
                MarketConditions={},
                HistoricalEvidence={},
                Metadata={"execute_live_order": True}
            )
        self.assertIn("Safety Violation", str(ex.exception))

    def test_full_intelligence_chain(self) -> None:
        """Test 10: Full intelligence chain (Research -> Strategy -> Risk -> Decision). Expected: Complete successful flow."""
        # 1. Run Research
        from src.Research.MarketAnalysis.Services.services import ResearchProcessor
        from src.Research.MarketAnalysis.Models.models import ResearchRequest

        research_engine = ResearchProcessor()
        res_req = ResearchRequest(Asset="AAPL", StartTime=self.now - timedelta(days=10), EndTime=self.now)
        research_res = research_engine.analyze_market(res_req)

        # 2. Run Strategy Evaluation
        from src.Strategy.Evaluation.evaluation import StrategyEvaluator
        strategy_evaluator = StrategyEvaluator()
        candidate = StrategyCandidate(
            Id="cand-AAPL",
            Name="AAPL Reversion",
            Description="AAPL Mean Reversion concept",
            ResearchContext=research_res.Findings,
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )
        strat_eval = strategy_evaluator.evaluate(candidate)

        # 3. Run Risk Intelligence
        from src.Risk.Analysis.analyzer import RiskAnalyzer
        from src.Risk.Analysis.context import RiskAnalysisContext
        risk_analyzer = RiskAnalyzer()
        risk_context = RiskAnalysisContext(
            MarketFeatureSet={"volatility": 0.20, "trend_strength": 0.5, "confidence": research_res.ConfidenceScore},
            ResearchInsights=[MarketInsight(Category="Trend", Description="Bullish", Confidence=research_res.ConfidenceScore, CreatedAt=self.now)],
            StrategyEvaluation={"strategy_id": strat_eval.StrategyId, "overall_score": strat_eval.Score.OverallScore, "confidence": strat_eval.Score.Confidence},
            HistoricalScenarioInfo={"success_rate": 0.70}
        )
        risk_assessment = risk_analyzer.analyze_advanced_risk(risk_context)

        # 4. Run Decision Intelligence
        decision_context = (
            DecisionContextBuilder()
            .with_research([MarketInsight(Category="Trend", Description="Bullish", Confidence=research_res.ConfidenceScore, CreatedAt=self.now)])
            .with_strategy([strat_eval])
            .with_risk([risk_assessment])
            .with_market_context({"volatility": 0.20})
            .with_historical_evidence({"success_rate": 0.70})
            .with_metadata({"asset": "AAPL", "strategy_id": strat_eval.StrategyId})
            .build()
        )

        final_report = self.engine.generate_intelligence_report(decision_context)

        self.assertIsNotNone(final_report)
        self.assertIsInstance(final_report, DecisionIntelligenceReport)
        self.assertEqual(final_report.Context.Metadata["asset"], "AAPL")
        self.assertEqual(final_report.EvidenceTrail.TraceabilityId, "ev-AAPL-1-1")
        self.assertTrue(final_report.QualityScore.OverallQualityScore > 0.0)
        self.assertTrue(len(final_report.ReportId) > 0)
