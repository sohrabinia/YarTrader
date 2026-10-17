from src.Application.Research.optimization.cost_model import CostModel


def test_fx_contract_multiplier_matches_standard_lot_backtest_accounting():
    result = CostModel(spread_pips=1.0, commission_per_lot=7.0, slippage_pips=0.5).calculate_cost_adjusted_pnl(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1000,
        exit_price=1.1010,
        volume_lots=1.0,
    )

    # 0.0010 * 100,000 = $100 gross; 1 pip spread + 0.5 pip slippage + $7 commission = $22.
    assert result["gross_pnl"] == 100.0
    assert result["spread_cost"] == 10.0
    assert result["slippage_cost"] == 5.0
    assert result["commission_cost"] == 7.0
    assert result["net_pnl"] == 78.0


def test_jpy_pair_uses_jpy_pip_size_and_exit_conversion():
    result = CostModel(spread_pips=1.0, commission_per_lot=0.0, slippage_pips=0.0).calculate_cost_adjusted_pnl(
        symbol="USDJPY",
        direction="BUY",
        entry_price=150.0,
        exit_price=151.0,
        volume_lots=1.0,
    )

    assert result["gross_pnl"] == round(100000.0 / 151.0, 2)
    assert result["spread_cost"] == round(100000.0 / 151.0 * 0.01, 2)
    assert result["net_pnl"] == round(result["gross_pnl"] - result["spread_cost"], 2)


def test_gold_contract_multiplier_remains_one_hundred_ounces():
    result = CostModel(spread_pips=0.0, commission_per_lot=0.0, slippage_pips=0.0).calculate_cost_adjusted_pnl(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2300.0,
        exit_price=2301.0,
        volume_lots=1.0,
    )
    assert result["gross_pnl"] == 100.0
    assert result["net_pnl"] == 100.0


def test_crypto_combined_friction_matches_backtest_convention():
    result = CostModel().calculate_cost_adjusted_pnl(
        symbol="BTCUSD",
        direction="BUY",
        entry_price=50_000.0,
        exit_price=51_000.0,
        volume_lots=0.01,
    )
    assert result["gross_pnl"] == 10.0
    assert result["spread_cost"] == 0.51
    assert result["commission_cost"] == 0.0
    assert result["slippage_cost"] == 0.0
    assert result["net_pnl"] == 9.49
