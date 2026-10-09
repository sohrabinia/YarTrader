import pytest
from src.Learning.Services.experiment_runner import PerturbatedExperimentRunner


def test_experiment_is_explicitly_diagnostic_and_drawdown_is_computed():
    runner = PerturbatedExperimentRunner()
    closes = [2000, 2004, 1998, 2010, 1990, 2001, 1980, 2005, 1995, 2012, 2000, 2010]
    bars = [{"timestamp": f"bar-{i}", "close": value} for i, value in enumerate(closes)]
    result = runner.run_experiment("v1", "XAUUSD", "M5", bars, 0.8, 1.2, {"rsi_period": 14})
    assert result.experiment_id.startswith("exp-")
    assert result.total_trades > 0
    assert result.perturbations["slippage_pip"] == 0.8
    assert result.evaluation_mode == "DIAGNOSTIC_LONG_ONLY_PRICE_PATH"
    assert result.is_strategy_backtest is False
    assert result.max_drawdown_usd > 0
    assert result.max_drawdown_usd != 150.0
    assert result.warnings


def test_missing_close_is_rejected_instead_of_fabricating_price():
    bars = [{"close": 2000.0} for _ in range(6)]
    del bars[3]["close"]
    with pytest.raises(ValueError, match="missing a close price"):
        PerturbatedExperimentRunner().run_experiment("v1", "XAUUSD", "M5", bars)


def test_invalid_or_nonpositive_close_is_rejected():
    bars = [{"close": 2000.0} for _ in range(6)]
    bars[2]["close"] = float("nan")
    with pytest.raises(ValueError, match="finite and greater than zero"):
        PerturbatedExperimentRunner().run_experiment("v1", "XAUUSD", "M5", bars)


def test_too_short_dataset_is_rejected():
    with pytest.raises(ValueError, match="At least 6"):
        PerturbatedExperimentRunner().run_experiment("v1", "XAUUSD", "M5", [{"close": 1.0}] * 5)


def test_ohlc_extremes_are_used_for_favorable_and_adverse_excursion():
    closes = [100, 101, 102, 103, 104, 105, 106, 107]
    bars = [{"open": c, "high": c + 2, "low": c - 3, "close": c} for c in closes]
    result = PerturbatedExperimentRunner().run_experiment("v1", "TEST", "M5", bars, 0, 0)
    assert result.max_favorable_excursion_price >= 2
    assert result.max_adverse_excursion_price >= 2
    assert any("OHLC extrema" in warning for warning in result.warnings)


def test_inconsistent_ohlc_range_is_rejected():
    bars = [{"open": 100, "high": 99, "low": 98, "close": 100} for _ in range(6)]
    with pytest.raises(ValueError, match="close must lie between low and high"):
        PerturbatedExperimentRunner().run_experiment("v1", "TEST", "M5", bars)
