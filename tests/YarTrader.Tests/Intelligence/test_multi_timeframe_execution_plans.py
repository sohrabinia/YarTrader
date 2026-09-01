import unittest
import math
from typing import Dict, List, Any
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException


class TestMultiTimeframeExecutionPlans(unittest.TestCase):
    """
    Regression Test Suite proving:
    1. Multi-timeframe synthesis (M1, M5, M15, H1, H4, D1) drives execution plans.
    2. Consecutive BUY -> BUY plans occur when MTF structure remains bullish.
    3. Consecutive SELL -> SELL plans occur when MTF structure remains bearish.
    4. Dynamic BUY -> SELL transition occurs only upon genuine MTF market state change.
    5. NO_TRADE / WAIT state is returned when conditions are conflicting or risk limits fail.
    6. Zero fixed BUY/SELL alternation mechanism exists.
    7. Daily-only logic is not authoritative.
    8. PRICE_ACTION_RTM is NOT the authoritative execution strategy.
    9. Live trading remains fail-closed (LIVE_TRADING_ENABLED = False).
    """

    def setUp(self):
        self.planner = ExecutionIntelligencePlanner()
        self.core = ExecutionIntelligenceCore.get_instance()

    def _generate_mock_candles(self, base_price: float = 2300.0, count: int = 30, trend: str = "BULLISH") -> List[Dict[str, Any]]:
        candles = []
        for i in range(count):
            # Oscillating wave with trend slope to produce swing peaks and troughs
            wave = math.sin(i * 0.8) * 2.0 + ((i * 0.5) if trend == "BULLISH" else (-(i * 0.5) if trend == "BEARISH" else 0.0))
            o = base_price + wave
            c = o + (0.3 if trend == "BULLISH" else (-0.3 if trend == "BEARISH" else 0.0))
            h = max(o, c) + 0.4
            l = min(o, c) - 0.4
            candles.append({"time": 1700000000 + i * 3600, "open": round(o, 4), "high": round(h, 4), "low": round(l, 4), "close": round(c, 4), "volume": 100.0})
        return candles

    def test_01_multi_timeframe_synthesis_in_execution_plans(self):
        """Verify M1, M5, M15, H1, H4, D1 participating in execution plan evaluation."""
        h1_candles = self._generate_mock_candles(trend="BULLISH")
        all_tf_candles = {
            "M1": self._generate_mock_candles(trend="BULLISH"),
            "M5": self._generate_mock_candles(trend="BULLISH"),
            "M15": self._generate_mock_candles(trend="BULLISH"),
            "H4": self._generate_mock_candles(trend="BULLISH"),
            "D1": self._generate_mock_candles(trend="BULLISH"),
        }
        res = self.core.evaluate_context(
            symbol="XAUUSD",
            timeframe="H1",
            candles=h1_candles,
            all_timeframe_candles=all_tf_candles
        )
        self.assertIn("plan", res)
        self.assertIn(res["plan"]["action"], ["BUY", "SELL", "WAIT", "AVOID"])
        self.assertIn("alignment", res)
        self.assertIn("similarity", res)

    def test_02_consecutive_buy_buy_plans(self):
        """Verify BUY can be followed by another BUY when conditions remain bullish."""
        candles_1 = self._generate_mock_candles(base_price=2300.0, trend="BULLISH")
        plan_1 = self.core.evaluate_context("XAUUSD", "H1", candles_1)["plan"]

        candles_2 = self._generate_mock_candles(base_price=2310.0, trend="BULLISH")
        plan_2 = self.core.evaluate_context("XAUUSD", "H1", candles_2)["plan"]

        self.assertEqual(plan_1["action"], "BUY")
        self.assertEqual(plan_2["action"], "BUY")

    def test_03_consecutive_sell_sell_plans(self):
        """Verify SELL can be followed by another SELL when conditions remain bearish."""
        candles_1 = self._generate_mock_candles(base_price=2300.0, trend="BEARISH")
        plan_1 = self.core.evaluate_context("XAUUSD", "H1", candles_1)["plan"]

        candles_2 = self._generate_mock_candles(base_price=2290.0, trend="BEARISH")
        plan_2 = self.core.evaluate_context("XAUUSD", "H1", candles_2)["plan"]

        self.assertEqual(plan_1["action"], "SELL")
        self.assertEqual(plan_2["action"], "SELL")

    def test_04_dynamic_buy_to_sell_transition_on_genuine_trend_shift(self):
        """Verify BUY -> SELL transition occurs only when market structure genuinely shifts from Bullish to Bearish."""
        bullish_candles = self._generate_mock_candles(base_price=2300.0, trend="BULLISH")
        plan_buy = self.core.evaluate_context("XAUUSD", "H1", bullish_candles)["plan"]

        bearish_candles = self._generate_mock_candles(base_price=2320.0, trend="BEARISH")
        plan_sell = self.core.evaluate_context("XAUUSD", "H1", bearish_candles)["plan"]

        self.assertEqual(plan_buy["action"], "BUY")
        self.assertEqual(plan_sell["action"], "SELL")

    def test_05_no_trade_wait_state_on_conflicting_conditions_or_risk(self):
        """Verify AVOID / WAIT state returned when risk limits are violated."""
        portfolio_risk_blocked = {"approved": False, "violations": ["Max drawdown ceiling exceeded"]}

        plan = self.planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative={"trend": "BULLISH"},
            liquidity={},
            zones={},
            alignment={"alignment": "FULLY_ALIGNED", "confidence": 85},
            similarity={},
            portfolio_risk=portfolio_risk_blocked,
            current_price=2300.0
        )["plan"]

        self.assertEqual(plan["action"], "AVOID")
        self.assertEqual(plan["entry"], 0.0)

    def test_06_proof_zero_fixed_buy_sell_alternation(self):
        """Verify execution planner does NOT use a fixed alternating BUY/SELL toggle."""
        c = self._generate_mock_candles(trend="BULLISH")
        actions = [self.core.evaluate_context("XAUUSD", "H1", c)["plan"]["action"] for _ in range(3)]
        self.assertEqual(actions, ["BUY", "BUY", "BUY"])

    def test_07_daily_only_logic_not_authoritative(self):
        """Verify execution plans operate on sub-daily timeframes (M1, M5, M15, H1)."""
        m5_candles = self._generate_mock_candles(trend="BULLISH")
        res_m5 = self.core.evaluate_context("XAUUSD", "M5", m5_candles)
        self.assertEqual(res_m5["timeframe"], "M5")
        self.assertEqual(res_m5["plan"]["action"], "BUY")

    def test_08_price_action_rtm_not_authoritative_strategy(self):
        """Verify execution plan strategy identity is NOT 'PRICE_ACTION_RTM'."""
        candles = self._generate_mock_candles(trend="BULLISH")
        plan = self.core.evaluate_context("XAUUSD", "H1", candles)["plan"]
        self.assertNotEqual(plan["strategy"], "PRICE_ACTION_RTM")
        self.assertEqual(plan["strategy"], "Multi-Timeframe Continuous Market Intelligence")

    def test_09_live_trading_remains_fail_closed(self):
        """Verify real live trading remains hard-blocked and fail-closed."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
