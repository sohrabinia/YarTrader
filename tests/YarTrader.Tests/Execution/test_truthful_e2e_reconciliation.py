import pytest
from unittest.mock import MagicMock
from src.Execution.Services.trade_journal import TradeJournalRecord
from src.Execution.Models.models import OrderRequest
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from scripts.run_real_mt5_demo_e2e import reconcile_pnl


def test_reconcile_pnl_success():
    mt5_metrics = {
        "symbol": "BITCOIN",
        "volume": 0.01,
        "net_pnl": -0.23,
        "open_price": 78311.0,
        "close_price": 77537.5
    }
    journal = TradeJournalRecord(
        decision_id="DEC-001",
        trade_id="TR-368555219",
        cycle_id="CYC-001",
        symbol="BITCOIN",
        timeframe="M15",
        direction="BUY",
        planned_entry=78311.0,
        planned_sl=77500.0,
        planned_tp=80000.0,
        planned_rr=2.0,
        actual_entry=78311.0,
        actual_exit=77537.5,
        volume=0.01,
        confidence=85.0,
        reasoning=["Real MT5 DEMO Execution"],
        evidence={},
        order_ticket="368555219",
        deal_ticket="326112166",
        open_time="2026-08-22T00:00:00",
        close_time="2026-08-22T01:00:00",
        exit_reason="Position Closed",
        pnl=-0.23,
        pnl_percent=-0.0023,
        mfe=0.0,
        mae=773.5,
        duration=60.0,
        market_regime="DEMO",
        result="LOSS",
        configuration_version="1.2.0"
    )

    is_reconciled, msg = reconcile_pnl(mt5_metrics, journal)
    assert is_reconciled is True
    assert "P&L Reconciled" in msg


def test_reconcile_pnl_missing_journal():
    mt5_metrics = {
        "symbol": "BITCOIN",
        "volume": 0.01,
        "net_pnl": -0.23
    }
    is_reconciled, msg = reconcile_pnl(mt5_metrics, None)
    assert is_reconciled is False
    assert "UNPROVEN / BLOCKED" in msg


def test_reconcile_pnl_discrepancy():
    mt5_metrics = {
        "symbol": "BITCOIN",
        "volume": 0.01,
        "net_pnl": -0.23
    }
    journal = TradeJournalRecord(
        decision_id="DEC-001",
        trade_id="TR-368555219",
        cycle_id="CYC-001",
        symbol="XAUUSD",  # Symbol mismatch
        timeframe="M15",
        direction="BUY",
        planned_entry=2600.0,
        planned_sl=2590.0,
        planned_tp=2620.0,
        planned_rr=2.0,
        actual_entry=2600.0,
        actual_exit=2620.0,
        volume=0.01,
        confidence=85.0,
        reasoning=[],
        evidence={},
        order_ticket="368555219",
        deal_ticket="326112166",
        open_time="2026-08-22T00:00:00",
        close_time="2026-08-22T01:00:00",
        exit_reason="Close",
        pnl=100.0,  # PnL mismatch
        pnl_percent=1.0,
        mfe=20.0,
        mae=0.0,
        duration=60.0,
        market_regime="DEMO",
        result="WIN",
        configuration_version="1.2.0"
    )

    is_reconciled, msg = reconcile_pnl(mt5_metrics, journal)
    assert is_reconciled is False
    assert "Reconciliation Failed" in msg
    assert "Symbol mismatch" in msg


def test_order_check_fail_closed():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.TRADE_RETCODE_DONE = 10009
    mock_mt5.TRADE_RETCODE_PLACED = 10008
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=2600.0, ask=2600.5)

    # Simulated failed order_check (retcode 10014 = INVALID_VOLUME)
    mock_check_res = MagicMock()
    mock_check_res.retcode = 10014
    mock_check_res.comment = "Invalid volume"
    mock_mt5.order_check.return_value = mock_check_res

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2600.5)
    resp = adapter.send_order_to_broker(req)

    assert resp.Status == "Failed"
    assert resp.Retcode == 10014
    assert "order_check validation failed" in resp.Comment
    # order_send MUST NOT be called!
    assert mock_mt5.order_send.call_count == 0


def test_order_check_success_allows_order_send():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=2600.0, ask=2600.5)

    mock_check_res = MagicMock()
    mock_check_res.retcode = 0  # DONE
    mock_mt5.order_check.return_value = mock_check_res

    mock_send_res = MagicMock()
    mock_send_res.retcode = 10009
    mock_send_res.order = 123456
    mock_send_res.deal = 654321
    mock_send_res.price = 2600.5
    mock_send_res.volume = 0.01
    mock_send_res.comment = "Request executed"
    mock_mt5.order_send.return_value = mock_send_res

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2600.5)
    resp = adapter.send_order_to_broker(req)

    assert resp.Status == "Placed"
    assert resp.OrderId == "123456"
    assert resp.DealTicket == "654321"
    assert mock_mt5.order_send.call_count == 1
