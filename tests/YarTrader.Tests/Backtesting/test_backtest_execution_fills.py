import pytest

from src.Application.Backtesting.backtest_learning_engine import resolve_bar_exit_fill


@pytest.mark.parametrize(
    ("direction", "bar", "stop", "target", "expected_reason", "expected_fill"),
    [
        # A gap through a stop is filled at the worse opening price, not the stop level.
        ("BUY", {"open": 98.0, "high": 101.0, "low": 97.0}, 99.0, 105.0, "STOP_LOSS_HIT", 98.0),
        ("SELL", {"open": 102.0, "high": 103.0, "low": 99.0}, 101.0, 95.0, "STOP_LOSS_HIT", 102.0),
        # A favorable gap through a target is filled at the open.
        ("BUY", {"open": 106.0, "high": 108.0, "low": 104.0}, 99.0, 105.0, "TAKE_PROFIT_HIT", 106.0),
        ("SELL", {"open": 94.0, "high": 96.0, "low": 92.0}, 101.0, 95.0, "TAKE_PROFIT_HIT", 94.0),
        # When the open is between both levels and both are touched, stop wins conservatively.
        ("BUY", {"open": 100.0, "high": 106.0, "low": 98.0}, 99.0, 105.0, "STOP_LOSS_HIT", 99.0),
        ("SELL", {"open": 100.0, "high": 102.0, "low": 94.0}, 101.0, 95.0, "STOP_LOSS_HIT", 101.0),
    ],
)
def test_bar_exit_fill_resolves_gaps_and_ambiguous_bars(
    direction, bar, stop, target, expected_reason, expected_fill
):
    reason, fill = resolve_bar_exit_fill(
        direction,
        bar["open"],
        bar["high"],
        bar["low"],
        stop,
        target,
    )
    assert reason == expected_reason
    assert fill == expected_fill


def test_bar_without_stop_or_target_touch_stays_open():
    reason, fill = resolve_bar_exit_fill(
        "BUY", open_price=100.0, high_price=104.0, low_price=100.0,
        stop_loss=99.0, take_profit=105.0,
    )
    assert reason is None
    assert fill == 100.0


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError, match="direction must be BUY or SELL"):
        resolve_bar_exit_fill("HOLD", 100.0, 101.0, 99.0, 98.0, 102.0)
