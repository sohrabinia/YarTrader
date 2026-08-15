import unittest
from datetime import datetime, timedelta
from src.ShadowTrading.Domain.VirtualAccount import VirtualAccount
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionStatus, PositionResult
from src.ShadowTrading.Engine.PositionManager import PositionManager
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
from src.ShadowTrading.Services.TradeEvaluator import TradeEvaluator
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem

class TestShadowTradingEngine(unittest.TestCase):
    """
    Comprehensive test suite verifying the YarTrader Shadow Trading Engine.
    Covers Virtual Account, Position Lifecycle, SL/TP simulation, and full E2E Integration.
    """

    def setUp(self) -> None:
        self.engine = ShadowTradingEngine.get_instance()
        self.engine.reset_account(10000.0)

    # 1. Virtual Account Tests
    def test_account_creation_and_balance_tracking(self) -> None:
        account = VirtualAccount(initial_balance=5000.0)
        self.assertEqual(account.balance, 5000.0)
        self.assertEqual(account.equity, 5000.0)
        self.assertEqual(len(account.get_open_positions()), 0)
        self.assertEqual(len(account.get_closed_positions()), 0)

    def test_account_equity_recalculation(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)

        # Open a virtual BUY position
        pos = VirtualPosition(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            volume=1.0,
            stop_loss=1985.0,
            take_profit=2030.0
        )
        account.add_position(pos)

        # Price goes in favor of BUY (2000.0 -> 2005.0)
        pos.update_price(2005.0)
        account.recalculate()

        # PnL = (2005 - 2000) * 100 * 1 = 500.0
        self.assertEqual(pos.profit_loss, 500.0)
        self.assertEqual(account.balance, 10000.0)
        self.assertEqual(account.equity, 10500.0)

    # 2. Position Lifecycle Tests
    def test_position_open_and_close_lifecycle(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)
        pos = VirtualPosition(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            volume=1.0,
            stop_loss=1.0900,
            take_profit=1.1200
        )
        self.assertEqual(pos.status, PositionStatus.OPEN)

        # Update price to some normal monitoring state
        pos.update_price(1.1050)
        self.assertEqual(pos.status, PositionStatus.MONITORING)

        # Close manually
        pos.close(PositionResult.WIN, close_price=1.1100)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.WIN)

    # 3. TP/SL Simulation Tests
    def test_buy_win_tp_trigger(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)
        manager = PositionManager(account)

        pos = manager.open_virtual_position(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            volume=1.0,
            stop_loss=1980.0,
            take_profit=2020.0
        )

        # Update price to hit TP
        closed = manager.update_prices_and_evaluate("XAUUSD", 2025.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.WIN)
        self.assertGreater(pos.profit_loss, 0.0)
        self.assertEqual(account.balance, 10000.0 + pos.profit_loss)

    def test_buy_loss_sl_trigger(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)
        manager = PositionManager(account)

        pos = manager.open_virtual_position(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            volume=1.0,
            stop_loss=1980.0,
            take_profit=2020.0
        )

        # Update price to hit SL
        closed = manager.update_prices_and_evaluate("XAUUSD", 1975.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.LOSS)
        self.assertLess(pos.profit_loss, 0.0)
        self.assertEqual(account.balance, 10000.0 + pos.profit_loss)

    def test_sell_win_tp_trigger(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)
        manager = PositionManager(account)

        pos = manager.open_virtual_position(
            symbol="XAUUSD",
            direction="SELL",
            entry_price=2000.0,
            volume=1.0,
            stop_loss=2020.0,
            take_profit=1980.0
        )

        # Price goes down (in favor of SELL)
        closed = manager.update_prices_and_evaluate("XAUUSD", 1970.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.WIN)
        self.assertGreater(pos.profit_loss, 0.0)

    def test_sell_loss_sl_trigger(self) -> None:
        account = VirtualAccount(initial_balance=10000.0)
        manager = PositionManager(account)

        pos = manager.open_virtual_position(
            symbol="XAUUSD",
            direction="SELL",
            entry_price=2000.0,
            volume=1.0,
            stop_loss=2020.0,
            take_profit=1980.0
        )

        # Price goes up (against SELL)
        closed = manager.update_prices_and_evaluate("XAUUSD", 2025.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(pos.status, PositionStatus.CLOSED)
        self.assertEqual(pos.result, PositionResult.LOSS)
        self.assertLess(pos.profit_loss, 0.0)

    # 4. E2E Integration Test
    def test_full_decision_to_experience_integration(self) -> None:
        # Mock Decision Intelligence output
        decision_action = "BUY"
        confidence = 72.0
        reason = "Matched similar historical continuation pattern signature"
        evidence_payload = {
            "signature": [2000.0, 1995.0, 2010.0],
            "historical_cases": 850
        }

        # Ingest Decision
        pos = self.engine.handle_decision(
            decision_action=decision_action,
            current_price=2000.0,
            confidence=confidence,
            reason=reason,
            evidence=evidence_payload,
            symbol="XAUUSD",
            volume=1.0,
            stop_loss=1990.0,
            take_profit=2020.0
        )

        self.assertIsNotNone(pos)
        self.assertEqual(pos.symbol, "XAUUSD")
        self.assertEqual(pos.direction, "BUY")
        self.assertEqual(pos.status, PositionStatus.OPEN)

        # Trigger SL Close via market price tick update
        closed_list = self.engine.update_market_price("XAUUSD", 1985.0)
        self.assertEqual(len(closed_list), 1)

        # Verify position is CLOSED with LOSS
        closed_pos = closed_list[0]
        self.assertEqual(closed_pos.status, PositionStatus.CLOSED)
        self.assertEqual(closed_pos.result, PositionResult.LOSS)

        # Verify Experience Memory has been created & persisted in the memory system
        experiences = self.engine.memory_system.get_experiences()
        target_exp = [e for e in experiences if e.meta.get("position_id") == closed_pos.position_id]
        self.assertEqual(len(target_exp), 1)

        exp = target_exp[0]
        self.assertEqual(exp.symbol, "XAUUSD")
        self.assertEqual(exp.decision_action, "BUY")
        self.assertEqual(exp.outcome_result, "FAILURE")
        self.assertEqual(exp.max_adverse_excursion, closed_pos.profit_loss)
        self.assertIn("Structural Error", exp.lesson_feedback)
