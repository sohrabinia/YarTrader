import pytest
from datetime import datetime, timedelta

from src.Application.Research.optimization import (
    ParameterSpace,
    DatasetSplitter,
    CostModel,
    ObjectiveEvaluator,
    GridSearchEngine,
    WalkForwardOptimizer,
    OverfittingDiagnostics,
    BaselineEvaluator,
    ExperimentProvenance,
    ResearchOptimizationRunner
)

@pytest.fixture
def sample_candles():
    candles = []
    base_price = 2000.0
    start_time = datetime(2025, 1, 1, 10, 0, 0)

    for i in range(300):
        t = start_time + timedelta(minutes=5 * i)
        # Generate deterministic synthetic price series
        change = (i % 5 - 2) * 0.5
        base_price += change
        candles.append({
            "timestamp": t.isoformat(),
            "open": base_price - 0.2,
            "high": base_price + 1.0,
            "low": base_price - 1.0,
            "close": base_price,
            "volume": 100.0 + (i % 10) * 10
        })
    return candles

def test_parameter_space():
    space = ParameterSpace({"threshold": [0.6, 0.7], "multiplier": [1.5, 2.0]})
    combos = space.generate_cartesian_product()
    assert len(combos) == 4
    assert "threshold" in combos[0]
    assert "multiplier" in combos[0]

def test_dataset_splitter(sample_candles):
    splits = DatasetSplitter.split_chronological(sample_candles, 0.6, 0.2, 0.2)
    assert len(splits["train"]) == 180
    assert len(splits["validation"]) == 60
    assert len(splits["test"]) == 60
    assert splits["hash"] is not None

def test_cost_model():
    cost = CostModel(spread_pips=1.0, commission_per_lot=7.0, slippage_pips=0.5)
    res = cost.calculate_cost_adjusted_pnl(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        exit_price=2010.0,
        volume_lots=0.1
    )
    assert res["gross_pnl"] == 100.0
    assert res["total_cost"] == 2.2  # (1.5 pips * 0.1 * 100) + $0.70 comm = $2.20
    assert res["net_pnl"] == 97.8

def test_objective_evaluator():
    closed_trades = [
        {"pnl": 50.0, "r_multiple": 2.0},
        {"pnl": -20.0, "r_multiple": -1.0},
        {"pnl": 30.0, "r_multiple": 1.5},
        {"pnl": 40.0, "r_multiple": 1.8},
        {"pnl": -15.0, "r_multiple": -1.0}
    ]
    metrics = ObjectiveEvaluator.calculate_metrics(closed_trades, initial_balance=10000.0)
    assert metrics["total_trades"] == 5
    assert metrics["wins"] == 3
    assert metrics["win_rate_pct"] == 60.0
    assert metrics["net_pnl"] == 85.0
    assert metrics["profit_factor"] > 1.0

def test_overfitting_diagnostics():
    candidate = {"net_pnl": 100.0, "trade_count": 10}
    val_metrics = {"net_pnl": 80.0}
    test_metrics = {"net_pnl": 75.0}

    diag = OverfittingDiagnostics.evaluate_candidate_robustness(candidate, val_metrics, test_metrics)
    assert diag["overfitting_detected"] is False
    assert diag["status"] == "PASS_ROBUST"

def test_research_runner(sample_candles):
    space = ParameterSpace({"stop_multiplier": [1.5, 2.0]})
    runner = ResearchOptimizationRunner()

    res = runner.run_full_research_pipeline(
        symbol="XAUUSD",
        timeframe="M5",
        candles=sample_candles,
        parameter_space=space,
        initial_balance=10000.0
    )

    assert res["status"] == "COMPLETED"
    assert "provenance" in res
    assert "baseline" in res
    assert "walk_forward" in res
    assert res["promotion_status"] == "RESEARCH_ONLY_NO_AUTO_PROMOTION"
