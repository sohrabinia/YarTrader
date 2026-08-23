import pytest
from unittest.mock import MagicMock
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Models.models import OrderRequest


def test_no_position_to_close_when_positions_get_empty():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=5,
        point=0.00001,
        trade_stops_level=20,
        trade_freeze_level=10,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=100.0,
        filling_mode=1
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.positions_get.return_value = []  # No open positions found

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(
        Symbol="EURUSD",
        OrderType="CLOSE",
        Volume=0.01,
        PositionTicket=123456
    )

    with pytest.raises(Exception) as exc_info:
        adapter.send_order_to_broker(req)

    assert "No open MT5 position found for ticket 123456" in str(exc_info.value)


def test_close_request_strips_sl_tp_and_passes_position_ticket():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=5,
        point=0.00001,
        trade_stops_level=20,
        trade_freeze_level=10,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=100.0,
        filling_mode=1
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.positions_get.return_value = [MagicMock(ticket=987654, type=0)]
    mock_mt5.order_check.return_value = MagicMock(retcode=10009, comment="OK")
    mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=987654, deal=112233, price=1.08500, volume=0.01)

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    # Order request has SL and TP set, but OrderType is CLOSE
    req = OrderRequest(
        Symbol="EURUSD",
        OrderType="CLOSE",
        Volume=0.01,
        PositionTicket=987654,
        StopLoss=1.0500,
        TakeProfit=1.1200
    )

    resp = adapter.send_order_to_broker(req)
    assert resp.Status == "Placed"

    # Verify order_send call payload
    sent_req = mock_mt5.order_send.call_args[0][0]
    assert sent_req["position"] == 987654
    assert "sl" not in sent_req
    assert "tp" not in sent_req


def test_close_request_with_invalid_position_ticket_raises():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=5,
        point=0.00001,
        trade_stops_level=20,
        trade_freeze_level=10,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=100.0,
        filling_mode=1
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(
        Symbol="EURUSD",
        OrderType="CLOSE",
        Volume=0.01,
        PositionTicket=0
    )

    with pytest.raises(Exception) as exc_info:
        adapter.send_order_to_broker(req)

    assert "Valid non-zero PositionTicket is required" in str(exc_info.value)
