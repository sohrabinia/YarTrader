import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Infrastructure.exceptions import ValidationException


class TestRealMT5BrokerAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = RealMT5BrokerAdapter(auto_initialize=False)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_verify_safety_and_account_unauthorized_account(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 99999999  # Unauthorized account
        mock_acc.server = "Alpari-MT5-Demo"
        mock_mt5.account_info.return_value = mock_acc

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        with self.assertRaises(ValidationException) as ctx:
            self.adapter.verify_safety_and_account("DEMO")

        self.assertIn("does not match authorized DEMO account", str(ctx.exception))

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_verify_safety_and_account_authorized(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        result = self.adapter.verify_safety_and_account("DEMO")
        self.assertTrue(result)
        mock_verify.assert_called_once_with(
            terminal_type="MT5",
            operation_type="DEMO",
            account_id="52961173",
            server_name="Alpari-MT5-Demo"
        )

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_send_order_to_broker_success(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 2300.50
        mock_tick.ask = 2300.80
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 123456789
        mock_res.deal = 987654321
        mock_res.price = 2300.80
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009, "order": 123456789}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="Buy",
            Volume=0.01,
            TargetWeight=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(resp.OrderId, "123456789")
        self.assertEqual(resp.DealTicket, "987654321")
        self.assertEqual(resp.Price, 2300.80)
        self.assertEqual(resp.Retcode, 10009)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_get_positions_mapping(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_pos = MagicMock()
        mock_pos._asdict.return_value = {
            "ticket": 12345,
            "symbol": "XAUUSD",
            "volume": 0.01,
            "profit": 15.5
        }
        mock_mt5.positions_get.return_value = [mock_pos]

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        positions = self.adapter.get_positions(symbol="XAUUSD")
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["ticket"], 12345)

    def test_resolve_filling_mode_bitcoin(self):
        mock_mt5 = MagicMock()
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.ORDER_FILLING_RETURN = 2

        sym_info_btc = MagicMock()
        sym_info_btc.filling_mode = 1  # SYMBOL_FILLING_FOK
        mode_btc = self.adapter._resolve_filling_mode(mock_mt5, "BITCOIN", sym_info_btc)
        self.assertEqual(mode_btc, 0)  # ORDER_FILLING_FOK

        sym_info_ioc = MagicMock()
        sym_info_ioc.filling_mode = 2  # SYMBOL_FILLING_IOC
        mode_ioc = self.adapter._resolve_filling_mode(mock_mt5, "EURUSD", sym_info_ioc)
        self.assertEqual(mode_ioc, 1)  # ORDER_FILLING_IOC

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_bitcoin_runtime_filling_mapping(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.POSITION_TYPE_BUY = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1  # BITCOIN filling_mode = 1 (SYMBOL_FILLING_FOK)
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_pos = MagicMock()
        mock_pos.type = 0  # BUY
        mock_mt5.positions_get.return_value = [mock_pos]

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 368555219
        mock_res.deal = 9999999
        mock_res.price = 65000.0
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009, "order": 368555219}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="CLOSE",
            Volume=0.01,
            PositionTicket=368555219
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(resp.OrderId, "368555219")
        mock_mt5.order_check.assert_called_once()
        trade_req_checked = mock_mt5.order_check.call_args[0][0]
        self.assertEqual(trade_req_checked["symbol"], "BITCOIN")
        self.assertEqual(trade_req_checked["position"], 368555219)
        self.assertEqual(trade_req_checked["type"], 1)
        self.assertEqual(trade_req_checked["type_filling"], 0)  # ORDER_FILLING_FOK

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_close_buy_generates_sell_request(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.POSITION_TYPE_BUY = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_pos = MagicMock()
        mock_pos.type = 0  # BUY
        mock_mt5.positions_get.return_value = [mock_pos]

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 368555219
        mock_res.deal = 9999999
        mock_res.price = 65000.0
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009, "order": 368555219}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="CLOSE",
            Volume=0.01,
            PositionTicket=368555219
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(resp.OrderId, "368555219")
        # Assert order_send trade_req type mapped to SELL (1)
        mock_mt5.order_send.assert_called_once()
        sent_trade_req = mock_mt5.order_send.call_args[0][0]
        self.assertEqual(sent_trade_req["type"], 1)
        self.assertEqual(sent_trade_req["position"], 368555219)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_order_check_blocks_10030(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # order_check returns retcode 10030 (Unsupported filling mode)
        mock_check = MagicMock()
        mock_check.retcode = 10030
        mock_check.comment = "Unsupported filling mode"
        mock_check._asdict.return_value = {"retcode": 10030, "comment": "Unsupported filling mode"}
        mock_mt5.order_check.return_value = mock_check

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="Buy",
            Volume=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Failed")
        self.assertEqual(resp.Retcode, 10030)
        mock_mt5.order_send.assert_not_called()

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_invalid_filling_blocks_order_send(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # order_check returns retcode 10030 (Unsupported filling mode)
        mock_check = MagicMock()
        mock_check.retcode = 10030
        mock_check.comment = "Unsupported filling mode"
        mock_check._asdict.return_value = {"retcode": 10030, "comment": "Unsupported filling mode"}
        mock_mt5.order_check.return_value = mock_check

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="Buy",
            Volume=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Failed")
        self.assertEqual(resp.Retcode, 10030)
        mock_mt5.order_send.assert_not_called()

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_authorized_demo_account_only(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        res = self.adapter.verify_safety_and_account("DEMO")
        self.assertTrue(res)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_order_check_invalid_retcode_10013_fails_closed(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 2300.50
        mock_tick.ask = 2300.80
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # order_check returns 10013 (TRADE_RETCODE_INVALID)
        mock_check = MagicMock()
        mock_check.retcode = 10013
        mock_check.comment = "Invalid stops or parameters"
        mock_check._asdict.return_value = {"retcode": 10013, "comment": "Invalid stops"}
        mock_mt5.order_check.return_value = mock_check

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="Buy",
            Volume=0.01,
            TargetWeight=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Failed")
        self.assertEqual(resp.OrderId, "0")
        self.assertEqual(resp.Retcode, 10013)
        mock_mt5.order_send.assert_not_called()

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_close_runtime_request_building(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.POSITION_TYPE_BUY = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 77000.0
        mock_tick.ask = 77050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_pos = MagicMock()
        mock_pos.type = 0  # BUY
        mock_mt5.positions_get.return_value = [mock_pos]

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 368555219
        mock_res.deal = 9999999
        mock_res.price = 77000.0
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009, "order": 368555219}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="CLOSE",
            Volume=0.01,
            PositionTicket=368555219
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(resp.OrderId, "368555219")
        mock_mt5.order_check.assert_called_once()
        trade_req_checked = mock_mt5.order_check.call_args[0][0]
        self.assertEqual(trade_req_checked["symbol"], "BITCOIN")
        self.assertEqual(trade_req_checked["position"], 368555219)
        self.assertEqual(trade_req_checked["type"], 1)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_filling_mode_used_in_trade_request(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.ORDER_FILLING_IOC = 1

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 2  # SYMBOL_FILLING_IOC (bit 1 = 2)
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 2300.50
        mock_tick.ask = 2300.80
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 111
        mock_res.deal = 222
        mock_res.price = 2300.80
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="Buy",
            Volume=0.01
        )

        self.adapter.send_order_to_broker(req)

        trade_req_sent = mock_mt5.order_send.call_args[0][0]
        self.assertEqual(trade_req_sent["type_filling"], 1)  # ORDER_FILLING_IOC resolved (1)

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_order_check_none_blocks_send(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 2300.50
        mock_tick.ask = 2300.80
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # order_check returns None for all candidate attempts
        mock_mt5.order_check.return_value = None

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="Buy",
            Volume=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Failed")
        self.assertEqual(resp.OrderId, "0")
        mock_mt5.order_send.assert_not_called()

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_close_order_filling_fallback(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.ORDER_FILLING_RETURN = 2
        mock_mt5.POSITION_TYPE_BUY = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1  # FOK preferred
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_pos = MagicMock()
        mock_pos.type = 0  # BUY
        mock_mt5.positions_get.return_value = [mock_pos]

        # First candidate (FOK) returns 10030 (unsupported filling), second candidate (IOC) returns 0 (success)
        fail_check = MagicMock()
        fail_check.retcode = 10030
        fail_check.comment = "Unsupported filling mode"

        success_check = MagicMock()
        success_check.retcode = 0
        success_check.comment = "OK"

        mock_mt5.order_check.side_effect = [fail_check, success_check]

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 368555219
        mock_res.deal = 888888
        mock_res.price = 65000.0
        mock_res.volume = 0.01
        mock_res.comment = "Close success via fallback"
        mock_res._asdict.return_value = {"retcode": 10009}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="CLOSE",
            Volume=0.01,
            PositionTicket=368555219
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(mock_mt5.order_check.call_count, 2)
        sent_req = mock_mt5.order_send.call_args[0][0]
        self.assertEqual(sent_req["type_filling"], 1)  # IOC fallback accepted

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_order_check_tries_multiple_fillings(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        mock_mt5.ORDER_FILLING_RETURN = 2

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 2300.50
        mock_tick.ask = 2300.80
        mock_mt5.symbol_info_tick.return_value = mock_tick

        fail_check = MagicMock()
        fail_check.retcode = 10030
        fail_check.comment = "Unsupported filling mode"

        mock_mt5.order_check.side_effect = [fail_check, fail_check, fail_check]

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="Buy",
            Volume=0.01
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Failed")
        self.assertEqual(mock_mt5.order_check.call_count, 3)
        mock_mt5.order_send.assert_not_called()

    @patch("src.Execution.Adapters.mt5_adapter.MetaTraderSafetyGate.verify_operation")
    def test_close_request_contains_position_ticket(self, mock_verify):
        mock_mt5 = MagicMock()
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_FOK = 0
        mock_mt5.POSITION_TYPE_BUY = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc

        mock_sym = MagicMock()
        mock_sym.visible = True
        mock_sym.volume_min = 0.01
        mock_sym.volume_step = 0.01
        mock_sym.volume_max = 100.0
        mock_sym.filling_mode = 1
        mock_mt5.symbol_info.return_value = mock_sym

        mock_tick = MagicMock()
        mock_tick.bid = 65000.0
        mock_tick.ask = 65050.0
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_pos = MagicMock()
        mock_pos.type = 0  # BUY
        mock_mt5.positions_get.return_value = [mock_pos]

        mock_check = MagicMock()
        mock_check.retcode = 0
        mock_mt5.order_check.return_value = mock_check

        mock_res = MagicMock()
        mock_res.retcode = 10009
        mock_res.order = 368555219
        mock_res.deal = 9999999
        mock_res.price = 65000.0
        mock_res.volume = 0.01
        mock_res.comment = "Success"
        mock_res._asdict.return_value = {"retcode": 10009, "order": 368555219}
        mock_mt5.order_send.return_value = mock_res

        self.adapter._mt5 = mock_mt5
        self.adapter._initialized = True

        req = OrderRequest(
            Symbol="BITCOIN",
            OrderType="CLOSE",
            Volume=0.01,
            PositionTicket=368555219
        )

        resp = self.adapter.send_order_to_broker(req)

        self.assertEqual(resp.Status, "Placed")
        self.assertEqual(resp.OrderId, "368555219")
        trade_req_sent = mock_mt5.order_send.call_args[0][0]
        self.assertIn("position", trade_req_sent)
        self.assertEqual(trade_req_sent["position"], 368555219)

    def test_close_request_comment_is_mt5_safe(self):
        sanitized_default = self.adapter._sanitize_comment(None)
        self.assertEqual(sanitized_default, "YarClose")
        self.assertLessEqual(len(sanitized_default), 15)

        long_comment = "YarTrader Real DEMO Close BITCOIN 12345"
        sanitized_long = self.adapter._sanitize_comment(long_comment)
        self.assertLessEqual(len(sanitized_long), 15)
        self.assertTrue(sanitized_long.isalnum())

        invalid_char_comment = "Close!! @#$ %^& *"
        sanitized_clean = self.adapter._sanitize_comment(invalid_char_comment)
        self.assertLessEqual(len(sanitized_clean), 15)
        self.assertEqual(sanitized_clean, "Close")


if __name__ == "__main__":
    unittest.main()
