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


def test_close_requires_positive_position_ticket():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    adapter._mt5 = MagicMock()
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    adapter._mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001)
    adapter._mt5.symbol_info_tick.return_value = MagicMock(bid=1.0850, ask=1.0852)

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=0)
    with pytest.raises(Exception) as exc:
        adapter.send_order_to_broker(req)
    assert "Valid non-zero PositionTicket is required" in str(exc.value)


def test_close_fetches_real_position():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    adapter._mt5 = MagicMock()
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    adapter._mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001)
    adapter._mt5.symbol_info_tick.return_value = MagicMock(bid=1.0850, ask=1.0852)
    adapter._mt5.positions_get.return_value = []

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=123456)
    with pytest.raises(Exception) as exc:
        adapter.send_order_to_broker(req)
    assert "No open MT5 position found" in str(exc.value)


def test_close_buy_uses_sell_and_bid():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.positions_get.return_value = [MagicMock(ticket=1001, type=0)]
    mock_mt5.order_check.return_value = MagicMock(retcode=10009, comment="OK")
    mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=1001, deal=2002, price=1.08500, volume=0.01)

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=1001)
    adapter.send_order_to_broker(req)

    sent_req = mock_mt5.order_send.call_args[0][0]
    assert sent_req["type"] == mock_mt5.ORDER_TYPE_SELL
    assert sent_req["price"] == 1.08500  # Bid


def test_close_sell_uses_buy_and_ask():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.POSITION_TYPE_SELL = 1
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.positions_get.return_value = [MagicMock(ticket=1002, type=1)]  # Existing SELL
    mock_mt5.order_check.return_value = MagicMock(retcode=10009, comment="OK")
    mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=1002, deal=2003, price=1.08520, volume=0.01)

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=1002)
    adapter.send_order_to_broker(req)

    sent_req = mock_mt5.order_send.call_args[0][0]
    assert sent_req["type"] == mock_mt5.ORDER_TYPE_BUY
    assert sent_req["price"] == 1.08520  # Ask


def test_close_strips_sl_and_tp_and_sets_position_ticket():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.positions_get.return_value = [MagicMock(ticket=555, type=0)]
    mock_mt5.order_check.return_value = MagicMock(retcode=10009, comment="OK")
    mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=555, deal=666, price=1.08500, volume=0.01)

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=555, StopLoss=1.0000, TakeProfit=1.2000)
    adapter.send_order_to_broker(req)

    sent_req = mock_mt5.order_send.call_args[0][0]
    assert sent_req["position"] == 555
    assert "sl" not in sent_req
    assert "tp" not in sent_req


def test_close_does_not_send_after_failed_order_check():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True
    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.symbol_info.return_value = MagicMock(visible=True, digits=5, point=0.00001, volume_min=0.01, volume_step=0.01, volume_max=100.0)
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)
    mock_mt5.positions_get.return_value = [MagicMock(ticket=777, type=0)]
    mock_mt5.order_check.return_value = MagicMock(retcode=10016, comment="Invalid stops")

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(Symbol="EURUSD", OrderType="CLOSE", Volume=0.01, PositionTicket=777)
    resp = adapter.send_order_to_broker(req)

    assert resp.Status == "Failed"
    assert resp.Retcode == 10016
    mock_mt5.order_send.assert_not_called()
