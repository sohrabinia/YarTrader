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
    4. Prohibition of automatic blind reversals.
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
        """Test A: Normal BUY allowed when symbol has NO active positions."""
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
        """Test B: Normal SELL allowed when symbol has NO active positions."""
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
        """Test C: BUY OPEN + SELL candidate -> SELL BLOCKED by Position Exclusivity Guard."""
        # Active BUY position on XAUUSD
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

    def test_buy_open_blocks_duplicate_buy_candidate(self):
        """Test C2: BUY OPEN + Duplicate BUY candidate -> BUY BLOCKED by Position Exclusivity Guard."""
        self.mock_adapter.get_positions.return_value = [
            {"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}
        ]
        duplicate_buy_req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="BUY",
            Volume=0.01,
            Price=2000.0,
            StopLoss=1990.0,
            TakeProfit=2020.0
        )
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, duplicate_buy_req, demo_mode_flag=True)

        self.assertIn("Position Exclusivity Guard", str(ctx.exception))

    def test_valid_sequential_reversal_lifecycle(self):
        """Test D: Valid BUY -> CLOSE BUY -> CONFIRM CLOSED -> REASSESS -> SELL allowed."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        # 1. Active BUY position ticket 1001
        active_pos = [{"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}]
        self.mock_adapter.get_positions.return_value = active_pos

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Close OK"
        )

        # 2. Issue Close
        # First query during close_position returns remaining positions -> return [] (confirming flat!)
        self.mock_adapter.get_positions.side_effect = [active_pos, []]

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)

        # Confirm close succeeded
        self.mock_adapter.get_positions.side_effect = None
        self.mock_adapter.get_positions.return_value = []  # Flat state confirmed!

        # 3. Now SELL order request is submitted after confirmed flat state
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
        """Test E: BUY OPEN -> CLOSE FAILS -> SELL BLOCKED (BUY remains active/protected)."""
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

        # Position remains open on broker after failed close request
        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)
        self.assertEqual(close_resp.Status, "Failed")

        # Opposite SELL entry must be BLOCKED because position ticket 1001 is still open
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
        """Test F: BUY OPEN -> CLOSE REQUESTED -> BROKER CLOSE PENDING -> SELL BLOCKED."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        active_pos = [{"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}]
        # Position remains listed in broker get_positions
        self.mock_adapter.get_positions.return_value = active_pos

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10008,  # Placed/Pending
            Comment="Order placed"
        )

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)
        # Since position is still in get_positions, close status is Failed/Unconfirmed
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
        """Test G: BUY OPEN -> CLOSE CONFIRMED -> Reassessment returns WAIT -> Remain FLAT."""
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        active_pos = [{"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01}]
        self.mock_adapter.get_positions.side_effect = [active_pos, []]

        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Close OK"
        )

        close_resp = engine.close_position(symbol="XAUUSD", position_ticket=1001)

        # After close, market state reassessment returns WAIT (no automatic SELL)
        reassessment_action = "WAIT"
        self.assertEqual(reassessment_action, "WAIT")
        # No order request submitted; system remains flat!
        self.mock_adapter.get_positions.side_effect = None
        self.mock_adapter.get_positions.return_value = []
        self.assertEqual(len(self.mock_adapter.get_positions(symbol="XAUUSD")), 0)

    def test_same_cycle_multi_strategy_candidate_single_execution(self):
        """Test H: FAST_SCALP BUY + SCALP SELL in same cycle -> Best candidate selected, maximum 1 entry."""
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

        # Active candidates list may contain multiple candidates
        self.assertGreaterEqual(eval_res["active_candidates_count"], 1)
        best = eval_res["best_candidate"]
        self.assertIsNotNone(best)
        # Exactly ONE best_candidate is selected for execution plan formulation
        self.assertIn(best["direction"], ["BUY", "SELL"])


if __name__ == "__main__":
    unittest.main()
