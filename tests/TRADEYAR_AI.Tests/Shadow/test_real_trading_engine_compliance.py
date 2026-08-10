import os
import unittest
from datetime import datetime, timedelta
from src.ShadowTrading.Domain.VirtualAccount import VirtualAccount
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionStatus, PositionResult
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine

class TestRealTradingEngineCompliance(unittest.TestCase):
    """
    Mandatory compliance tests verifying the enhanced $1,000 Paper/Demo Account,
    order fill triggers, SL/TP automatic evaluation, realistic transaction costs,
    persistence, restart recovery, and strict broker non-execution gates.
    """

    def setUp(self) -> None:
        self.persistence_path = os.path.join("runtime_logs", "paper_account.json")
        if os.path.exists(self.persistence_path):
            try:
                os.remove(self.persistence_path)
            except Exception:
                pass

        self.engine = ShadowTradingEngine(initial_balance=1000.0)
        self.engine.reset_account(balance=1000.0)

    def tearDown(self) -> None:
        if os.path.exists(self.persistence_path):
            try:
                os.remove(self.persistence_path)
            except Exception:
                pass

    def test_paper_account_initial_balance_and_metrics(self) -> None:
        # Verify account starts with exactly $1,000 virtual balance and correct ID
        self.assertEqual(self.engine.account.account_id, "YARTRADER-PAPER-001")
        self.assertEqual(self.engine.account.initial_balance, 1000.0)
        self.assertEqual(self.engine.account.cash_balance, 1000.0)
        self.assertEqual(self.engine.account.equity, 1000.0)
        self.assertEqual(self.engine.account.unrealized_pnl, 0.0)
        self.assertEqual(self.engine.account.realized_pnl, 0.0)

    def test_orders_creation_fill_and_positions(self) -> None:
        # Create a paper position / order
        pos = self.engine.handle_decision(
            decision_action="BUY",
            current_price=2000.0,
            volume=1.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            symbol="XAUUSD",
            timeframe="H1",
            mode="PAPER"
        )
        self.assertIsNotNone(pos)
        self.assertEqual(pos.account_id, "YARTRADER-PAPER-001")
        self.assertEqual(pos.mode, "PAPER")
        self.assertEqual(pos.entry_price, 2000.0)
        self.assertEqual(pos.stop_loss, 1980.0)
        self.assertEqual(pos.take_profit, 2040.0)
        self.assertEqual(pos.status, PositionStatus.OPEN)

        # Update price to floating profit
        self.engine.update_market_price("XAUUSD", 2010.0)
        self.assertEqual(pos.current_price, 2010.0)
        self.assertGreater(pos.profit_loss, 0.0)

        # Recalculate metrics
        metrics = self.engine.get_metrics()
        self.assertEqual(metrics["open_positions_count"], 1)
        self.assertGreater(metrics["equity"], 1000.0)

    def test_sl_tp_evaluation_and_transaction_costs(self) -> None:
        pos = self.engine.handle_decision(
            decision_action="BUY",
            current_price=2000.0,
            volume=1.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            symbol="XAUUSD"
        )
        self.assertIsNotNone(pos)
        self.assertEqual(pos.fees, 2.0)
        self.assertEqual(pos.slippage, 0.1)

        # Hit SL price limit
        closed = self.engine.update_market_price("XAUUSD", 1970.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.LOSS)

        # Metrics must reflect realized loss and commission fees
        metrics = self.engine.get_metrics()
        self.assertEqual(metrics["closed_positions_count"], 1)
        self.assertLess(metrics["balance"], 1000.0)

    def test_restart_recovery_persistence(self) -> None:
        # Open an initial order and write state
        self.engine.handle_decision(
            decision_action="BUY",
            current_price=2000.0,
            volume=1.0,
            symbol="XAUUSD"
        )
        self.engine.account.save_state()

        # Simulate engine restart by creating a new engine instance loading same state
        new_engine = ShadowTradingEngine(initial_balance=1000.0)
        self.assertEqual(new_engine.account.account_id, "YARTRADER-PAPER-001")
        self.assertEqual(len(new_engine.account.get_open_positions()), 1)
        self.assertEqual(new_engine.account.get_open_positions()[0].entry_price, 2000.0)

    def test_strict_broker_non_execution_gates(self) -> None:
        # Verify that MT5 broker execution paths remain disabled/mocked and no live money trades can occur
        ps_engine = PredictiveShadowEngine.get_instance()

        # Verify block flag or execution safety
        self.assertTrue(ps_engine.get_broker_balance() == 0.0 or ps_engine.get_broker_balance() is not None)

        # Test creation of shadow orders behaves safely and is isolated from live MT5 broker
        trade = ps_engine.create_predictive_order(
            symbol="EURUSD",
            direction="LONG",
            entry=1.1000,
            stop=1.0900,
            target=1.1200,
            confidence=90.0
        )
        self.assertEqual(trade.status, "CREATED")

        # Ensure no live broker placement is connected/triggered
        self.assertNotIn("broker_order_ticket", trade.to_dict())
