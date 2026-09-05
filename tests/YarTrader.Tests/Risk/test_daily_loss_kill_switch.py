import unittest
import os
import shutil
from datetime import datetime, timezone, timedelta
from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch, IRAN_TZ

class TestDailyLossKillSwitch(unittest.TestCase):
    """
    Test suite covering all 12 requirements for the YarTrader Daily 8% Loss Kill-Switch:
    1. Session starts at 01:35 Iran time.
    2. 00:00–00:24 belongs to the previous session.
    3. 00:25–01:34 does not allow new entries.
    4. Daily baseline is captured once per session at 01:35.
    5. 7.99% loss -> entry remains eligible.
    6. 8.00% loss -> entries blocked.
    7. Loss > 8.00% -> entries remain blocked.
    8. Once blocked, additional trade signals cannot open new positions.
    9. At next 01:35 session start, the daily loss state resets correctly.
    10. Reset does not occur at midnight (00:00).
    11. Restart/recovery does not accidentally reset daily baseline or bypass kill-switch.
    12. Existing Risk Engine / Trading Policy Gate behavior remains intact.
    """

    def setUp(self):
        self.test_dir = "runtime_logs/test_kill_switch"
        os.makedirs(self.test_dir, exist_ok=True)
        self.persistence_path = os.path.join(self.test_dir, "daily_loss_kill_switch.json")
        if os.path.exists(self.persistence_path):
            os.remove(self.persistence_path)
        self.kill_switch = DailyLossKillSwitch(persistence_path=self.persistence_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_iran_dt(self, year=2026, month=3, day=1, hour=1, minute=35, second=0):
        return datetime(year, month, day, hour, minute, second, tzinfo=IRAN_TZ)

    def test_01_session_starts_at_0135_iran_time(self):
        """1. Session starts at 01:35 Iran time & captures baseline equity."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        key, is_open, is_trans = self.kill_switch.get_session_key_and_window(dt_start)

        self.assertEqual(key, "2026-03-01")
        self.assertTrue(is_open)
        self.assertFalse(is_trans)

        res = self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["baseline_equity"], 10000.0)

    def test_02_midnight_0000_to_0024_belongs_to_previous_session(self):
        """2. 00:00-00:24 belongs to the previous session."""
        dt_midnight = self._create_iran_dt(day=2, hour=0, minute=10) # 00:10 on March 2
        key, is_open, is_trans = self.kill_switch.get_session_key_and_window(dt_midnight)

        self.assertEqual(key, "2026-03-01") # Belongs to March 1 session!
        self.assertTrue(is_open)
        self.assertFalse(is_trans)

    def test_03_transition_window_0025_to_0134_blocks_entries(self):
        """3. 00:25-01:34 does not allow new entries (SESSION_TRANSITION_WINDOW)."""
        dt_trans = self._create_iran_dt(day=2, hour=0, minute=45) # 00:45 on March 2
        key, is_open, is_trans = self.kill_switch.get_session_key_and_window(dt_trans)

        self.assertFalse(is_open)
        self.assertTrue(is_trans)

        res = self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_trans)
        self.assertFalse(res["allowed"])
        self.assertEqual(res["reason"], "SESSION_TRANSITION_WINDOW")

    def test_04_daily_baseline_captured_once_and_immutable(self):
        """4. Daily baseline is captured once per session and does not continuously move."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)

        dt_later = self._create_iran_dt(hour=10, minute=0)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9500.0, dt=dt_later)

        self.assertEqual(res["baseline_equity"], 10000.0) # Baseline remains $10,000!

    def test_05_loss_7_99_percent_remains_eligible(self):
        """5. 7.99% loss -> entry remains eligible."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)

        dt_check = self._create_iran_dt(hour=12, minute=0)
        # $10,000 - $799 = $9,201 (7.99% loss)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9201.0, dt=dt_check)

        self.assertTrue(res["allowed"])
        self.assertFalse(res["kill_switch_active"])
        self.assertAlmostEqual(res["daily_loss_pct"], 7.99, places=2)

    def test_06_loss_8_00_percent_triggers_kill_switch(self):
        """6. 8.00% loss -> entries blocked."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)

        dt_check = self._create_iran_dt(hour=12, minute=0)
        # $10,000 - $800 = $9,200 (8.00% loss)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9200.0, dt=dt_check)

        self.assertFalse(res["allowed"])
        self.assertTrue(res["kill_switch_active"])
        self.assertEqual(res["reason"], "DAILY_LOSS_LIMIT_REACHED")
        self.assertAlmostEqual(res["daily_loss_pct"], 8.00, places=2)

    def test_07_loss_greater_than_8_percent_remains_blocked(self):
        """7. Loss > 8% -> entries remain blocked."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)

        dt_check = self._create_iran_dt(hour=14, minute=0)
        # $10,000 - $1,000 = $9,000 (10.00% loss)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9000.0, dt=dt_check)

        self.assertFalse(res["allowed"])
        self.assertTrue(res["kill_switch_active"])
        self.assertEqual(res["reason"], "DAILY_LOSS_LIMIT_REACHED")

    def test_08_additional_signals_cannot_bypass_active_kill_switch(self):
        """8. Once blocked, additional trade signals cannot open new positions."""
        dt_start = self._create_iran_dt(hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_start)

        dt_trigger = self._create_iran_dt(hour=12, minute=0)
        self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=dt_trigger) # 9% loss -> active

        dt_signal = self._create_iran_dt(hour=15, minute=0)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9300.0, dt=dt_signal) # Equity recovered slightly to 7% loss

        # Block MUST remain active for the remainder of the session!
        self.assertFalse(res["allowed"])
        self.assertTrue(res["kill_switch_active"])
        self.assertEqual(res["reason"], "DAILY_LOSS_LIMIT_REACHED")

    def test_09_resets_at_next_0135_session_start(self):
        """9. At next 01:35 session start, the daily loss state resets correctly."""
        dt_day1 = self._create_iran_dt(day=1, hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_day1)
        self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=self._create_iran_dt(day=1, hour=12)) # Triggered

        # Next session starts at 01:35 on March 2
        dt_day2 = self._create_iran_dt(day=2, hour=1, minute=35)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=dt_day2)

        self.assertTrue(res["allowed"])
        self.assertFalse(res["kill_switch_active"])
        self.assertEqual(res["baseline_equity"], 9100.0) # Fresh baseline captured!

    def test_10_reset_does_not_occur_at_midnight(self):
        """10. Reset does NOT occur at midnight (00:00)."""
        dt_day1 = self._create_iran_dt(day=1, hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_day1)
        self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=self._create_iran_dt(day=1, hour=12)) # Triggered

        # Check at 00:00 on March 2
        dt_midnight = self._create_iran_dt(day=2, hour=0, minute=0)
        res = self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=dt_midnight)

        self.assertFalse(res["allowed"])
        self.assertTrue(res["kill_switch_active"]) # STILL BLOCKED!

    def test_11_restart_recovery_preserves_kill_switch_and_baseline(self):
        """11. Restart/recovery does not accidentally reset daily baseline or bypass kill-switch."""
        dt_day1 = self._create_iran_dt(day=1, hour=1, minute=35)
        self.kill_switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt_day1)
        self.kill_switch.evaluate_entry_allowed(current_equity=9100.0, dt=self._create_iran_dt(day=1, hour=12)) # Triggered

        # Instantiate fresh DailyLossKillSwitch object simulating process restart
        recovered_ks = DailyLossKillSwitch(persistence_path=self.persistence_path)
        dt_after_restart = self._create_iran_dt(day=1, hour=14, minute=0)
        res = recovered_ks.evaluate_entry_allowed(current_equity=9100.0, dt=dt_after_restart)

        self.assertFalse(res["allowed"])
        self.assertTrue(res["kill_switch_active"])
        self.assertEqual(res["baseline_equity"], 10000.0)

    def test_12_existing_risk_engine_integration(self):
        """12. Existing Risk Engine behavior remains intact."""
        from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
        risk_engine = ProfessionalRiskEngine()
        eval_res = risk_engine.evaluate_trade_risk(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2300.0,
            stop_loss=2297.0,
            take_profit=2310.0,
            account_balance=10000.0
        )
        self.assertTrue(eval_res.is_valid)

    def test_13_nan_inf_equity_and_baseline_rejected(self):
        """Test 13: Invalid/NaN/Inf current_equity or baseline are fail-closed and cannot replace baseline."""
        switch = DailyLossKillSwitch(persistence_path=self.persistence_path)
        dt = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)

        # Establish valid baseline $10,000.00 first
        res_valid = switch.evaluate_entry_allowed(current_equity=10000.0, dt=dt)
        self.assertTrue(res_valid["allowed"])
        self.assertEqual(switch.baseline_equity, 10000.0)

        # Attempt updating session state with invalid values
        invalid_equities = [float("nan"), float("inf"), float("-inf"), 0, -500, None, True, "invalid"]
        for inv_eq in invalid_equities:
            # Advance to new session date to test update_session_state
            dt_next = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
            switch.update_session_state(inv_eq, dt=dt_next)
            # Verify baseline remains $10,000.00 and is NOT replaced by invalid equity
            self.assertEqual(switch.baseline_equity, 10000.0)

            # Test evaluate_daily_loss fails closed
            allowed, reason, meta = switch.evaluate_daily_loss(inv_eq, now_utc=dt)
            self.assertFalse(allowed)

if __name__ == "__main__":
    unittest.main()
