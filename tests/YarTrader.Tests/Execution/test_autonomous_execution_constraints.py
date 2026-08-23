import pytest
from unittest.mock import MagicMock
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Models.models import OrderRequest


def test_eurusd_5_digits_and_stops_level_normalization():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.POSITION_TYPE_SELL = 1
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=5,
        point=0.00001,
        trade_stops_level=20,  # 20 pts = 0.00020
        trade_freeze_level=10,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=100.0,
        filling_mode=1
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1.08500, ask=1.08520)

    mock_check_res = MagicMock(retcode=0, comment="OK")
    mock_mt5.order_check.return_value = mock_check_res

    mock_send_res = MagicMock(retcode=10009, order=101, deal=201, price=1.08520, volume=0.01, comment="Executed")
    mock_mt5.order_send.return_value = mock_send_res

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    # Request with SL too close to entry (distance 0.00005 < min_stop_distance 0.00020)
    req = OrderRequest(
        Symbol="EURUSD",
        OrderType="BUY",
        Volume=0.013,  # Should align to step 0.01
        Price=1.08520,
        StopLoss=1.08515,  # Too close!
        TakeProfit=1.08600
    )

    resp = adapter.send_order_to_broker(req)
    assert resp.Status == "Placed"

    # Inspect trade_req passed to order_check
    args, kwargs = mock_mt5.order_check.call_args
    trade_req = args[0]

    assert trade_req["symbol"] == "EURUSD"
    assert trade_req["volume"] == 0.01  # Aligned to step
    assert trade_req["price"] == 1.08520
    # StopLoss should be adjusted to at least price - 0.00020 = 1.08500
    assert trade_req["sl"] <= 1.08500


def test_bitcoin_2_digits_and_volume_step_alignment():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.POSITION_TYPE_SELL = 1
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=2,
        point=0.01,
        trade_stops_level=500,  # 500 pts = $5.00
        trade_freeze_level=0,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        filling_mode=2
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=65000.00, ask=65005.00)

    mock_check_res = MagicMock(retcode=0, comment="OK")
    mock_mt5.order_check.return_value = mock_check_res

    mock_send_res = MagicMock(retcode=10009, order=301, deal=401, price=65005.00, volume=0.01, comment="Executed")
    mock_mt5.order_send.return_value = mock_send_res

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(
        Symbol="BITCOIN",
        OrderType="BUY",
        Volume=0.01,
        Price=65005.00,
        StopLoss=65003.00,  # $2 distance < $5.00 min stop
        TakeProfit=65100.00
    )

    resp = adapter.send_order_to_broker(req)
    assert resp.Status == "Placed"

    args, kwargs = mock_mt5.order_check.call_args
    trade_req = args[0]

    assert trade_req["price"] == 65005.00
    assert trade_req["sl"] <= 65000.00  # Adjusted for min stop distance


def test_xauusd_decimal_precision_and_close_order():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_mt5.POSITION_TYPE_BUY = 0
    mock_mt5.POSITION_TYPE_SELL = 1
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.symbol_info.return_value = MagicMock(
        visible=True,
        digits=2,
        point=0.01,
        trade_stops_level=100,  # $1.00
        trade_freeze_level=50,
        volume_min=0.01,
        volume_step=0.01,
        volume_max=100.0,
        filling_mode=1
    )
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=2350.50, ask=2351.00)
    mock_mt5.positions_get.return_value = [MagicMock(ticket=999, type=0)]  # POSITION_TYPE_BUY = 0

    mock_check_res = MagicMock(retcode=0, comment="OK")
    mock_mt5.order_check.return_value = mock_check_res

    mock_send_res = MagicMock(retcode=10009, order=999, deal=888, price=2350.50, volume=0.01, comment="Executed")
    mock_mt5.order_send.return_value = mock_send_res

    adapter._mt5 = mock_mt5
    adapter.verify_safety_and_account = MagicMock(return_value=True)

    req = OrderRequest(
        Symbol="XAUUSD",
        OrderType="CLOSE",
        Volume=0.01,
        PositionTicket=999,
        Comment="Closing position 999"
    )

    resp = adapter.send_order_to_broker(req)
    assert resp.Status == "Placed"

    args, kwargs = mock_mt5.order_check.call_args
    trade_req = args[0]

    assert trade_req["position"] == 999
    assert trade_req["type"] == mock_mt5.ORDER_TYPE_SELL  # Closing a BUY order requires SELL
    assert trade_req["price"] == 2350.50
