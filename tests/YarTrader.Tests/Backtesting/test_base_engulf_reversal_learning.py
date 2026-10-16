import json

from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine


def test_base_engulf_observation_is_deduplicated_and_trade_outcome_is_linked(tmp_path):
    engine = BacktestAndLearningEngine(storage_dir=str(tmp_path))
    base = {"low": 10.0, "high": 11.0, "width": 1.0, "start_time": 100, "end_time": 200}
    item = {"timeframe": "M5", "base": base, "engulfed": True, "engulf_time": 300,
            "trend_direction": 1, "departure_time": 250, "direction": "SELL",
            "status": "ENTRY_PROPOSAL", "reason": "test signal"}
    result = {"timeframe_results": {"M5": item}}
    engine._record_base_engulf_observations("EURUSD", result, "1970-01-01T00:05:00+00:00")
    engine._record_base_engulf_observations("EURUSD", result, "1970-01-01T00:10:00+00:00")
    key = "EURUSD|M5|100|200|300"
    trade = {"strategy": "BASE_ENGULF_REVERSAL", "base_engulf_observation_key": key,
             "symbol": "EURUSD", "setup_timeframe": "M5", "outcome": "LOSS",
             "exit_reason": "STOP_LOSS_HIT", "entry_time": 400, "exit_time": 500,
             "entry": 10.5, "exit_price": 11.1, "stop_loss": 11.1, "take_profit": None,
             "pnl": -10.0, "r_multiple": -1.0, "mfe": 0.2, "mae": -0.6}
    engine._record_base_engulf_outcome(trade)
    engine._record_base_engulf_outcome(trade)
    rows = [json.loads(line) for line in engine._base_engulf_observation_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["label_status"] == "PENDING_FORWARD_OUTCOME"
    assert rows[1]["record_type"] == "OUTCOME_LABEL"
    assert rows[1]["observation_key"] == key
    assert rows[1]["outcome"] == "LOSS"



def test_forward_labels_cover_not_yet_engulfed_controls_without_lookahead(tmp_path):
    engine = BacktestAndLearningEngine(storage_dir=str(tmp_path))
    base = {"low": 99.5, "high": 100.5, "width": 1.0, "start_time": 0, "end_time": 0}
    item = {"timeframe": "M1", "base": base, "engulfed": False,
            "observation_time": 0, "observation_close": 100.0,
            "trend_direction": 1, "departure_time": 0, "direction": "WAIT",
            "status": "WAIT", "reason": "control observation"}
    bars = []
    for i in range(11):
        # The first post-observation bar reaches the 2x-width reversal target,
        # without touching the 1x-width adverse barrier.
        low = 97.9 if i == 1 else 99.2
        high = 100.5
        bars.append({"timestamp": i*60, "open": 100.0, "high": high,
                     "low": low, "close": 99.5})
    engine._record_base_engulf_observations(
        "EURUSD", {"timeframe_results": {"M1": item}}, "historical-decision",
        timeframe_candles={"M1": bars}, now_epoch=660,
    )
    rows = [json.loads(line) for line in engine._base_engulf_observation_path.read_text(encoding="utf-8").splitlines()]
    labels = [row for row in rows if row.get("record_type") == "FORWARD_OUTCOME_LABEL"]
    assert len(labels) == 1
    assert labels[0]["engulfed"] is False
    assert labels[0]["outcome_source"] == "historical_ohlc_barrier_simulation"
    assert labels[0]["first_transition"] == "reversal_target_first"
    assert labels[0]["label_horizon_bars"] == 10
