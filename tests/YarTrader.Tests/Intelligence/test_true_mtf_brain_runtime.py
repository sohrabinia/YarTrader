import unittest
import math
from typing import Dict, List, Any
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine


class TestTrueMTFBrainRuntime(unittest.TestCase):
    """
    Dedicated True MTF Brain Regression Test Suite covering:
    1. Multi-timeframe synthesis across all standard horizons (M1, M5, M15, H1, H4, D1, W1, MN1).
    2. Same-direction re-entries (consecutive BUY -> BUY and SELL -> SELL).
    3. Dynamic trend transitions (BUY -> SELL and SELL -> BUY on genuine state shifts).
    4. Independent 0.5% max risk per trade calculation based on account equity.
    5. Legacy strategy isolation (confirming strategy identity is Multi-Timeframe Continuous Market Intelligence).
    6. Hard-locked fail-closed safety boundary (LIVE_TRADING_ENABLED = False).
    """

    def setUp(self):
        self.planner = ExecutionIntelligencePlanner()
        self.core = ExecutionIntelligenceCore.get_instance()
        self.risk_engine = ProfessionalRiskEngine()

    def _generate_mock_candles(
        self,
        base_price: float = 2300.0,
        count: int = 30,
        trend: str = "BULLISH"
    ) -> List[Dict[str, Any]]:
        candles = []
        for i in range(count):
            wave = math.sin(i * 0.8) * 2.0 + (
                (i * 0.5) if trend == "BULLISH" else (-(i * 0.5) if trend == "BEARISH" else 0.0)
            )
            o = base_price + wave
            c = o + (0.3 if trend == "BULLISH" else (-0.3 if trend == "BEARISH" else 0.0))
            h = max(o, c) + 0.4
            l = min(o, c) - 0.4
            candles.append({
                "time": 1700000000 + i * 3600,
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(l, 4),
                "close": round(c, 4),
                "volume": 100.0
            })
        return candles

    def test_01_multi_timeframe_horizon_synthesis(self):
        """Proves M1, M5, M15, H1, H4, D1, W1, MN1 horizon synthesis in execution evaluation."""
        h1_candles = self._generate_mock_candles(trend="BULLISH")
        all_tf = {
            tf: self._generate_mock_candles(trend="BULLISH")
            for tf in ["M1", "M5", "M15", "H4", "D1", "W1", "MN1"]
        }
        res = self.core.evaluate_context("XAUUSD", "H1", h1_candles, all_timeframe_candles=all_tf)

        self.assertEqual(res["symbol"], "XAUUSD")
        self.assertEqual(res["timeframe"], "H1")
        self.assertIn("plan", res)
        self.assertIn(res["plan"]["action"], ["BUY", "SELL", "WAIT", "AVOID"])
        self.assertEqual(res["plan"]["strategy"], "Multi-Timeframe Continuous Market Intelligence")

    def test_02_same_direction_buy_reentry(self):
        """Proves consecutive BUY -> BUY re-entries when market structure remains bullish."""
        c1 = self._generate_mock_candles(base_price=2300.0, trend="BULLISH")
        res1 = self.core.evaluate_context("XAUUSD", "H1", c1)

        c2 = self._generate_mock_candles(base_price=2310.0, trend="BULLISH")
        res2 = self.core.evaluate_context("XAUUSD", "H1", c2)

        self.assertEqual(res1["plan"]["action"], "BUY")
        self.assertEqual(res2["plan"]["action"], "BUY")

    def test_03_same_direction_sell_reentry(self):
        """Proves consecutive SELL -> SELL re-entries when market structure remains bearish."""
        all_tf_bearish = {
            tf: self._generate_mock_candles(base_price=2300.0, trend="BEARISH")
            for tf in ["M15", "H4", "D1"]
        }
        c1 = self._generate_mock_candles(base_price=2300.0, trend="BEARISH")
        res1 = self.core.evaluate_context("XAUUSD", "H1", c1, all_timeframe_candles=all_tf_bearish)

        c2 = self._generate_mock_candles(base_price=2290.0, trend="BEARISH")
        res2 = self.core.evaluate_context("XAUUSD", "H1", c2, all_timeframe_candles=all_tf_bearish)

        self.assertEqual(res1["plan"]["action"], "SELL")
        self.assertEqual(res2["plan"]["action"], "SELL")

    def test_04_dynamic_buy_to_sell_transition(self):
        """Proves dynamic BUY -> SELL transition on genuine market structure shift."""
        all_tf_bullish = {
            tf: self._generate_mock_candles(base_price=2300.0, trend="BULLISH")
            for tf in ["M15", "H4", "D1"]
        }
        c_bullish = self._generate_mock_candles(base_price=2300.0, trend="BULLISH")
        res_buy = self.core.evaluate_context("XAUUSD", "H1", c_bullish, all_timeframe_candles=all_tf_bullish)

        all_tf_bearish = {
            tf: self._generate_mock_candles(base_price=2320.0, trend="BEARISH")
            for tf in ["M15", "H4", "D1"]
        }
        c_bearish = self._generate_mock_candles(base_price=2320.0, trend="BEARISH")
        res_sell = self.core.evaluate_context("XAUUSD", "H1", c_bearish, all_timeframe_candles=all_tf_bearish)

        self.assertEqual(res_buy["plan"]["action"], "BUY")
        self.assertEqual(res_sell["plan"]["action"], "SELL")

    def test_05_independent_0_5_percent_max_risk_budget(self):
        """Proves 0.5% account equity risk calculation in risk engine."""
        account_equity = 100000.0 # $100,000 equity
        sizing_res = self.risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2300.0,
            stop_loss=2297.0, # $3.00 SL distance
            account_equity=account_equity,
            free_margin=100000.0,
            risk_pct=0.5
        )
        expected_budget = account_equity * 0.005 # $500.00

        self.assertTrue(sizing_res.is_valid)
        self.assertAlmostEqual(sizing_res.risk_budget_usd, expected_budget, places=2)
        self.assertGreater(sizing_res.volume_lots, 0.0)

    def test_06_legacy_strategy_isolation(self):
        """Proves legacy strategy identities (e.g. PRICE_ACTION_RTM, FAST_SCALP) are isolated."""
        c = self._generate_mock_candles(trend="BULLISH")
        plan = self.core.evaluate_context("XAUUSD", "H1", c)["plan"]

        self.assertNotEqual(plan["strategy"], "PRICE_ACTION_RTM")
        self.assertNotEqual(plan["strategy"], "FAST_SCALP")
        self.assertEqual(plan["strategy"], "Multi-Timeframe Continuous Market Intelligence")

    def test_07_fail_closed_safety_gate(self):
        """Proves live broker order execution remains fail-closed."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
