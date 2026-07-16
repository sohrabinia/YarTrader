import unittest
from src.Infrastructure.exceptions import ValidationException
from src.Application.Dashboard.control_center import (
    ControlCenterAggregator,
    SymbolMetadata,
    SymbolManager,
    OperatingModeManager
)


class TestAdminControlCenter(unittest.TestCase):
    """
    Unit and integration tests for the Administrative Control Center & Operational Dashboard.
    """

    def setUp(self) -> None:
        self.aggregator = ControlCenterAggregator()

    def test_operating_mode_transitions_and_rules(self) -> None:
        """Verify operating mode safety, confirmations, and logging rules."""
        mode_mgr = self.aggregator.mode_manager
        self.assertEqual(mode_mgr.active_mode, "Research") # default safe

        # Safe transition
        mode_mgr.set_mode("Shadow")
        self.assertEqual(mode_mgr.active_mode, "Shadow")

        # LiveTrading without confirmation triggers Security Error
        with self.assertRaises(ValidationException) as context:
            mode_mgr.set_mode("LiveTrading", live_confirmation=False)
        self.assertIn("requires explicit confirmation", str(context.exception))

        # LiveTrading with confirmation succeeds
        mode_mgr.set_mode("LiveTrading", live_confirmation=True)
        self.assertEqual(mode_mgr.active_mode, "LiveTrading")
        self.assertEqual(len(mode_mgr.mode_logs), 2)

    def test_symbol_administration(self) -> None:
        """Verify additions, configurations editing, disabling, and deletions of symbols."""
        sym_mgr = self.aggregator.symbol_manager

        # Initial symbols
        symbols = sym_mgr.list_symbols()
        self.assertEqual(len(symbols), 2)
        self.assertTrue(sym_mgr.validate_symbol_connection("XAUUSD"))

        # Add new symbol
        new_sym = SymbolMetadata("BTCUSD", "BTCUSD_m", "Crypto", ["M1", "H1"])
        sym_mgr.add_symbol(new_sym)
        self.assertEqual(len(sym_mgr.list_symbols()), 3)
        self.assertTrue(sym_mgr.validate_symbol_connection("BTCUSD"))

        # Edit/Disable
        sym_mgr.disable_symbol("BTCUSD")
        self.assertFalse(sym_mgr._symbols["BTCUSD"].active)

        # Delete
        sym_mgr.delete_symbol("BTCUSD")
        self.assertEqual(len(sym_mgr.list_symbols()), 2)
        self.assertFalse(sym_mgr.validate_symbol_connection("BTCUSD"))

    def test_autonomous_runtime_state_controls(self) -> None:
        """Verify start, stop, pause, resume, and restart controls of background runtime."""
        control = self.aggregator.runtime_control
        self.assertEqual(control.status, "STOPPED")

        control.start()
        self.assertEqual(control.status, "RUNNING")

        control.pause()
        self.assertEqual(control.status, "PAUSED")

        control.resume()
        self.assertEqual(control.status, "RUNNING")

        control.restart()
        self.assertEqual(control.status, "RUNNING")

        control.stop()
        self.assertEqual(control.status, "STOPPED")

    def test_backtest_job_launcher_and_metrics(self) -> None:
        """Verify launching backtesting jobs and calculated metric updates."""
        backtest_mgr = self.aggregator.backtest_manager
        job_id = backtest_mgr.create_job("XAUUSD", "H1", "2026-01-01", "2026-06-01", 10000.0)

        job = backtest_mgr.jobs[job_id]
        self.assertEqual(job.status, "PENDING")

        backtest_mgr.execute_job(job_id)
        self.assertEqual(job.status, "COMPLETED")
        self.assertEqual(job.metrics["win_rate"], 0.65)
        self.assertEqual(job.metrics["sharpe_ratio"], 2.15)

    def test_risk_panel_and_emergency_stop_kill_switch(self) -> None:
        """Verify that emergency stop trigger locks down overall metrics."""
        risk_panel = self.aggregator.risk_panel
        self.assertFalse(risk_panel.emergency_stop_triggered)

        # Trigger emergency stop
        risk_panel.trigger_emergency_stop()
        self.assertTrue(risk_panel.emergency_stop_triggered)

        # Complete dashboard state reflects trigger and health score drops to 0
        state = self.aggregator.get_complete_dashboard_state()
        self.assertTrue(state["emergency_stop_active"])
        self.assertEqual(state["metrics"]["health_score"], 0.0)
