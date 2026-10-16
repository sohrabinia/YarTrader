import os
import tempfile
import unittest
from unittest.mock import patch

from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch
from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine


class TestScopedExplorationRisk(unittest.TestCase):
    def test_daily_loss_limit_defaults_to_production_policy(self):
        with patch.dict(os.environ, {}, clear=True):
            switch = DailyLossKillSwitch(persistence_path=tempfile.mktemp(suffix=".json"))
            self.assertEqual(switch.effective_max_daily_loss_pct(), 10.0)

    def test_sixty_percent_only_when_all_demo_exploration_flags_are_explicit(self):
        env = {
            "YARTRADER_DEMO_EXPLORATION_MODE": "true",
            "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
            "YARTRADER_TRADING_MODE": "DEMO",
        }
        with patch.dict(os.environ, env, clear=True):
            switch = DailyLossKillSwitch(persistence_path=tempfile.mktemp(suffix=".json"))
            self.assertEqual(switch.effective_max_daily_loss_pct(), 60.0)
            from datetime import datetime, timezone
            session_key, _, _ = switch.get_session_key_and_window(datetime.now(timezone.utc))
            self.assertTrue(switch.set_session_baseline(1000.0, session_key))
            allowed, reason, meta = switch.evaluate_daily_loss(
                1000.0, bot_daily_pnl=-550.0
            )
            self.assertTrue(allowed)
            self.assertIsNone(reason)
            self.assertEqual(meta["max_daily_loss_pct"], 60.0)
            self.assertEqual(meta["loss_pct"], 55.0)

    def test_sixty_percent_limit_blocks_at_sixty_percent_loss(self):
        env = {
            "YARTRADER_DEMO_EXPLORATION_MODE": "true",
            "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
            "YARTRADER_TRADING_MODE": "DEMO",
        }
        with patch.dict(os.environ, env, clear=True):
            switch = DailyLossKillSwitch(persistence_path=tempfile.mktemp(suffix=".json"))
            from datetime import datetime, timezone
            session_key, _, _ = switch.get_session_key_and_window(datetime.now(timezone.utc))
            self.assertTrue(switch.set_session_baseline(1000.0, session_key))
            allowed, reason, meta = switch.evaluate_daily_loss(1000.0, bot_daily_pnl=-600.0)
            self.assertFalse(allowed)
            self.assertEqual(reason, "DAILY_LOSS_LIMIT_REACHED")
            self.assertEqual(meta["max_daily_loss_pct"], 60.0)

    def test_portfolio_threshold_argument_is_honored_and_default_stays_ten(self):
        self.assertEqual(PortfolioRiskIntelligenceEngine().max_daily_drawdown_pct, 10.0)
        self.assertEqual(PortfolioRiskIntelligenceEngine(max_daily_drawdown_pct=60.0).max_daily_drawdown_pct, 60.0)

    def test_autonomy_policy_requires_explicit_demo_flags_and_live_disabled(self):
        from src.Execution.Safety.demo_exploration_policy import demo_exploration_autonomy_enabled
        env = {
            "YARTRADER_DEMO_EXPLORATION_MODE": "true",
            "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
            "YARTRADER_TRADING_MODE": "DEMO",
            "LIVE_TRADING_ENABLED": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(demo_exploration_autonomy_enabled())
            os.environ["LIVE_TRADING_ENABLED"] = "true"
            self.assertFalse(demo_exploration_autonomy_enabled())
            os.environ["LIVE_TRADING_ENABLED"] = "false"
            os.environ["YARTRADER_TRADING_MODE"] = "LIVE"
            self.assertFalse(demo_exploration_autonomy_enabled())

    def test_demo_exploration_requires_demo_mode_and_opt_in(self):
        from src.Decision.Intelligence.base_reaction_decision_engine import _demo_exploration_enabled
        with patch.dict(os.environ, {
            "YARTRADER_DEMO_EXPLORATION_MODE": "true",
            "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
            "YARTRADER_TRADING_MODE": "DEMO",
        }, clear=True):
            self.assertTrue(_demo_exploration_enabled())
            os.environ["YARTRADER_TRADING_MODE"] = "LIVE"
            self.assertFalse(_demo_exploration_enabled())


if __name__ == "__main__":
    unittest.main()
