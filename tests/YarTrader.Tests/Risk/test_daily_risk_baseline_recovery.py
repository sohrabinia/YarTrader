from unittest.mock import patch

from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader
from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch


def _evaluate(tmp_path, pnl):
    switch = DailyLossKillSwitch(persistence_path=str(tmp_path / "daily-risk.json"))
    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    trader.adapter = object()
    broker_pnl = {
        "total_pnl": pnl,
        "realized_pnl": pnl,
        "floating_pnl": 0.0,
        "owned_deal_count": 1,
        "owned_open_positions": 0,
    }
    with patch.object(DailyLossKillSwitch, "get_instance", return_value=switch), patch(
        "src.Risk.Services.daily_loss_kill_switch.calculate_yartrader_daily_pnl",
        return_value=broker_pnl,
    ):
        result = trader._evaluate_daily_risk({"equity": 1000.0}, broker_tick_time=0)
    return switch, result


def test_demo_daily_risk_bootstraps_missing_baseline_without_blocking_valid_1pct_loss(tmp_path):
    switch, result = _evaluate(tmp_path, pnl=-9.99)
    assert switch.baseline_equity == 1000.0
    assert result["allowed"] is True
    assert result["meta"]["max_daily_loss_pct"] == 10.0
    assert result["meta"]["loss_pct"] == 1.0


def test_demo_daily_risk_blocks_at_hard_10pct_even_after_baseline_recovery(tmp_path):
    switch, result = _evaluate(tmp_path, pnl=-100.0)
    assert switch.baseline_equity == 1000.0
    assert result["allowed"] is False
    assert result["reason"] == "DAILY_LOSS_LIMIT_REACHED"
    assert result["meta"]["max_daily_loss_pct"] == 10.0
