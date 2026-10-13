import os
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts.run_autonomous_demo_runtime import run_autonomous_demo_cycle, generate_simulated_candles
from src.Decision.Intelligence.timeframe_selector import AutomaticTimeframeSelector
from src.Decision.Intelligence.professional_signal_engine import ProfessionalSignalEngine
from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader


class TestAutonomousDemoRuntime(unittest.TestCase):

    def setUp(self):
        self.report_file = "reports/autonomous_demo_runtime_report.json"

    def test_post_exit_tracker_records_price_path_after_sl_or_tp(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        import time
        from src.Execution.Services import autonomous_demo_trader as trader_module

        now = int(time.time())
        adapter = MagicMock()
        adapter._mt5 = SimpleNamespace(
            DEAL_ENTRY_IN=0, DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3,
            DEAL_REASON_SL=4, DEAL_REASON_TP=5, DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        )
        adapter.get_history_deals.return_value = [
            {"ticket": 10, "position_id": 99, "symbol": "XAUUSD", "magic": 100001,
             "entry": 0, "type": 0, "reason": 3, "time": now - 300, "price": 1998.0, "profit": 0.0},
            {"ticket": 11, "position_id": 99, "symbol": "XAUUSD", "magic": 100001,
             "entry": 1, "type": 1, "reason": 4, "time": now - 30, "price": 1995.0, "profit": -30.0},
        ]
        trader = AutonomousDemoTrader(adapter=adapter)
        with TemporaryDirectory() as folder, patch.object(trader_module, "_PROJECT_ROOT", Path(folder)):
            trader._track_post_exit_market_path("XAUUSD", {"bid": 1996.0, "ask": 1996.2})
            saved = json.loads((Path(folder) / "runtime_logs" / "post_exit_price_tracking.json").read_text())
        self.assertIn("11", saved)
        self.assertEqual(saved["11"]["exit_reason"], "STOP_LOSS")
        self.assertEqual(saved["11"]["direction"], "BUY")
        self.assertEqual(len(saved["11"]["observations"]), 1)
        self.assertGreater(saved["11"]["max_favorable_move"], 0)

    def test_structural_profit_protection_uses_confirmed_swing_and_only_tightens(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        adapter = MagicMock()
        adapter._mt5 = SimpleNamespace(POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1)
        trader = AutonomousDemoTrader(adapter=adapter)
        position = {"type": 0, "price_open": 100.5, "sl": 99.5,
                    "time": 102, "time_msc": 102000, "ticket": 77}
        lows = [100.8, 101.4, 101.3, 101.0, 101.2, 101.5, 101.3, 101.6]
        candles = [{"timestamp": 101 + i, "open": low + 0.2,
                    "high": low + 0.5, "low": low, "close": low + 0.3}
                   for i, low in enumerate(lows)]
        candidate = trader._candidate_structural_trailing_stop(
            position, candles, {"bid": 102.0, "ask": 102.02},
            {"point": 0.01, "trade_stops_level": 0},
        )
        self.assertAlmostEqual(candidate, 101.26, places=6)

        # If the stop has already advanced beyond the latest swing-based candidate,
        # the manager never loosens it or falls back to an older/wider swing.
        position["sl"] = 101.3
        self.assertIsNone(trader._candidate_structural_trailing_stop(
            position, candles, {"bid": 102.0, "ask": 102.02},
            {"point": 0.01, "trade_stops_level": 0},
        ))

    def test_automatic_timeframe_selector(self):
        selector = AutomaticTimeframeSelector()
        candles_by_tf = {
            "M5": generate_simulated_candles("XAUUSD", 2350.0, 50),
            "M15": generate_simulated_candles("XAUUSD", 2350.0, 50),
            "H1": generate_simulated_candles("XAUUSD", 2350.0, 50),
            "H4": generate_simulated_candles("XAUUSD", 2350.0, 50),
        }
        res = selector.select_best_timeframe("XAUUSD", candles_by_tf)
        self.assertIn(res.selected_timeframe, ["M5", "M15", "H1", "H4"])
        self.assertGreaterEqual(res.confidence, 0.50)

    @patch("src.Decision.Intelligence.professional_signal_engine.BrainLearningBridge.record_signal")
    def test_professional_signal_engine_unified_signal(self, mock_record_signal):
        """Legacy API delegates to Base-only model and fails closed without learned profiles."""
        engine = ProfessionalSignalEngine()
        candles_by_tf = {
            "M5": generate_simulated_candles("EURUSD", 1.0850, 50),
            "M15": generate_simulated_candles("EURUSD", 1.0850, 50),
            "H1": generate_simulated_candles("EURUSD", 1.0850, 50),
            "H4": generate_simulated_candles("EURUSD", 1.0850, 50),
        }
        sig = engine.generate_unified_signal("EURUSD", candles_by_tf)
        self.assertEqual(sig.direction, "WAIT")
        self.assertEqual(sig.pattern_id, "BASE_WAIT")
        mock_record_signal.assert_not_called()

    def test_autonomous_demo_cycle_execution(self):
        # This unit test uses synthetic candles; never connect to or submit orders
        # to the operator's real MT5 DEMO account from the test runner.
        with patch("scripts.run_autonomous_demo_runtime.RealMT5BrokerAdapter") as adapter_factory, \
             patch("src.Decision.Intelligence.professional_signal_engine.BrainLearningBridge.record_signal"), \
             patch("scripts.run_autonomous_demo_runtime.FractalPatternMemory") as fractal_factory, \
             patch("scripts.run_autonomous_demo_runtime.TradeJournalManager.get_instance") as journal_factory:
            adapter = adapter_factory.return_value
            adapter._initialized = False
            adapter.get_terminal_info.return_value = None
            fractal_factory.return_value.memory = {}
            journal = journal_factory.return_value
            journal.get_all_records.return_value = []
            journal.journal_file = "test_journal.json"
            run_autonomous_demo_cycle(symbols=["XAUUSD"], max_cycles=1)
        self.assertTrue(os.path.exists(self.report_file))

        with open(self.report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertGreaterEqual(data["signals_generated"], 1)
        self.assertGreaterEqual(len(data["timeframes_used"]), 1)
        self.assertIn("performance_metrics", data)
        self.assertIn("expectancy", data["performance_metrics"])

    def test_performance_analytics_engine(self):
        from src.Strategy.Evaluation.performance_analytics import PerformanceAnalyticsEngine
        from src.Execution.Services.trade_journal import TradeJournalRecord

        engine = PerformanceAnalyticsEngine()
        records = [
            TradeJournalRecord(
                decision_id="DEC-1", trade_id="TR-1", cycle_id="CYC-1", symbol="XAUUSD", timeframe="M15",
                direction="BUY", planned_entry=2350.0, planned_sl=2340.0, planned_tp=2370.0, planned_rr=2.0,
                actual_entry=2350.0, actual_exit=2370.0, volume=0.01, confidence=0.85, reasoning=["Setup"],
                evidence={}, order_ticket="101", deal_ticket="1001", open_time="2026-08-23T10:00:00Z",
                close_time="2026-08-23T10:05:00Z", exit_reason="TP HIT", pnl=20.0, pnl_percent=2.0,
                mfe=0.0, mae=0.0, duration=300.0, market_regime="TRENDING", result="WIN", configuration_version="v1.2.0"
            ),
            TradeJournalRecord(
                decision_id="DEC-2", trade_id="TR-2", cycle_id="CYC-1", symbol="XAUUSD", timeframe="M15",
                direction="SELL", planned_entry=2350.0, planned_sl=2360.0, planned_tp=2330.0, planned_rr=2.0,
                actual_entry=2350.0, actual_exit=2360.0, volume=0.01, confidence=0.85, reasoning=["Setup"],
                evidence={}, order_ticket="102", deal_ticket="1002", open_time="2026-08-23T10:10:00Z",
                close_time="2026-08-23T10:15:00Z", exit_reason="SL HIT", pnl=-10.0, pnl_percent=-1.0,
                mfe=0.0, mae=0.0, duration=300.0, market_regime="TRENDING", result="LOSS", configuration_version="v1.2.0"
            )
        ]

        metrics = engine.calculate_metrics(records)
        self.assertEqual(metrics.total_trades, 2)
        self.assertEqual(metrics.wins, 1)
        self.assertEqual(metrics.losses, 1)
        self.assertEqual(metrics.win_rate, 50.0)
        self.assertEqual(metrics.average_win, 20.0)
        self.assertEqual(metrics.average_loss, 10.0)
        self.assertEqual(metrics.profit_factor, 2.0)
        self.assertEqual(metrics.expectancy, 5.0)  # (0.5 * 20.0) - (0.5 * 10.0) = 5.0

    @patch("src.Intelligence.Execution.strategy_orchestrator.StrategyOrchestrator.evaluate_all_strategies")
    def test_demo_plan_delegates_to_canonical_base_orchestrator(self, evaluate):
        from unittest.mock import MagicMock
        evaluate.return_value = {
            "symbol": "XAUUSD", "primary_timeframe": "M1", "candidates": [],
            "best_candidate": None, "base_plan": {"status": "WAIT", "reason": "Model not validated"},
            "hierarchy": {"structure": {}},
            "reaction_analysis": {"status": "WAIT", "execution_enabled": False},
            "model_status": "REACTION_MODEL_NOT_ACTIVATED",
            "summary": "No validated Base-only reaction proposal.",
        }
        trader = AutonomousDemoTrader(adapter=MagicMock())
        bars = [{"timestamp": 100, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5}]
        result = trader._evaluate_hierarchical_base_plan(
            {"M1": bars}, {"time": 100, "bid": 100.4, "ask": 100.5}, symbol="XAUUSD"
        )
        evaluate.assert_called_once()
        self.assertEqual(result["decision_authority"], "NONE")
        self.assertEqual(result["status"], "WAIT")
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["model_status"], "REACTION_MODEL_NOT_ACTIVATED")
        self.assertEqual(set(result["strategy_results"]), {"BASE_HIERARCHY", "RTM", "PRICE_ACTION"})
        self.assertEqual(result["execution_mode"], "INDEPENDENT_STRATEGIES_SHARED_RISK_GATE")


    @patch("src.Intelligence.Execution.strategy_orchestrator.StrategyOrchestrator.evaluate_all_strategies")
    def test_executable_plan_preserves_broker_take_profit(self, evaluate):
        from unittest.mock import MagicMock
        evaluate.return_value = {
            "symbol": "XAUUSD", "primary_timeframe": "M1", "candidates": [],
            "best_candidate": {"strategy_name": "BASE_HIERARCHY", "direction": "BUY"},
            "base_plan": {
                "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
                "entry": 1998.0, "stop_loss": 1995.0, "take_profit": 2007.0,
                "net_reward_risk": 1.5,
            },
            "hierarchy": {"structure": {
                "hierarchy_complete_to_m1": True,
                "parent_base_id": "H1:parent", "child_base_id": "M5:child",
                "micro_base_id": "M1:micro",
            }, "order_plan": {"take_profit": 2007.0}},
            "reaction_analysis": {"order_plan": {"take_profit": 2007.0}},
            "model_status": "COSTED_REACTION_MODEL_LOADED", "summary": "qualified",
        }
        trader = AutonomousDemoTrader(adapter=MagicMock())
        bars = [{"timestamp": 100, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5}]
        result = trader._evaluate_hierarchical_base_plan(
            {"M1": bars}, {"time": 100, "bid": 2000.0, "ask": 2000.2}, symbol="XAUUSD"
        )
        self.assertEqual(result["status"], "ORDER_PROPOSAL")
        self.assertEqual(result["order_plan"]["take_profit"], 2007.0)
        self.assertNotIn("reward_target_estimate", result["order_plan"])
        self.assertEqual(result["base_plan"]["take_profit"], 2007.0)
        self.assertEqual(result["hierarchy"]["order_plan"]["take_profit"], 2007.0)
        self.assertEqual(result["reaction_analysis"]["order_plan"]["take_profit"], 2007.0)

        # A plausible candidate must still be blocked when the MTF parent/child/M1
        # chain is absent; reaction-only exploration is not an execution fallback.
        evaluate.return_value["hierarchy"]["structure"] = {}
        blocked = trader._evaluate_hierarchical_base_plan(
            {"M1": bars}, {"time": 100, "bid": 2000.0, "ask": 2000.2}, symbol="XAUUSD"
        )
        self.assertEqual(blocked["status"], "WAIT")
        self.assertEqual(blocked["order_plan"]["status"], "WAIT")

    def test_stale_pending_trigger_is_blocked_before_broker_dispatch(self):
        """A crossed pending trigger must not be submitted as an unintended immediate entry."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.get_active_orders.return_value = []
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {
            "status": "ORDER_PROPOSAL",
            "order_plan": {
                "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
                "entry": 2500.3, "stop_loss": 2490.3, "take_profit": None,
                "net_reward_risk": 1.5, "expires_at": 2000,
            },
        }
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2500.0, "ask": 2500.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0}, {"digits": 2},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("trigger is no longer valid", result["reason"])
        adapter.send_order_to_broker.assert_not_called()

    def test_wait_cycle_does_not_cancel_existing_pending_order(self):
        """A transient WAIT/no-new-signal cycle must retain a broker-accepted pending order."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.get_active_orders.return_value = [{
            "magic": 100001, "comment": "YarBase", "ticket": 778899,
            "type": 2, "price_open": 1998.0, "sl": 1995.0, "tp": 0.0,
            "time_expiration": 4000,
        }]
        trader = AutonomousDemoTrader(adapter=adapter)
        result = trader._reconcile_base_pending_order(
            "XAUUSD",
            {"status": "WAIT", "reason": "No parent base this cycle"},
            {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2},
        )
        self.assertEqual(result["status"], "ALREADY_PENDING")
        self.assertEqual(result["retained_pending_orders"], [778899])
        self.assertEqual(result["cancelled_pending_orders"], [])
        adapter.cancel_pending_order.assert_not_called()
        adapter.send_order_to_broker.assert_not_called()

    @patch.dict(os.environ, {
        "YARTRADER_DEMO_EXPLORATION_MODE": "true",
        "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
        "YARTRADER_TRADING_MODE": "DEMO",
        "LIVE_TRADING_ENABLED": "false",
    })
    def test_exploration_keeps_existing_order_even_when_new_proposal_differs(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY_LIMIT = 2
        adapter.get_active_orders.return_value = [{
            "magic": 100001, "comment": "YarBase", "ticket": 55501, "type": 2,
            "price_open": 1998.0, "sl": 1995.0, "tp": 0.0,
            "time_expiration": 0,
        }]
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
            "entry": 1997.5, "stop_loss": 1994.5, "take_profit": None,
            "net_reward_risk": 0.4, "expires_at": 5000,
        }}
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0}, {"digits": 2},
        )
        self.assertEqual(result["status"], "ALREADY_PENDING")
        self.assertEqual(result["retained_pending_orders"], [55501])
        adapter.cancel_pending_order.assert_not_called()
        adapter.send_order_to_broker.assert_not_called()

    @patch.dict(os.environ, {
        "YARTRADER_DEMO_EXPLORATION_MODE": "true",
        "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
        "YARTRADER_TRADING_MODE": "DEMO",
        "LIVE_TRADING_ENABLED": "false",
    })
    def test_new_pending_order_has_no_preset_tp_and_uses_volatility_aware_stop(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY_LIMIT = 2
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(
            Status="Placed", OrderId=98765, Comment="accepted", Retcode=10009
        )
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
            "entry": 1998.0, "stop_loss": 1994.5, "take_profit": None,
            "net_reward_risk": 1.5, "expires_at": 5000,
        }}
        def bars(rng):
            return [{"timestamp": 100 + i * 30, "open": 2000.0, "high": 2000.0 + rng / 2,
                     "low": 2000.0 - rng / 2, "close": 2000.0} for i in range(20)]
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0},
            per_tf={"M5": bars(2.0), "M15": bars(4.0)},
        )
        self.assertEqual(result["status"], "PENDING_PLACED")
        request = adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.StopLoss, 1994.5)
        self.assertEqual(request.TakeProfit, 0.0)

    def test_same_pending_order_without_preset_tp_is_reused(self):
        """A TP-free pending order is retained for strategy-managed exits."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY_LIMIT = 2
        adapter.get_active_orders.return_value = [{
            "magic": 100001, "comment": "YarBase", "ticket": 12345, "type": 2,
            "price_open": 1998.0, "sl": 1995.0, "tp": 0.0,
            "time_expiration": 0,
        }]
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
            "entry": 1998.0, "stop_loss": 1995.0, "take_profit": None,
            "net_reward_risk": 1.5, "expires_at": 5000,
        }}
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0}, {"digits": 2},
        )
        self.assertEqual(result["status"], "ALREADY_PENDING")
        self.assertEqual(result["ticket"], 12345)
        adapter.cancel_pending_order.assert_not_called()
        adapter.send_order_to_broker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
if __name__ == "__main__":
    unittest.main()
