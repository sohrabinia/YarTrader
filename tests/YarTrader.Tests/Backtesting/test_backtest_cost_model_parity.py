from src.Application.Backtesting.backtest_learning_engine import calculate_backtest_cost_adjusted_pnl


def test_backtest_and_research_cost_model_share_fx_accounting():
    result = calculate_backtest_cost_adjusted_pnl("EURUSD", "BUY", 1.1000, 1.1010, 1.0)
    assert result["gross_pnl"] == 100.0
    assert result["total_cost"] == 17.0
    assert result["net_pnl"] == 83.0


def test_backtest_and_research_cost_model_share_gold_accounting():
    result = calculate_backtest_cost_adjusted_pnl("XAUUSD", "BUY", 2300.0, 2301.0, 1.0)
    assert result["gross_pnl"] == 100.0
    assert result["total_cost"] == 27.0
    assert result["net_pnl"] == 73.0


def test_backtest_and_research_cost_model_share_silver_accounting():
    result = calculate_backtest_cost_adjusted_pnl("XAGUSD", "BUY", 30.0, 30.02, 1.0)
    assert result["gross_pnl"] == 100.0
    assert result["total_cost"] == 107.0
    assert result["net_pnl"] == -7.0


def test_backtest_and_research_cost_model_convert_jpy_quote_pnl():
    result = calculate_backtest_cost_adjusted_pnl("USDJPY", "BUY", 150.0, 151.0, 1.0)
    assert result["gross_pnl"] == 662.25
    assert result["spread_cost"] == 6.62
    assert result["commission_cost"] == 7.0
    assert result["net_pnl"] == 648.63


def test_backtest_and_research_cost_model_share_crypto_friction():
    result = calculate_backtest_cost_adjusted_pnl("BTCUSD", "BUY", 50_000.0, 51_000.0, 0.01)
    assert result["gross_pnl"] == 10.0
    assert result["total_cost"] == 0.51
    assert result["net_pnl"] == 9.49
