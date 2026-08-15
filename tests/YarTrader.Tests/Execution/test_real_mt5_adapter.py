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


if __name__ == "__main__":
    unittest.main()
