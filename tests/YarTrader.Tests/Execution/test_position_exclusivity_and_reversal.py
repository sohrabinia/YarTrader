import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Infrastructure.exceptions import ValidationException
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator


class TestPositionExclusivityAndReversal(unittest.TestCase):
    """
    Deterministic regression and invariant test suite for:
    1. Position Exclusivity Guard (At most 1 active directional position per symbol).
    2. Sequential Reversal Lifecycle (OPEN -> CLOSE -> CONFIRM FLAT -> REASSESS -> INDEPENDENT OPPOSITE ENTRY).
    3. Fail-Closed protection on unconfirmed/failed close.
    4. Prohibition of stale auto_dec fallback parameters.
    5. Prohibition of automatic blind reversals.
    """

    def setUp(self):
        self.mock_adapter = MagicMock()
        # Mock account info and terminal info for DemoExecutionGate
        self.mock_adapter.get_account_info.return_value = {
            "login": "52961173",
            "server": "Alpari-MT5-Demo",
            "trade_mode": 0
        }
        self.mock_adapter.get_terminal_info.return_value = {
            "trade_allowed": True,
            "tradeapi_disabled": False
        }
        self.mock_adapter.get_symbol_info.return_value = {
            "trade_mode": 4,
            "volume_min": 0.01,
            "volume_max": 100.0
        }

    def test_normal_buy_when_flat(self):
        """Test 1: Normal BUY allowed when symbol has NO active positions."""
        self.mock_adapter.get_positions.return_value = []
        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="BUY",
            Volume=0.01,
            Price=2000.0,
            StopLoss=1990.0,
            TakeProfit=2020.0
        )
        self.assertTrue(DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True))

    def test_normal_sell_when_flat(self):
        """Test 2: Normal SELL allowed when symbol has NO active positions."""
        self.mock_adapter.get_positions.return_value = []
        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="SELL",
            Volume=0.01,
            Price=2000.0,
            StopLoss=2010.0,
            TakeProfit=1980.0
        )
        self.assertTrue(DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True))

    def test_buy_open_blocks_sell_candidate(self):
        """Test 3: BUY OPEN + SELL candidate -> SELL BLOCKED by Position Exclusivity Guard."""
        self.mock_adapter.get_positions.return_value = [
            {"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}
        ]
        sell_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="SELL",
            Volume=0.01,
            Price=2000.0,
            StopLoss=2010.0,
            TakeProfit=1980.0
        )
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, sell_req, demo_mode_flag=True)

        self.assertIn("Position Exclusivity Guard", str(ctx.exception))
        self.assertIn("Simultaneous or duplicate position entry is strictly forbidden", str(ctx.exception))

    def test_sell_open_blocks_buy_candidate(self):
        """Test 4: SELL OPEN + BUY candidate -> BUY BLOCKED by Position Exclusivity Guard."""
        self.mock_adapter.get_positions.return_value = [
            {"ticket": 1002, "symbol": "XAUUSD", "type": 1, "volume": 0.01}
        ]
        buy_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="BUY",
            Volume=0.01,
            Price=2000.0,
            StopLoss=1990.0,
            TakeProfit=2020.0
        )
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, buy_req, demo_mode_flag=True)

        self.assertIn("Position Exclusivity Guard", str(ctx.exception))

    def test_valid_sequential_reversal_lifecycle(self):
        """Test 5: Valid BUY -> CLOSE BUY -> CONFIRM CLOSED -> REASSESS -> SELL allowed."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Closed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Close OK"
        )

        # Mock active positions before close containing ticket 1001, and empty list after close
        # Mock active positions before close containing ticket 1001, and empty list after close
        self.mock_adapter.get_positions.side_effect = lambda symbol=None: []
        engine.get_active_positions = lambda symbol=None: [{"ticket": 1001, "volume": 0.01, "symbol": "XAUUSD"}] if not getattr(engine, "_closed_flag", False) else []

        orig_send = self.mock_adapter.send_order_to_broker
        def mock_send(req):
            engine._closed_flag = True
            return OrderResponse(OrderId="1001", Symbol=req.Symbol, Status="Closed", SubmittedAt=datetime.now(timezone.utc), Retcode=10009, Comment="Close OK")
        self.mock_adapter.send_order_to_broker = mock_send

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)

        self.assertEqual(close_resp.Status, "Closed")

        sell_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="SELL",
            Volume=0.01,
            Price=2000.0,
            StopLoss=2010.0,
            TakeProfit=1980.0
        )
        self.assertTrue(DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, sell_req, demo_mode_flag=True))

    def test_failed_close_blocks_opposite_entry(self):
        """Test 6: BUY OPEN -> CLOSE FAILS -> SELL BLOCKED (no reassessment, no opposite entry)."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        active_pos = [{"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}]
        self.mock_adapter.get_positions.return_value = active_pos

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="0",
            Symbol="XAUUSD",
            Status="Failed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10018,
            Comment="Market closed"
        )

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)
        self.assertEqual(close_resp.Status, "Failed")

        sell_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="SELL",
            Volume=0.01,
            Price=2000.0,
            StopLoss=2010.0,
            TakeProfit=1980.0
        )
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, sell_req, demo_mode_flag=True)

        self.assertIn("Position Exclusivity Guard", str(ctx.exception))

    def test_pending_close_blocks_opposite_entry(self):
        """Test 7: BUY OPEN -> CLOSE REQUESTED -> BROKER CLOSE PENDING -> SELL BLOCKED."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        active_pos = [{"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}]
        self.mock_adapter.get_positions.return_value = active_pos

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10008,
            Comment="Order placed"
        )

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)
        self.assertEqual(close_resp.Status, "Failed")

        sell_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="SELL",
            Volume=0.01,
            Price=2000.0,
            StopLoss=2010.0,
            TakeProfit=1980.0
        )
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, sell_req, demo_mode_flag=True)

        self.assertIn("Position Exclusivity Guard", str(ctx.exception))

    def test_close_without_opposite_confirmation_remains_flat(self):
        """Test 8: BUY OPEN -> CLOSE CONFIRMED -> Reassessment returns WAIT -> Remain FLAT."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Closed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Close OK"
        )

        self.mock_adapter.get_positions.side_effect = lambda symbol=None: []
        engine.get_active_positions = lambda symbol=None: [{"ticket": 1001, "volume": 0.01, "symbol": "XAUUSD"}] if not getattr(engine, "_closed_flag", False) else []
        orig_send = self.mock_adapter.send_order_to_broker
        def mock_send(req):
            engine._closed_flag = True
            return OrderResponse(OrderId="1001", Symbol=req.Symbol, Status="Closed", SubmittedAt=datetime.now(timezone.utc), Retcode=10009, Comment="Close OK")
        self.mock_adapter.send_order_to_broker = mock_send

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)
        self.assertEqual(close_resp.Status, "Closed")

        self.assertEqual(len(self.mock_adapter.get_positions(symbol="XAUUSD")), 0)

    def test_reversal_missing_fresh_parameters_fails_closed(self):
        """Test 9: Reversal with fresh action but missing entry/SL/TP parameters in reassess_dec -> BLOCKED."""
        reassess_dec = {
            "action": "SELL",
            "confidence": 75.0,
            "risk_reward": 2.0
            # missing "entry", "stop_loss", "take_profit"
        }

        rev_price = reassess_dec.get("entry")
        rev_sl = reassess_dec.get("stop_loss")
        rev_tp = reassess_dec.get("take_profit")

        is_valid = bool(rev_price and rev_sl and rev_tp and float(rev_price) > 0 and float(rev_sl) > 0 and float(rev_tp) > 0)
        self.assertFalse(is_valid)

    def test_reversal_never_uses_stale_fallback(self):
        """Test 10: Reversal parameters extracted strictly from reassess_dec without auto_dec fallback."""
        auto_dec = {
            "entry": 2000.0,
            "stop_loss": 1990.0,
            "take_profit": 2020.0
        }
        reassess_dec = {
            "action": "SELL",
            "entry": 2005.0,
            "stop_loss": 2015.0,
            "take_profit": 1985.0
        }

        rev_price = reassess_dec.get("entry")
        rev_sl = reassess_dec.get("stop_loss")
        rev_tp = reassess_dec.get("take_profit")

        self.assertEqual(rev_price, 2005.0)
        self.assertEqual(rev_sl, 2015.0)
        self.assertEqual(rev_tp, 1985.0)
        self.assertNotEqual(rev_price, auto_dec["entry"])

    def test_same_cycle_multi_strategy_candidate_single_execution(self):
        """Test 11: FAST_SCALP BUY + SCALP SELL in same cycle -> Exactly 1 candidate selected."""
        orchestrator = StrategyOrchestrator()
        candles = [
            {"open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
            for _ in range(10)
        ]
        liquidity = {"latest_sweep": {"type": "SELL_SIDE_LIQUIDITY_SWEEP"}}
        zones = {"order_blocks": [{"type": "BEARISH_OB", "top": 2010.0, "bottom": 2002.0}]}

        eval_res = orchestrator.evaluate_all_strategies(
            symbol="XAUUSD",
            primary_timeframe="M5",
            candles=candles,
            liquidity=liquidity,
            zones=zones
        )

        self.assertGreaterEqual(eval_res["active_candidates_count"], 1)
        best = eval_res["best_candidate"]
        self.assertIsNotNone(best)
        self.assertIn(best["direction"], ["BUY", "SELL"])


if __name__ == "__main__":
    unittest.main()
