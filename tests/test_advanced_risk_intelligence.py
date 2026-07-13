import unittest
from datetime import datetime, timedelta
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Risk.Analysis.analyzer import RiskAnalyzer
from src.Risk.Analysis.exposure import ExposureAnalyzer, ExposureAssessment
from src.Risk.Analysis.correlation import CorrelationAnalyzer, CorrelationReport
from src.Risk.Analysis.scenario import RiskScenarioEngine, RiskScenarioResult
from src.Risk.Analysis.scorer import RiskScoreCalculator, RiskScore
from src.Risk.Analysis.assessment import AdvancedRiskAssessment
from src.Risk.Analysis.report import RiskReportBuilder, RiskAnalysisReport
from src.Research.MarketAnalysis.Models.models import MarketInsight
from src.Strategy.Models.models import StrategyCandidate, StrategyScore, StrategyEvaluation
from src.Infrastructure.exceptions import ValidationException

class TestAdvancedRiskIntelligence(unittest.TestCase):
    """
    Thorough test suite verifying Phase 17 Advanced Risk Intelligence Layer.
    """

    def setUp(self) -> None:
        self.analyzer = RiskAnalyzer()
        self.now = datetime.now()

        # Build healthy default inputs
        self.default_features = {
            "volatility": 0.18,
            "trend_strength": 0.6,
            "confidence": 0.88
        }
        self.default_insights = [
            MarketInsight(Category="Trend", Description="Bullish Trend", Confidence=0.85, CreatedAt=self.now)
        ]
        self.default_strategy_eval = {
            "strategy_id": "cand-001",
            "overall_score": 0.82,
            "confidence": 0.90,
            "beta": 1.1
        }
        self.default_history = {
            "success_rate": 0.68
        }

        self.context = RiskAnalysisContext(
            MarketFeatureSet=self.default_features,
            ResearchInsights=self.default_insights,
            StrategyEvaluation=self.default_strategy_eval,
            HistoricalScenarioInfo=self.default_history,
            RiskContext={"risk_limit": 0.75}
        )

    def test_basic_risk_analysis(self) -> None:
        """Test 1: Basic risk analysis. Expected: AdvancedRiskAssessment generated."""
        assessment = self.analyzer.analyze_advanced_risk(self.context)

        self.assertIsNotNone(assessment)
        self.assertIsInstance(assessment, AdvancedRiskAssessment)
        self.assertIn(assessment.OverallClassification, ["Low", "Moderate", "High", "Critical"])
        self.assertTrue(len(assessment.RiskFactors) >= 0)
        self.assertIn("insights_count", assessment.Evidence)

    def test_high_volatility_scenario_increases_risk(self) -> None:
        """Test 2: High volatility scenario. Expected: Risk level increases."""
        # 1. Healthy volatility state
        low_vol_features = {"volatility": 0.08, "trend_strength": 0.3, "confidence": 0.9}
        ctx_low = RiskAnalysisContext(
            MarketFeatureSet=low_vol_features,
            ResearchInsights=self.default_insights,
            StrategyEvaluation=self.default_strategy_eval,
            HistoricalScenarioInfo=self.default_history
        )
        assessment_low = self.analyzer.analyze_advanced_risk(ctx_low)

        # 2. Extreme volatility state
        high_vol_features = {"volatility": 0.45, "trend_strength": 0.3, "confidence": 0.9}
        ctx_high = RiskAnalysisContext(
            MarketFeatureSet=high_vol_features,
            ResearchInsights=self.default_insights,
            StrategyEvaluation=self.default_strategy_eval,
            HistoricalScenarioInfo=self.default_history
        )
        assessment_high = self.analyzer.analyze_advanced_risk(ctx_high)

        self.assertGreater(
            assessment_high.RiskScoreInfo.MarketRiskScore,
            assessment_low.RiskScoreInfo.MarketRiskScore
        )
        self.assertGreater(
            assessment_high.RiskScoreInfo.OverallRiskScore,
            assessment_low.RiskScoreInfo.OverallRiskScore
        )

    def test_correlation_analysis(self) -> None:
        """Test 3: Correlation analysis. Expected: Relationships detected."""
        corr_analyzer = CorrelationAnalyzer()
        report = corr_analyzer.analyze_correlation(self.context)

        self.assertIsNotNone(report)
        self.assertIsInstance(report, CorrelationReport)
        self.assertIn("Price", report.CorrelationMatrix)
        self.assertIn("Volatility", report.CorrelationMatrix["Price"])
        self.assertTrue(len(report.CoreCorrelatedConditions) >= 0)

    def test_exposure_analysis(self) -> None:
        """Test 4: Exposure analysis. Expected: Exposure report generated."""
        exp_analyzer = ExposureAnalyzer()
        assessment = exp_analyzer.analyze_exposure(self.context)

        self.assertIsNotNone(assessment)
        self.assertIsInstance(assessment, ExposureAssessment)
        self.assertIn(assessment.ConcentrationRating, ["Low", "Medium", "High"])
        self.assertIn("volatility_state_dependency", assessment.DependencyAnalysis)
        self.assertIn("beta", assessment.SensitivityMetrics)

    def test_risk_scoring_consistency(self) -> None:
        """Test 5: Risk scoring consistency. Expected: Same input produces stable score."""
        scorer = RiskScoreCalculator()

        score_1 = scorer.calculate_risk_score(self.context)
        score_2 = scorer.calculate_risk_score(self.context)

        self.assertEqual(score_1.MarketRiskScore, score_2.MarketRiskScore)
        self.assertEqual(score_1.StrategyCompatibilityRisk, score_2.StrategyCompatibilityRisk)
        self.assertEqual(score_1.StabilityScore, score_2.StabilityScore)
        self.assertEqual(score_1.OverallRiskScore, score_2.OverallRiskScore)

    def test_invalid_context(self) -> None:
        """Test 6: Invalid context. Expected: Safe validation failure."""
        with self.assertRaises(ValidationException):
            self.analyzer.analyze_advanced_risk(None)

    def test_simulation_safety(self) -> None:
        """Test 7: Simulation safety. Expected: Risk layer cannot execute actions (detects execution words and fails)."""
        # Attempt to pass active trading keywords in feature set
        with self.assertRaises(ValidationException) as ex:
            RiskAnalysisContext(
                MarketFeatureSet={"volatility": 0.1, "buy_order_trigger": "active_signal"},
                ResearchInsights=[],
                StrategyEvaluation={},
                HistoricalScenarioInfo={}
            )
        self.assertIn("Safety Violation", str(ex.exception))

        # Attempt to pass broker connection in metadata
        with self.assertRaises(ValidationException) as ex_metadata:
            RiskAnalysisContext(
                MarketFeatureSet={},
                ResearchInsights=[],
                StrategyEvaluation={},
                HistoricalScenarioInfo={},
                Metadata={"broker_reference": "live_account_123"}
            )
        self.assertIn("Safety Violation", str(ex_metadata.exception))

    def test_full_pipeline_integration(self) -> None:
        """Test 8: Full pipeline integration. Expected: Research -> Strategy -> Risk flow works."""
        # 1. Run Research Layer Interpretation
        from src.Research.MarketAnalysis.Services.services import ResearchProcessor
        from src.Research.MarketAnalysis.Models.models import ResearchRequest

        research_engine = ResearchProcessor()
        res_req = ResearchRequest(
            Asset="ETH",
            StartTime=self.now - timedelta(days=5),
            EndTime=self.now
        )
        research_res = research_engine.analyze_market(res_req)

        # 2. Run Strategy Layer Assessment
        from src.Strategy.Evaluation.evaluation import StrategyEvaluator

        strategy_evaluator = StrategyEvaluator()
        candidate = StrategyCandidate(
            Id="cand-ETH",
            Name="Pipeline Eth Concept",
            Description="ETH Momentum concept",
            ResearchContext=research_res.Findings,
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )
        strat_eval = strategy_evaluator.evaluate(candidate)

        # 3. Feed findings into Advanced Risk Intelligence Context
        integration_context = RiskAnalysisContext(
            MarketFeatureSet={
                "volatility": 0.22,
                "trend_strength": 0.7,
                "confidence": research_res.ConfidenceScore
            },
            ResearchInsights=[
                MarketInsight(Category="Trend", Description="Bullish Shift", Confidence=research_res.ConfidenceScore, CreatedAt=self.now)
            ],
            StrategyEvaluation={
                "strategy_id": strat_eval.StrategyId,
                "overall_score": strat_eval.Score.OverallScore,
                "confidence": strat_eval.Score.Confidence,
                "beta": 1.25
            },
            HistoricalScenarioInfo={"success_rate": 0.72}
        )

        # 4. Generate advanced report
        full_report = self.analyzer.build_full_report(integration_context)

        self.assertIsNotNone(full_report)
        self.assertIsInstance(full_report, RiskAnalysisReport)
        self.assertEqual(full_report.MarketConditions["volatility"], 0.22)
        self.assertAlmostEqual(full_report.RiskScoring.ConfidenceLevel, 0.865, places=2)
        self.assertEqual(full_report.ExposureAnalysis.ConcentrationRating, "Low")
        self.assertTrue(len(full_report.ReportId) > 0)
