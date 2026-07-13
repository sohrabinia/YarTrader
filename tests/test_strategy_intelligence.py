from datetime import datetime
from src.Strategy.Models.models import StrategyDefinition, StrategyCandidate, StrategyScore, StrategyEvaluation
from src.Strategy.Interfaces.interfaces import IStrategyEngine, IStrategyEvaluator, IStrategyRegistry, IRuleValidator
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Strategy.Services.services import StrategyEvaluator, StrategyRegistry, StrategyAnalyzer

def test_strategy_modules_imports():
    """Verify that all Phase 4 Strategy Intelligence classes are successfully imported."""
    assert StrategyDefinition is not None
    assert StrategyCandidate is not None
    assert StrategyScore is not None
    assert StrategyEvaluation is not None
    assert IStrategyEngine is not None
    assert IStrategyEvaluator is not None
    assert IStrategyRegistry is not None
    assert IRuleValidator is not None
    assert EvaluationCriteria is not None
    assert StrategyEvaluator is not None
    assert StrategyRegistry is not None
    assert StrategyAnalyzer is not None

def test_strategy_models_instantiation():
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
    assert definition.id == "strat-001"
    assert definition.name == "Mean Reversion"
    assert definition.status == "Draft"

    candidate = StrategyCandidate(
        Id="cand-123",
        Name="Momentum Rating",
        Description="Evaluates price velocity rating",
        ResearchContext={"timeframe": "D1"},
        CreatedAt=now,
        EvaluationStatus="Pending"
    )
    assert candidate.id == "cand-123"
    assert candidate.evaluation_status == "Pending"

    score = StrategyScore(
        OverallScore=0.82,
        Confidence=0.90,
        Criteria={"Stability": 0.80}
    )
    assert score.overall_score == 0.82
    assert score.criteria["Stability"] == 0.80

    evaluation = StrategyEvaluation(
        StrategyId="cand-123",
        Score=score,
        EvaluationNotes="Passed structural checks",
        EvaluatedAt=now
    )
    assert evaluation.strategy_id == "cand-123"
    assert evaluation.score.overall_score == 0.82

def test_strategy_services():
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
    assert retrieved is not None
    assert retrieved.name == "Trend-Following Profile"

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
    assert evaluation.strategy_id == "cand-456"
    assert evaluation.score.overall_score > 0.0
    assert EvaluationCriteria.STABILITY in evaluation.score.criteria

    # 3. Test StrategyAnalyzer (IRuleValidator)
    analyzer = StrategyAnalyzer()
    assert analyzer.validate_structure(def_concept) is True

    invalid_concept = StrategyDefinition(
        Id="strat-invalid",
        Name="",
        Description="Missing name",
        CreatedAt=now,
        Version="1.0.0",
        Status="Draft"
    )
    assert analyzer.validate_structure(invalid_concept) is False
