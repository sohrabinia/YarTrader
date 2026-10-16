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
        # Execution-path unit tests opt in explicitly; production remains watch-only
        # through YARTRADER_DEMO_ORDER_SUBMISSION_ENABLED=false in .env.production.
        self._order_submission_patch = patch.dict(os.environ, {"YARTRADER_DEMO_ORDER_SUBMISSION_ENABLED": "true"})
        self._order_submission_patch.start()
        self.addCleanup(self._order_submission_patch.stop)

    def test_watch_only_mode_journals_setup_without_sending_order(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.get_active_orders.return_value = []
        trader = AutonomousDemoTrader(adapter=adapter)
        trader._log_event = MagicMock()
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY",
                "order_plan": {"status": "PROPOSED", "direction": "SELL",
                               "order_type": "SELL_LIMIT", "entry": 1.1266,
                               "stop_loss": 1.1270, "take_profit": 1.1241}}
        with patch.dict(os.environ, {"YARTRADER_DEMO_ORDER_SUBMISSION_ENABLED": "false"}):
            result = trader._reconcile_base_pending_order(
                "EURUSD", plan, {"bid": 1.1260, "ask": 1.1261, "time": 1000},
                {"balance": 10000.0, "equity": 10000.0},
                {"digits": 5, "point": 0.00001})
        self.assertEqual(result["status"], "WATCH_ONLY")
        adapter.send_order_to_broker.assert_not_called()
        self.assertTrue(any(call.args[0].get("event") == "setup_zone_watch_only"
                            for call in trader._log_event.call_args_list))

    def test_demo_exploration_uses_lower_rr_floor_only_when_demo_exploration_is_enabled(self):
        from unittest.mock import MagicMock, patch
        trader = AutonomousDemoTrader(adapter=MagicMock())
        plan = {"execution_mode": "DEMO_STYLE_DISCOVERY"}
        with patch("src.Execution.Services.autonomous_demo_trader._demo_exploration_enabled", return_value=True):
            self.assertEqual(trader._minimum_net_rr_for_plan(plan), 0.20)
        with patch("src.Execution.Services.autonomous_demo_trader._demo_exploration_enabled", return_value=False):
            self.assertEqual(trader._minimum_net_rr_for_plan(plan), float(trader.MIN_RR))
        self.assertEqual(trader._minimum_net_rr_for_plan({"execution_mode": "PRODUCTION"}), float(trader.MIN_RR))

    def test_tp_extension_requires_confirmed_completed_m5_momentum_and_structure(self):
        from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader
        bullish = [
            {"open": 10.0, "high": 10.3, "low": 9.9, "close": 10.2},
            {"open": 10.2, "high": 10.5, "low": 10.1, "close": 10.4},
            {"open": 10.4, "high": 10.7, "low": 10.3, "close": 10.6},
            {"open": 10.6, "high": 10.8, "low": 10.5, "close": 10.7},  # forming; ignored
        ]
        bearish = [
            {"open": 10.6, "high": 10.8, "low": 10.4, "close": 10.5},
            {"open": 10.5, "high": 10.6, "low": 10.2, "close": 10.3},
            {"open": 10.3, "high": 10.4, "low": 10.0, "close": 10.1},
            {"open": 10.1, "high": 10.2, "low": 9.9, "close": 10.0},  # forming; ignored
        ]
        self.assertTrue(AutonomousDemoTrader._has_confirmed_tp_extension_momentum("BUY", {"M5": bullish}))
        self.assertTrue(AutonomousDemoTrader._has_confirmed_tp_extension_momentum("SELL", {"M5": bearish}))
        self.assertFalse(AutonomousDemoTrader._has_confirmed_tp_extension_momentum("BUY", {"M5": bearish}))
        self.assertFalse(AutonomousDemoTrader._has_confirmed_tp_extension_momentum("BUY", {"M5": bullish[:3]}))

    def test_zone_watch_state_requires_proximity_then_a_new_closed_candle_rejection(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import MagicMock, patch
        from src.Execution.Services import autonomous_demo_trader as trader_module

        trader = AutonomousDemoTrader(adapter=MagicMock())
        trader._log_event = MagicMock()
        plan = {"direction": "BUY", "entry": 100.0, "stop_loss": 99.0, "take_profit": 102.0}
        info = {"point": 0.01}
        far_tick = {"bid": 98.0, "ask": 98.02}
        near_tick = {"bid": 99.99, "ask": 100.01}
        bars_far = [
            {"timestamp": 1, "open": 98.0, "high": 98.3, "low": 97.8, "close": 98.1},
            {"timestamp": 2, "open": 98.1, "high": 98.2, "low": 97.9, "close": 98.0},
            {"timestamp": 3, "open": 98.0, "high": 98.1, "low": 97.8, "close": 97.9},
        ]
        with TemporaryDirectory() as folder, patch.object(trader_module, "_PROJECT_ROOT", Path(folder)):
            first = trader._advance_setup_zone_watch("EURUSD", "BASE_HIERARCHY", plan, far_tick, info, {"M1": bars_far})
            self.assertEqual(first["state"], "WAITING_FOR_ZONE")
            bars_near = bars_far + [
                {"timestamp": 4, "open": 99.8, "high": 100.2, "low": 99.5, "close": 100.1}
            ]
            second = trader._advance_setup_zone_watch("EURUSD", "BASE_HIERARCHY", plan, near_tick, info, {"M1": bars_near})
            self.assertEqual(second["state"], "NEAR_ZONE")
            self.assertFalse(second["reaction_confirmed"])
            # A distinct completed bullish rejection candle is required after the near-zone state.
            bars_reaction = bars_near + [
                {"timestamp": 5, "open": 99.95, "high": 100.3, "low": 99.7, "close": 100.15}
            ]
            third = trader._advance_setup_zone_watch("EURUSD", "BASE_HIERARCHY", plan, near_tick, info, {"M1": bars_reaction})
            self.assertEqual(third["state"], "REACTION_CONFIRMED")
            self.assertTrue(third["reaction_confirmed"])
            saved = json.loads((Path(folder) / "runtime_logs" / "setup_zone_watch_state_EURUSD_BASE_HIERARCHY.json").read_text(encoding="utf-8"))
            self.assertTrue(saved["EURUSD|BASE_HIERARCHY"]["reaction_confirmed"])

    def test_zone_watch_state_does_not_confirm_wrong_direction_candle(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import MagicMock, patch
        from src.Execution.Services import autonomous_demo_trader as trader_module

        trader = AutonomousDemoTrader(adapter=MagicMock())
        plan = {"direction": "SELL", "entry": 1.1000, "stop_loss": 1.1010, "take_profit": 1.0980}
        tick = {"bid": 1.09995, "ask": 1.10005}
        bars = [
            {"timestamp": 1, "open": 1.0990, "high": 1.0992, "low": 1.0988, "close": 1.0991},
            {"timestamp": 2, "open": 1.0991, "high": 1.0993, "low": 1.0989, "close": 1.0990},
            {"timestamp": 3, "open": 1.0990, "high": 1.0992, "low": 1.0988, "close": 1.0991},
        ]
        with TemporaryDirectory() as folder, patch.object(trader_module, "_PROJECT_ROOT", Path(folder)):
            trader._advance_setup_zone_watch("EURUSD", "RTM", plan, {"bid": 1.0980, "ask": 1.0981}, {"point": 0.00001}, {"M1": bars})
            near = trader._advance_setup_zone_watch("EURUSD", "RTM", plan, tick, {"point": 0.00001}, {"M1": bars})
            self.assertEqual(near["state"], "NEAR_ZONE")
            # Next closed candle is bullish, so it cannot confirm a SELL rejection.
            next_bars = bars + [{"timestamp": 4, "open": 1.0997, "high": 1.1003, "low": 1.0996, "close": 1.1001}]
            result = trader._advance_setup_zone_watch("EURUSD", "RTM", plan, tick, {"point": 0.00001}, {"M1": next_bars})
            self.assertEqual(result["state"], "NEAR_ZONE")
            self.assertFalse(result["reaction_confirmed"])

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

    def test_post_exit_tracker_does_not_infer_favorable_move_when_history_is_discovered_late(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        import time
        from src.Execution.Services import autonomous_demo_trader as trader_module

        now = int(time.time())
        adapter = MagicMock()
        adapter._mt5 = SimpleNamespace(
            DEAL_ENTRY_IN=0, DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3,
            DEAL_REASON_SL=4, DEAL_REASON_TP=5, DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        )
        adapter.get_history_deals.return_value = [
            {"ticket": 20, "position_id": 199, "symbol": "XAUUSD", "magic": 100001,
             "entry": 0, "type": 0, "reason": 3, "time": now-8000, "price": 1998.0, "profit": 0.0},
            {"ticket": 21, "position_id": 199, "symbol": "XAUUSD", "magic": 100001,
             "entry": 1, "type": 1, "reason": 4, "time": now-7200, "price": 1995.0, "profit": -30.0},
        ]
        trader = AutonomousDemoTrader(adapter=adapter)
        with TemporaryDirectory() as folder, patch.object(trader_module, "_PROJECT_ROOT", Path(folder)):
            trader._track_post_exit_market_path("XAUUSD", {"bid": 2050.0, "ask": 2050.2})
            saved = json.loads((Path(folder) / "runtime_logs" / "post_exit_price_tracking.json").read_text())
        self.assertTrue(saved["21"]["tracking_complete"])
        self.assertEqual(saved["21"]["tracking_status"], "SKIPPED_LATE_DISCOVERY")
        self.assertEqual(saved["21"]["observations"], [])
        self.assertEqual(saved["21"]["max_favorable_move"], 0.0)

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
        self.assertEqual(set(result["strategy_results"]), {"BASE_HIERARCHY", "RTM", "PRICE_ACTION", "SCALP", "BASE_ENGULF_REVERSAL", "MARKET_BEHAVIOR"})
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

    def test_stale_entry_plan_is_rejected_instead_of_chasing_market(self):
        """A market entry materially beyond the intended structural level must wait."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="123", DealTicket="456", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY",
            "entry": 2480.0, "stop_loss": 2470.0, "take_profit": None,
            "net_reward_risk": 1.5, "expires_at": 2000,
        }, "reaction_analysis": {"scenario": {"target": 2525.0}}}
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2500.0, "ask": 2500.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0, "trade_contract_size": 100.0},
        )
        self.assertEqual(result["status"], "WAIT")
        self.assertIn("moved 2.02R", result["reason"])
        adapter.send_order_to_broker.assert_not_called()

    def test_research_target_is_used_when_reaction_scenario_target_is_missing(self):
        """A strategy's research target may supply analysis, but still passes execution-owned R:R checks."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="321", DealTicket="654", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {
            "status": "ORDER_PROPOSAL", "selected_strategy": "BASE_ENGULF_REVERSAL",
            "order_plan": {"status": "PROPOSED", "direction": "BUY", "order_type": "BUY",
                           "entry": 2500.2, "stop_loss": 2490.3, "take_profit": None,
                           "net_reward_risk": 1.5, "expires_at": 2000},
            "reaction_analysis": {"scenario": {"target": None}},
            "strategy_results": {"BASE_ENGULF_REVERSAL": {"research_target": 2525.0}},
        }
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2500.0, "ask": 2500.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0, "trade_contract_size": 100.0},
        )
        self.assertEqual(result["status"], "MARKET_OPENED")
        adapter.send_order_to_broker.assert_called_once()
        request = adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "BUY")
        self.assertEqual(request.TakeProfit, 2525.0)  # validated analytical target is protected broker-side

    def test_wait_cycle_cancels_legacy_yartrader_pending_order(self):
        """Legacy bot-owned pending entries are removed after the market-entry migration."""
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.get_active_orders.return_value = [{"magic": 100001, "comment": "YarBase", "ticket": 778899,
                                                   "type": 2, "price_open": 1998.0, "sl": 1995.0, "tp": 0.0}]
        def cancel_and_refresh(*args, **kwargs):
            adapter.get_active_orders.return_value = []
            return MagicMock(Status="Cancelled", Comment="removed")
        adapter.cancel_pending_order.side_effect = cancel_and_refresh
        trader = AutonomousDemoTrader(adapter=adapter)
        result = trader._reconcile_base_pending_order(
            "XAUUSD", {"status": "WAIT", "reason": "No parent base this cycle"},
            {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0}, {"digits": 2},
        )
        self.assertEqual(result["status"], "WAIT")
        self.assertEqual(result["cancelled_legacy_pending_orders"], [778899])
        adapter.cancel_pending_order.assert_called_once_with(778899)
        adapter.send_order_to_broker.assert_not_called()

    def test_exploration_replaces_legacy_pending_with_protected_pending_order(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.ORDER_TYPE_BUY_LIMIT = 2
        adapter._mt5.ORDER_TYPE_SELL_LIMIT = 3
        adapter._mt5.ORDER_TYPE_BUY_STOP = 4
        adapter._mt5.ORDER_TYPE_SELL_STOP = 5
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = [{"magic": 100001, "comment": "YarBase", "ticket": 55501,
                                                   "type": 2, "price_open": 1998.0, "sl": 1995.0, "tp": 0.0}]
        def cancel_and_refresh(*args, **kwargs):
            adapter.get_active_orders.return_value = []
            return MagicMock(Status="Cancelled", Comment="removed")
        adapter.cancel_pending_order.side_effect = cancel_and_refresh
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="987", DealTicket="654", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
            "entry": 1999.5, "stop_loss": 1994.5, "take_profit": None,
            "net_reward_risk": 0.4, "expires_at": 5000,
        }, "reaction_analysis": {"scenario": {"target": 2012.0}}}
        def bars(rng):
            return [{"timestamp": 100 + i * 30, "open": 2000.0, "high": 2000.0 + rng / 2,
                     "low": 2000.0 - rng / 2, "close": 2000.0} for i in range(20)]
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "point": 0.01, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0, "trade_contract_size": 100.0},
            per_tf={"M5": bars(2.0), "M15": bars(4.0)},
        )
        self.assertEqual(result["status"], "PENDING_ORDER_SUBMITTED")
        adapter.cancel_pending_order.assert_called_once_with(55501)
        request = adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "BUY_LIMIT")
        self.assertEqual(request.Price, 1999.5)
        self.assertEqual(request.StopLoss, 1994.5)
        self.assertEqual(request.TakeProfit, 2012.0)
        self.assertEqual(request.Expiration, 4600)

    def test_new_market_entry_sets_validated_broker_tp_and_volatility_aware_stop(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="98765", DealTicket="12345", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY",
            "entry": 2000.2, "stop_loss": 1994.5, "take_profit": None,
            "net_reward_risk": 1.5, "expires_at": 5000,
        }, "reaction_analysis": {"scenario": {"target": 2012.0}}}
        def bars(rng):
            return [{"timestamp": 100 + i * 30, "open": 2000.0, "high": 2000.0 + rng / 2,
                     "low": 2000.0 - rng / 2, "close": 2000.0} for i in range(20)]
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0, "trade_contract_size": 100.0},
            per_tf={"M5": bars(2.0), "M15": bars(4.0)},
        )
        self.assertEqual(result["status"], "MARKET_OPENED")
        request = adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "BUY")
        self.assertEqual(request.Price, 2000.2)
        self.assertEqual(request.StopLoss, 1994.5)
        self.assertEqual(request.TakeProfit, 2012.0)

    def test_too_close_child_stop_rejects_out_of_envelope_parent_boundary(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_SELL_LIMIT = 3
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(
            Status="Placed", OrderId=98766, Comment="accepted", Retcode=10009
        )
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {
            "status": "ORDER_PROPOSAL",
            "order_plan": {
                "status": "PROPOSED", "direction": "SELL", "order_type": "SELL_LIMIT",
                "entry": 1.12012, "stop_loss": 1.12025, "take_profit": None,
                "gross_reward_risk": 24.0, "net_reward_risk": 16.0, "expires_at": 5000,
            },
            "structure": {"hierarchy_chain": [
                {"timeframe": "M5", "role": "SELECTED_CHILD", "base_low": 1.11989, "base_high": 1.1202},
                {"timeframe": "H1", "role": "INTERMEDIATE_BASE", "event_id": "H1:test", "base_low": 1.11855, "base_high": 1.1204},
                {"timeframe": "H4", "role": "INTERMEDIATE_BASE", "event_id": "H4:test", "base_low": 1.12119, "base_high": 1.12311},
                {"timeframe": "W1", "role": "MOTHER", "event_id": "W1:test", "base_low": 1.13616, "base_high": 1.14724},
            ]},
            "reaction_analysis": {"scenario": {"target": 1.11908}},
        }
        def bars(width):
            return [{"timestamp": 100 + i * 30, "open": 1.1200,
                     "high": 1.1200 + width / 2, "low": 1.1200 - width / 2,
                     "close": 1.1200} for i in range(20)]
        result = trader._reconcile_base_pending_order(
            "EURUSD", plan, {"bid": 1.1201, "ask": 1.1202, "time": 1000},
            {"balance": 2771.46, "equity": 2771.46},
            {"digits": 5, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0},
            per_tf={"M5": bars(0.0004), "M15": bars(0.0004)},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("net R:R", result["reason"])
        adapter.send_order_to_broker.assert_not_called()

    def test_legacy_pending_is_cancelled_before_market_entry(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = [{"magic": 100001, "comment": "YarBase", "ticket": 12345,
                                                   "type": 2, "price_open": 1998.0, "sl": 1995.0, "tp": 0.0}]
        def cancel_and_refresh(*args, **kwargs):
            adapter.get_active_orders.return_value = []
            return MagicMock(Status="Cancelled", Comment="removed")
        adapter.cancel_pending_order.side_effect = cancel_and_refresh
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="54321", DealTicket="67890", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY", "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY",
            "entry": 2000.2, "stop_loss": 1995.0, "take_profit": None,
            "net_reward_risk": 1.5, "expires_at": 5000,
        }, "reaction_analysis": {"scenario": {"target": 2012.0}}}
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 2000.0, "ask": 2000.2, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0, "trade_contract_size": 100.0},
        )
        self.assertEqual(result["status"], "MARKET_OPENED")
        adapter.cancel_pending_order.assert_called_once_with(12345)
        self.assertEqual(adapter.send_order_to_broker.call_args.args[0].OrderType, "BUY")


    def test_near_zone_confirmed_rejection_converts_pending_setup_to_market_entry(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._mt5.order_calc_profit.side_effect = lambda typ, sym, vol, entry, stop: -abs(entry - stop) * vol * 100
        adapter.get_active_orders.return_value = []
        adapter.send_order_to_broker.return_value = MagicMock(Status="Placed", OrderId="98767", DealTicket="12346", Comment="filled")
        trader = AutonomousDemoTrader(adapter=adapter)
        trader._log_event = MagicMock()
        trader._advance_setup_zone_watch = lambda *args, **kwargs: {
            "state": "REACTION_CONFIRMED", "reaction_confirmed": True,
            "distance_to_entry": 0.2, "proximity_tolerance": 0.5,
            "reaction_evidence": {"candle_timestamp": 970, "rejection": True},
        }
        plan = {"status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY", "order_plan": {
            "status": "PROPOSED", "direction": "SELL", "order_type": "SELL_LIMIT",
            "entry": 2000.1, "stop_loss": 2001.1, "take_profit": None,
            "net_reward_risk": 2.0, "expires_at": 5000,
        }, "reaction_analysis": {"scenario": {"target": 1993.0}}}
        def bars(rng):
            return [{"timestamp": 100 + i * 30, "open": 2000.0, "high": 2000.0 + rng / 2,
                     "low": 2000.0 - rng / 2, "close": 2000.0} for i in range(20)]
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 1999.9, "ask": 2000.0, "time": 1000},
            {"balance": 100000.0, "equity": 100000.0},
            {"digits": 2, "point": 0.01, "volume_min": 0.01, "volume_step": 0.01,
             "volume_max": 10.0, "trade_contract_size": 100.0},
            per_tf={"M5": bars(2.0), "M15": bars(4.0)},
        )
        self.assertEqual(result["status"], "MARKET_OPENED")
        request = adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "SELL")
        self.assertEqual(request.Price, 1999.9)
        decision_events = [call.args[0] for call in trader._log_event.call_args_list
                           if call.args and call.args[0].get("event") == "live_entry_context_decision"]
        self.assertEqual(decision_events[-1]["decision_mode"], "MARKET_AFTER_CONFIRMED_ZONE_REACTION")
        self.assertTrue(decision_events[-1]["reaction_confirmed"])
        self.assertFalse(decision_events[-1]["broker_confirmed"])


