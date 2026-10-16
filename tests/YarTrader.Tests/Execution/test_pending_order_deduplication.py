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


def test_pending_order_matching_tolerates_small_quote_noise_without_churn():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    order = {"type": 2, "price_open": 2300.00, "sl": 2290.00, "tp": 2320.00}
    matches, entry_tolerance, protection_tolerance, target_tolerance = _pending_order_matches_current_plan(
        order, expected_type=2, entry=2300.08, stop=2290.02, target=2320.02,
        point=0.01, spread=0.03,
    )
    assert matches is True
    assert entry_tolerance >= 0.23
    assert protection_tolerance >= 0.045
    assert target_tolerance >= 4.9


def test_pending_order_target_noise_does_not_trigger_cancel_replace():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    # Same entry and protective stop, with a small structural target adjustment.
    # Retaining the existing valid TP avoids cancelling/re-creating the order each cycle.
    order = {"type": 3, "price_open": 4184.67, "sl": 4192.48, "tp": 4170.48}
    matches, _, _, target_tolerance = _pending_order_matches_current_plan(
        order, expected_type=3, entry=4184.67, stop=4192.48, target=4170.09,
        point=0.01, spread=0.04, direction="SELL",
    )
    assert target_tolerance >= 3.9
    assert matches is True


def test_pending_order_matching_detects_material_structural_change():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    order = {"type": 2, "price_open": 2300.00, "sl": 2290.00, "tp": 2320.00}
    matches, _, _, _ = _pending_order_matches_current_plan(
        order, expected_type=2, entry=2302.00, stop=2290.00, target=2320.00,
        point=0.01, spread=0.03,
    )
    assert matches is False


def test_existing_sell_order_with_safer_stop_and_target_is_kept_when_plan_moves_slightly():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    order = {"type": 3, "price_open": 4184.67, "sl": 4192.48, "tp": 4168.70}
    matches, _, stop_tolerance, target_tolerance = _pending_order_matches_current_plan(
        order, expected_type=3, entry=4184.666, stop=4192.7419, target=4165.85,
        point=0.01, spread=0.04, direction="SELL",
    )
    assert stop_tolerance >= 0.26
    assert target_tolerance >= 2.85
    assert matches is True


def test_pending_order_with_less_protective_stop_is_not_kept_on_wide_tolerance():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    order = {"type": 3, "price_open": 4184.67, "sl": 4192.90, "tp": 4168.70}
    matches, _, stop_tolerance, _ = _pending_order_matches_current_plan(
        order, expected_type=3, entry=4184.666, stop=4192.7419, target=4165.85,
        point=0.01, spread=0.04, direction="SELL",
    )
    assert stop_tolerance < 0.26
    assert matches is False


def test_strategy_comments_survive_mt5_sanitization_and_legacy_truncation():
    from src.Execution.Services.autonomous_demo_trader import (
        _legacy_strategy_comment_matches, _strategy_broker_comment,
    )

    assert _strategy_broker_comment("RTM") == "YarBaseRTM"
    assert _strategy_broker_comment("BASE_ENGULF_REVERSAL") == "YarBaseENGULF"
    assert len(_strategy_broker_comment("BASE_ENGULF_REVERSAL")) <= 15
    assert _legacy_strategy_comment_matches("YarBaseBASE_ENG", "BASE_ENGULF_REVERSAL")
    assert not _legacy_strategy_comment_matches("YarBaseRTM", "BASE_ENGULF_REVERSAL")


def test_pending_order_keeps_conservative_target_within_one_risk_distance():
    from src.Execution.Services.autonomous_demo_trader import _pending_order_matches_current_plan

    order = {"type": 3, "price_open": 1.12443, "sl": 1.12512, "tp": 1.12250}
    matches, _, _, target_tolerance = _pending_order_matches_current_plan(
        order, expected_type=3, entry=1.12443, stop=1.125124,
        target=1.12204, point=0.00001, spread=0.00002, direction="SELL",
    )
    assert target_tolerance >= 0.00069
    assert matches is True
