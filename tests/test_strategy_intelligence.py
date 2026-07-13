import unittest
from datetime import datetime
from src.Strategy.Models.models import StrategyDefinition, StrategyCandidate, StrategyScore, StrategyEvaluation
from src.Strategy.Interfaces.interfaces import IStrategyEngine, IStrategyEvaluator, IStrategyRegistry, IRuleValidator
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Strategy.Services.services import StrategyAnalyzer
from src.Strategy.Evaluation.evaluation import StrategyEvaluator, EvaluationResult
from src.Strategy.Registry.registry import StrategyRegistry

class TestStrategyIntelligence(unittest.TestCase):
    def test_strategy_modules_imports(self):
        """Verify that all Phase 4 Strategy Intelligence classes are successfully imported."""
        self.assertIsNotNone(StrategyDefinition)
        self.assertIsNotNone(StrategyCandidate)
        self.assertIsNotNone(StrategyScore)
        self.assertIsNotNone(StrategyEvaluation)
        self.assertIsNotNone(IStrategyEngine)
        self.assertIsNotNone(IStrategyEvaluator)
        self.assertIsNotNone(IStrategyRegistry)
        self.assertIsNotNone(IRuleValidator)
        self.assertIsNotNone(EvaluationCriteria)
        self.assertIsNotNone(StrategyEvaluator)
        self.assertIsNotNone(StrategyRegistry)
        self.assertIsNotNone(StrategyAnalyzer)

    def test_strategy_models_instantiation(self):
        """Verify strategy request, score, candidate, and evaluation models properties."""
        now = datetime.now()
        definition = StrategyDefinition(
            Id="strat-001",
            Name="Mean Reversion",
            Description="Descriptive mean reversion concepts",
            CreatedAt=now,
            Version="1.0.0",
            Status="Draft"
        )
        self.assertEqual(definition.id, "strat-001")
        self.assertEqual(definition.name, "Mean Reversion")
        self.assertEqual(definition.status, "Draft")

        candidate = StrategyCandidate(
            Id="cand-123",
            Name="Momentum Rating",
            Description="Evaluates price velocity rating",
            ResearchContext={"timeframe": "D1"},
            CreatedAt=now,
            EvaluationStatus="Pending"
        )
        self.assertEqual(candidate.id, "cand-123")
        self.assertEqual(candidate.evaluation_status, "Pending")

        score = StrategyScore(
            OverallScore=0.82,
            Confidence=0.90,
            Criteria={"Stability": 0.80}
        )
        self.assertEqual(score.overall_score, 0.82)
        self.assertEqual(score.criteria["Stability"], 0.80)

        evaluation = StrategyEvaluation(
            StrategyId="cand-123",
            Score=score,
            EvaluationNotes="Passed structural checks",
            EvaluatedAt=now
        )
        self.assertEqual(evaluation.strategy_id, "cand-123")
        self.assertEqual(evaluation.score.overall_score, 0.82)

    def test_strategy_services(self):
        """Verify placeholder strategy evaluator, registry, and rule validator services."""
        now = datetime.now()

        # 1. Test StrategyRegistry
        registry = StrategyRegistry()
        def_concept = StrategyDefinition(
            Id="strat-002",
            Name="Trend-Following Profile",
            Description="Passive trend following concepts",
            CreatedAt=now,
            Version="1.1.0",
            Status="Approved"
        )
        registry.register_strategy(def_concept)
        retrieved = registry.get_strategy("strat-002")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Trend-Following Profile")

        # 2. Test StrategyEvaluator
        evaluator = StrategyEvaluator()
        candidate = StrategyCandidate(
            Id="cand-456",
            Name="Alpha Rating",
            Description="Calculates rating alpha metric",
            ResearchContext={},
            CreatedAt=now,
            EvaluationStatus="Evaluating"
        )
        evaluation = evaluator.evaluate(candidate)
        self.assertEqual(evaluation.strategy_id, "cand-456")
        self.assertTrue(evaluation.score.overall_score > 0.0)
        self.assertIn(EvaluationCriteria.STABILITY, evaluation.score.criteria)

        # 3. Test StrategyAnalyzer (IRuleValidator)
        analyzer = StrategyAnalyzer()
        self.assertTrue(analyzer.validate_structure(def_concept))

        invalid_concept = StrategyDefinition(
            Id="strat-invalid",
            Name="",
            Description="Missing name",
            CreatedAt=now,
            Version="1.0.0",
            Status="Draft"
        )
        self.assertFalse(analyzer.validate_structure(invalid_concept))