def test_explicit_structural_invalidation_cancels_finite_expiry_pending_order(monkeypatch):
    from unittest.mock import MagicMock
    # Exercise execution-enabled reconciliation explicitly; CI must not depend on local .env.production.
    monkeypatch.setenv("YARTRADER_DEMO_ORDER_SUBMISSION_ENABLED", "true")
    adapter = MagicMock()
    adapter.get_active_orders.return_value = [{
        "magic": 100001, "comment": "YarBaseRTM", "ticket": 778900,
        "type": 2, "price_open": 1.1240, "sl": 1.1230, "tp": 1.1260,
        "time_expiration": 5000,
    }]
    def cancel_and_refresh(*args, **kwargs):
        adapter.get_active_orders.return_value = []
        return MagicMock(Status="Cancelled", Comment="removed after structural invalidation")
    adapter.cancel_pending_order.side_effect = cancel_and_refresh
    trader = AutonomousDemoTrader(adapter=adapter)
    result = trader._reconcile_base_pending_order(
        "EURUSD", {"status": "WAIT", "reason": "Higher-timeframe structure opposes the RTM zone-departure direction."},
        {"bid": 1.1240, "ask": 1.1241, "time": 1000},
        {"balance": 10000.0, "equity": 10000.0}, {"digits": 5, "point": 0.00001},
    )
    assert result["status"] == "WAIT"
    adapter.cancel_pending_order.assert_called_once_with(778900)
    assert adapter.cancel_pending_order.call_count == 1
