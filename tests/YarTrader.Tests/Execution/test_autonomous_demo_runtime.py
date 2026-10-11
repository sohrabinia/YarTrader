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

    def test_base_reaction_number_counts_causal_contiguous_m1_visits(self):
        child = {"confirmation_time": 100, "base_low": 10.0, "base_high": 20.0}
        candles = [
            {"timestamp": 90, "low": 12.0, "high": 18.0},   # before Base confirmation
            {"timestamp": 110, "low": 12.0, "high": 18.0},  # visit 1
            {"timestamp": 120, "low": 11.0, "high": 19.0},  # same contiguous visit
            {"timestamp": 130, "low": 21.0, "high": 22.0},  # outside zone
            {"timestamp": 140, "low": 12.0, "high": 18.0},  # visit 2
            {"timestamp": 160, "low": 12.0, "high": 18.0},  # beyond causal cutoff
        ]
        self.assertEqual(AutonomousDemoTrader._next_reaction_number(candles, child, 150), 3)

    def test_latest_base_reaction_measures_actual_side_depth_and_visit_number(self):
        child = {"event_id": "M15:100:RBR", "confirmation_time": 100,
                 "base_low": 10.0, "base_high": 20.0}
        candles = [
            {"timestamp": 90, "low": 24.0, "high": 26.0, "close": 25.0},
            {"timestamp": 110, "low": 17.0, "high": 26.0, "close": 18.0},
            {"timestamp": 120, "low": 19.0, "high": 21.0, "close": 20.0},
            {"timestamp": 130, "low": 21.0, "high": 22.0, "close": 21.5},
            {"timestamp": 140, "low": 15.0, "high": 22.0, "close": 16.0},
            {"timestamp": 160, "low": 10.0, "high": 11.0, "close": 10.5},
        ]
        measured = AutonomousDemoTrader._measure_latest_base_reaction(candles, child, 150)
        self.assertEqual(measured["reaction_number"], 2)
        self.assertEqual(measured["entry_side"], "FROM_ABOVE")
        self.assertAlmostEqual(measured["penetration_fraction"], 0.5)
        self.assertEqual(measured["start_time"], 140)

    def test_base_reaction_number_fails_closed_on_invalid_zone(self):
        candles = [{"timestamp": 110, "low": 1.0, "high": 2.0}]
        child = {"confirmation_time": 100, "base_low": 3.0, "base_high": 2.0}
        self.assertEqual(AutonomousDemoTrader._next_reaction_number(candles, child, 150), 1)


if __name__ == "__main__":
    unittest.main()
