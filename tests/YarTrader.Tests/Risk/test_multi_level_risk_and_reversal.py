import unittest
from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine
from src.Risk.Services.reversal_handoff import ReversalHandoffManager

class TestMultiLevelRiskAndReversal(unittest.TestCase):
    """
    Phase 5 & Phase 6 Deterministic Risk & Reversal Tests.
    Proves:
    - 0.5% max risk per trade limit.
    - 3.0% strategy exposure ceiling.
    - 10.0% max daily equity drawdown circuit breaker (halts new trade generation).
    - FAST_SCALP / SCALP post-close opposite direction evaluation (prohibiting blind reversal).
    """

    def setUp(self) -> None:
        self.portfolio_engine = PortfolioRiskIntelligenceEngine(
            max_risk_per_trade_pct=0.5,
            max_strategy_exposure_ceiling_pct=3.0,
            max_daily_drawdown_pct=10.0
        )
        self.reversal_manager = ReversalHandoffManager()

    def test_single_trade_risk_limit_0_5_percent(self):
        """Verifies single trade risk exceeding 0.5% equity is rejected."""
        active_trades = [
            {"symbol": "XAUUSD", "status": "RUNNING", "entry": 2000.0, "stop": 1990.0, "volume": 0.01, "risk_pct": 0.8}
        ]
        res = self.portfolio_engine.calculate_portfolio_risk(active_trades, virtual_balance=10000.0)
        self.assertFalse(res["approved"])
        self.assertTrue(any("Single trade risk exceeds max limit" in v for v in res["violations"]))

    def test_combined_strategy_exposure_ceiling_3_percent(self):
        """Verifies combined strategy portfolio heat exceeding 3.0% equity is rejected."""
        # 4 trades each taking 1.0% heat = 4.0% > 3.0%
        active_trades = [
            {"symbol": "XAUUSD", "status": "RUNNING", "entry": 2000.0, "stop": 1900.0, "volume": 0.01, "risk_pct": 0.4},
            {"symbol": "EURUSD", "status": "RUNNING", "entry": 1.0800, "stop": 1.0700, "volume": 0.10, "risk_pct": 0.4},
            {"symbol": "GBPUSD", "status": "RUNNING", "entry": 1.2500, "stop": 1.2400, "volume": 0.10, "risk_pct": 0.4},
            {"symbol": "USDJPY", "status": "RUNNING", "entry": 150.00, "stop": 149.00, "volume": 0.10, "risk_pct": 0.4}
        ]
        res = self.portfolio_engine.calculate_portfolio_risk(active_trades, virtual_balance=10000.0)
        self.assertFalse(res["approved"])

    def test_max_daily_drawdown_limit_10_percent_breaker(self):
        """Verifies 10.0% max daily equity drawdown halts new trade generation."""
        active_trades = []
        # Start of day equity = 10,000, daily PnL = -1,050 (-10.5% drawdown)
        res = self.portfolio_engine.calculate_portfolio_risk(
            active_trades,
            virtual_balance=8950.0,
            start_of_day_equity=10000.0,
            daily_pnl=-1050.0
        )
        self.assertFalse(res["approved"])
        self.assertTrue(any("Trading halted" in v for v in res["violations"]))

    def test_fast_scalp_and_scalp_reversal_requires_market_structure(self):
        """
        Verifies post-close FAST_SCALP/SCALP reversal requires fresh market structure validation.
        Prohibits blind reversal if RTM zone or Fractal Base is missing.
        """
        closed_trade_buy = {
            "symbol": "XAUUSD",
            "trading_style": "FAST_SCALP",
            "direction": "BUY",
            "exit_reason": "TAKE_PROFIT_HIT",
            "exit_price": 2020.0
        }

        # Case A: Blind reversal without market structure confirmation -> REJECTED
        market_structure_blind = {"has_rtm_zone": False, "has_fractal_base": False}
        res_blind = self.reversal_manager.evaluate_reversal_candidate(
            closed_position=closed_trade_buy,
            market_structure=market_structure_blind,
            account_equity=10000.0,
            free_margin=9000.0
        )
        self.assertFalse(res_blind.is_candidate)
        self.assertIn("lacks RTM zone or Fractal Base structural confirmation", res_blind.reason)

        # Case B: Validated reversal with RTM supply zone -> ACCEPTED for SHORT
        market_structure_valid = {
            "has_rtm_zone": True,
            "has_fractal_base": True,
            "suggested_sl_pips": 20,
            "suggested_tp_pips": 60,
            "win_probability": 0.60
        }
        res_valid = self.reversal_manager.evaluate_reversal_candidate(
            closed_position=closed_trade_buy,
            market_structure=market_structure_valid,
            account_equity=10000.0,
            free_margin=9000.0
        )
        self.assertTrue(res_valid.is_candidate)
        self.assertEqual(res_valid.reversal_direction, "SELL")

if __name__ == "__main__":
    unittest.main()
