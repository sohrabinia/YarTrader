from types import SimpleNamespace

from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader


class FakeAdapter:
    def __init__(self, orders, cancel_status="Cancelled"):
        self.orders = list(orders)
        self.cancel_status = cancel_status
        self.cancelled = []

    def cancel_pending_order(self, ticket):
        self.cancelled.append(ticket)
        if self.cancel_status == "Cancelled":
            self.orders = [o for o in self.orders if o["ticket"] != ticket]
        return SimpleNamespace(Status=self.cancel_status, Retcode=10009, Comment="test")

    def get_active_orders(self, symbol=None):
        return list(self.orders)


def _order(ticket, *, comment="YarBaseRTM", magic=100001, volume=0.14):
    return {
        "ticket": ticket, "type": 2, "magic": magic, "comment": comment,
        "price_open": 1.12424, "sl": 1.12362, "tp": 1.12587,
        "volume_current": volume,
    }


def _trader(orders, adapter):
    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    trader.adapter = adapter
    trader.events = []
    trader._log_event = trader.events.append
    return trader


def test_exact_duplicate_bot_order_is_cancelled_but_manual_order_is_preserved():
    orders = [_order(390083605), _order(390085505),
              _order(900, comment="ManualOrder", magic=0)]
    adapter = FakeAdapter(orders)
    trader = _trader(orders, adapter)

    result = trader._dedupe_owned_pending_orders("EURUSD", orders, {"digits": 5})

    assert result["ok"] is True
    assert result["cancelled_tickets"] == [390085505]
    assert adapter.cancelled == [390085505]
    assert {o["ticket"] for o in result["orders"]} == {390083605, 900}
    event = trader.events[0]
    assert event["event"] == "duplicate_pending_order_reconciled"
    assert event["duplicate_ticket"] == 390085505
    assert event["kept_ticket"] == 390083605
    assert event["broker_confirmed"] is True


def test_duplicate_cancellation_failure_blocks_further_execution():
    orders = [_order(1), _order(2)]
    adapter = FakeAdapter(orders, cancel_status="Failed")
    trader = _trader(orders, adapter)

    result = trader._dedupe_owned_pending_orders("EURUSD", orders, {"digits": 5})

    assert result["ok"] is False
    assert "Could not cancel duplicate" in result["reason"]
    assert trader.events[0]["broker_confirmed"] is False


def test_symbol_execution_lock_suppresses_concurrent_worker(tmp_path):
    import os
    from unittest.mock import patch
    import src.Execution.Services.autonomous_demo_trader as trader_module

    with patch.object(trader_module, "_PROJECT_ROOT", tmp_path):
        first_fd, first_path = trader_module._acquire_symbol_execution_lock("XAUUSD")
        assert first_fd is not None
        try:
            second_fd, second_path = trader_module._acquire_symbol_execution_lock("XAUUSD")
            assert second_fd is None
            assert second_path == first_path
        finally:
            os.close(first_fd)
            first_path.unlink(missing_ok=True)
        third_fd, third_path = trader_module._acquire_symbol_execution_lock("XAUUSD")
        assert third_fd is not None
        os.close(third_fd)
        third_path.unlink(missing_ok=True)


def test_submission_outcome_journals_final_broker_order_prices_not_original_plan(tmp_path):
    from unittest.mock import patch
    import src.Execution.Services.autonomous_demo_trader as trader_module

    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    trader.events = []
    trader._log_event = trader.events.append
    trader._reconcile_base_pending_order_impl = lambda *args, **kwargs: {
        "status": "PENDING_ORDER_SUBMITTED", "ticket": 1234,
        "broker_status": "Placed", "reason": "Request executed",
        "order_type": "BUY_LIMIT", "entry": 100.0, "stop_loss": 99.0,
        "take_profit": 102.0, "volume": 0.03, "broker_retcode": 10009,
        "risk": {"risk_budget_usd": 27.0},
    }
    plan = {"selected_strategy": "RTM", "order_plan": {
        "direction": "BUY", "order_type": "BUY_LIMIT", "entry": 100.0,
        "stop_loss": 98.0, "take_profit": 103.0,
    }}
    with patch.object(trader_module, "_PROJECT_ROOT", tmp_path):
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 100.0, "ask": 100.1}, {}, {},
        )

    outcome = trader.events[-1]
    assert result["ticket"] == 1234
    assert outcome["broker_confirmed"] is True
    assert outcome["stop_loss"] == 99.0
    assert outcome["take_profit"] == 102.0
    assert outcome["execution_details"]["volume"] == 0.03
    assert outcome["execution_details"]["broker_retcode"] == 10009
