import unittest
from datetime import datetime
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Strategy.Evaluation.context import StrategyEvaluationContext
from src.Strategy.Evaluation.scorer import StrategyScorer
from src.Strategy.Evaluation.comparator import StrategyComparator, StrategyComparisonResult
from src.Strategy.Evaluation.report import EvaluationReportBuilder, StrategyEvaluationReport
from src.Strategy.Evaluation.evaluation import StrategyEvaluator, EvaluationResult
from src.Research.MarketAnalysis.Models.models import MarketInsight, MarketObservation
from src.Infrastructure.exceptions import ValidationException

class TestStrategyEvaluationFramework(unittest.TestCase):
    """
    Unit and integration tests for Phase 16: Strategy Intelligence Evaluation Framework.
    """

    def setUp(self) -> None:
        self.evaluator = StrategyEvaluator()
        self.scorer = StrategyScorer()
        self.comparator = StrategyComparator()
        self.report_builder = EvaluationReportBuilder()

        # Build some standard testing inputs
        self.now = datetime.now()
        self.candidate_a = StrategyCandidate(
            Id="cand-A",
            Name="Mean Reversion Concept",
            Description="Descriptive mean reversion concepts",
            ResearchContext={"alpha": 0.05},
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )
        self.candidate_b = StrategyCandidate(
            Id="cand-B",
            Name="Trend Following Concept",
            Description="Follows trends over daily timeframes",
            ResearchContext={"beta": 1.2},
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )

    def test_basic_strategy_evaluation(self) -> None:
        """Test 1: Basic strategy evaluation produces correct StrategyEvaluation."""
        context = StrategyEvaluationContext(
            ResearchInsights=[],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.6},
            RiskContext={"risk_limit": 0.7},
            Metadata={"asset": "AAPL"}
        )

        evaluation = self.evaluator.evaluate(self.candidate_a, context)

        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.StrategyId, "cand-A")
        self.assertIsInstance(evaluation, StrategyEvaluation)
        self.assertIsInstance(evaluation.Score, StrategyScore)
        self.assertTrue(0.0 <= evaluation.Score.OverallScore <= 1.0)
        self.assertTrue(len(evaluation.EvaluationNotes) > 0)

    def test_multiple_strategy_comparison(self) -> None:
        """Test 2: Multiple strategy comparison ranks correctly and returns StrategyComparisonResult."""
        context_a = StrategyEvaluationContext(
            ResearchInsights=[MarketInsight(Category="Trend", Description="Bullish", Confidence=0.9, CreatedAt=self.now)],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.8},
            RiskContext={"risk_limit": 0.9}
        )
        context_b = StrategyEvaluationContext(
            ResearchInsights=[MarketInsight(Category="Volatility", Description="Choppy", Confidence=0.4, CreatedAt=self.now)],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.3},
            RiskContext={"risk_limit": 0.3}
        )

        eval_a = self.evaluator.evaluate(self.candidate_a, context_a)
        eval_b = self.evaluator.evaluate(self.candidate_b, context_b)

        result = self.comparator.compare([self.candidate_a, self.candidate_b], [eval_a, eval_b])

        self.assertIsNotNone(result)
        self.assertIsInstance(result, StrategyComparisonResult)
        self.assertEqual(result.BestStrategyId, "cand-A")
        self.assertEqual(result.RankedStrategyIds, ["cand-A", "cand-B"])
        self.assertIn("cand-A", result.Evaluations)
        self.assertIn("cand-B", result.Evaluations)
        self.assertTrue(result.ComparisonDetails["score_differential"] > 0)

        # Build report
        report = self.report_builder.build_report(
            candidates=[self.candidate_a, self.candidate_b],
            evaluations=[eval_a, eval_b],
            comparison=result,
            summary_notes="Comparison test report"
        )
        self.assertIsInstance(report, StrategyEvaluationReport)
        self.assertEqual(len(report.EvaluatedStrategies), 2)
        self.assertEqual(report.ComparisonInfo.BestStrategyId, "cand-A")

    def test_scoring_consistency(self) -> None:
        """Test 3: Scoring consistency is maintained (stable scores on identical input)."""
        context = StrategyEvaluationContext(
            ResearchInsights=[MarketInsight(Category="Trend", Description="Bullish", Confidence=0.85, CreatedAt=self.now)],
            MarketObservations=[MarketObservation(Asset="BTC", Timestamp=self.now, Observations={"vol": 0.2}, Source="Engine")],
            HistoricalScenarioInfo={"success_rate": 0.65},
            RiskContext={"risk_limit": 0.75}
        )

        score_1 = self.scorer.calculate_score(self.candidate_a, context)
        score_2 = self.scorer.calculate_score(self.candidate_a, context)

        self.assertEqual(score_1.OverallScore, score_2.OverallScore)
        self.assertEqual(score_1.Confidence, score_2.Confidence)
        self.assertEqual(score_1.Criteria, score_2.Criteria)

    def test_invalid_strategy_input(self) -> None:
        """Test 4: Invalid strategy input fails safely (raising appropriate ValidationException)."""
        invalid_cand = StrategyCandidate(
            Id="",
            Name="",
            Description="Invalid",
            ResearchContext={},
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )

        with self.assertRaises(ValidationException):
            self.evaluator.evaluate(invalid_cand)

    def test_research_integration(self) -> None:
        """Test 5: Research insight affects evaluation context and scores dynamically."""
        # Baseline context with no insights
        context_baseline = StrategyEvaluationContext(
            ResearchInsights=[],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.5},
            RiskContext={"risk_limit": 0.5}
        )

        # High confidence research insights
        high_conf_insight = MarketInsight(
            Category="Trend",
            Description="Strong upward velocity",
            Confidence=0.95,
            CreatedAt=self.now
        )
        context_high_conf = StrategyEvaluationContext(
            ResearchInsights=[high_conf_insight],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.5},
            RiskContext={"risk_limit": 0.5}
        )

        # Low confidence research insights
        low_conf_insight = MarketInsight(
            Category="Trend",
            Description="Weak reversal potential",
            Confidence=0.20,
            CreatedAt=self.now
        )
        context_low_conf = StrategyEvaluationContext(
            ResearchInsights=[low_conf_insight],
            MarketObservations=[],
            HistoricalScenarioInfo={"success_rate": 0.5},
            RiskContext={"risk_limit": 0.5}
        )

        eval_baseline = self.evaluator.evaluate(self.candidate_a, context_baseline)
        eval_high = self.evaluator.evaluate(self.candidate_a, context_high_conf)
        eval_low = self.evaluator.evaluate(self.candidate_a, context_low_conf)

        # High confidence research should elevate research alignment and overall score relative to low confidence
        self.assertGreater(
            eval_high.Score.Criteria["ResearchAlignment"],
            eval_low.Score.Criteria["ResearchAlignment"]
        )
        self.assertGreater(
            eval_high.Score.OverallScore,
            eval_low.Score.OverallScore
        )

    def test_simulation_safety(self) -> None:
        """Test 6: Simulation safety check (verify context cannot contain orders, trade commands, or broker references)."""
        # Test candidate containing forbidden keywords
        leaking_candidate = StrategyCandidate(
            Id="cand-leak",
            Name="Momentum Trader",
            Description="Executes live trade commands and place_order.",
            ResearchContext={},
            CreatedAt=self.now,
            EvaluationStatus="Pending"
        )

        with self.assertRaises(ValidationException) as ex:
            self.evaluator.evaluate(leaking_candidate)
        self.assertIn("Safety Violation", str(ex.exception))

        # Test context containing forbidden keywords
        with self.assertRaises(ValidationException) as ex_ctx:
            StrategyEvaluationContext(
                ResearchInsights=[],
                MarketObservations=[],
                HistoricalScenarioInfo={"broker_connection": "active_broker_connection"},
                RiskContext={}
            )
        self.assertIn("Safety Violation", str(ex_ctx.exception))
