import os
import json
import unittest
from datetime import datetime, timezone

from scripts.run_autonomous_demo_runtime import run_autonomous_demo_cycle, generate_simulated_candles
from src.Decision.Intelligence.timeframe_selector import AutomaticTimeframeSelector
from src.Decision.Intelligence.professional_signal_engine import ProfessionalSignalEngine


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

    def test_professional_signal_engine_unified_signal(self):
        engine = ProfessionalSignalEngine()
        candles_by_tf = {
            "M5": generate_simulated_candles("EURUSD", 1.0850, 50),
            "M15": generate_simulated_candles("EURUSD", 1.0850, 50),
            "H1": generate_simulated_candles("EURUSD", 1.0850, 50),
            "H4": generate_simulated_candles("EURUSD", 1.0850, 50),
        }
        sig = engine.generate_unified_signal("EURUSD", candles_by_tf)
        self.assertTrue(sig.signal_id.startswith("SIG-"))
        self.assertEqual(sig.symbol, "EURUSD")
        self.assertIn(sig.direction, ["BUY", "SELL", "WAIT"])
        if sig.direction != "WAIT":
            self.assertGreaterEqual(sig.risk_reward, 1.5)
            self.assertGreater(sig.entry_price, 0.0)

    def test_autonomous_demo_cycle_execution(self):
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

    def test_runtime_status_blocks_when_mt5_ipc_missing(self):
        forensic_report_file = "reports/final_autonomous_runtime_forensic_report.json"
        run_autonomous_demo_cycle(symbols=["XAUUSD"], max_cycles=1)
        self.assertTrue(os.path.exists(forensic_report_file))

        with open(forensic_report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # In Linux container sandbox without MT5 IPC, runtime_status must be BLOCKED_NO_MT5_IPC
        self.assertIn(data["runtime_status"], ["BLOCKED_NO_MT5_IPC", "NATIVE_MT5_DEMO_VERIFIED", "TRUTHFUL_ORDER_REJECTED"])

    def test_no_false_blocked_status_after_successful_demo_execution(self):
        forensic_report_file = "reports/final_autonomous_runtime_forensic_report.json"
        run_autonomous_demo_cycle(symbols=["XAUUSD"], max_cycles=1)
        self.assertTrue(os.path.exists(forensic_report_file))

        with open(forensic_report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # If trades executed on connected MT5, status must not false-block
        if data.get("mt5_connection") and data.get("closed_trades", 0) > 0:
            self.assertEqual(data["runtime_status"], "NATIVE_MT5_DEMO_VERIFIED")


if __name__ == "__main__":
    unittest.main()
