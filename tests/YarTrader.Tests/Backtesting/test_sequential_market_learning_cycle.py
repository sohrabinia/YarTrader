import json

from scripts.run_sequential_market_learning_cycle import SYMBOL_ORDER, atomic_json, metric_snapshot


def test_market_order_is_gold_then_eurusd():
    assert SYMBOL_ORDER == ("XAUUSD", "EURUSD")


def test_metric_snapshot_uses_closed_trade_pnl_and_r_multiple():
    result = metric_snapshot({
        "net_pnl": 5.0,
        "learning_updates_count": 2,
        "closed_trades": [
            {"outcome": "WIN", "pnl": 10.0, "r_multiple": 1.5},
            {"outcome": "LOSS", "pnl": -5.0, "r_multiple": -1.0},
        ],
    })

    assert result["total_trades"] == 2
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["win_rate_pct"] == 50.0
    assert result["profit_factor"] == 2.0
    assert result["mean_r_multiple"] == 0.25
    assert result["learning_updates_count"] == 2


def test_atomic_json_persists_parseable_report(tmp_path):
    path = tmp_path / "report.json"
    atomic_json(path, {"status": "ok", "broker_orders_submitted": 0})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "status": "ok", "broker_orders_submitted": 0
    }
    assert not path.with_suffix(".json.tmp").exists()
