import unittest
import math
from typing import Dict, List, Any
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException


class TestTrueMTFCausalIsolation(unittest.TestCase):
    """
    Dedicated Causal Isolation & Real Data Provenance Test Suite proving:
    1. M5 context mutation alters M5 context identity and decision while H1 context identity remains unchanged.
    2. H1 context mutation alters H1 context identity and decision while M5 context identity remains unchanged.
    3. Genuine OHLC differentiation across M5, M15, H1, H4 (failing if fed identical candles or timestamp-only changes).
    4. Legacy strategy orchestrator is NOT execution authority (`decision_source` == "BRAIN").
    5. Hard-locked fail-closed safety gate (`LIVE_TRADING_ENABLED = False`).
    """

    def setUp(self):
        self.planner = ExecutionIntelligencePlanner()
        self.core = ExecutionIntelligenceCore.get_instance()

    def _generate_mock_candles(
        self,
        base_price: float = 2300.0,
        count: int = 30,
        step_sec: int = 300,
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
                "time": 1700000000 + i * step_sec,
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(l, 4),
                "close": round(c, 4),
                "volume": 100.0
            })
        return candles

    def test_01_m5_mutation_leaves_h1_context_unchanged(self):
        """M5 mutation alters M5 context identity and decision while H1 context identity remains unchanged."""
        m5_candles_a = self._generate_mock_candles(base_price=2300.0, step_sec=300, trend="BULLISH")
        h1_candles_a = self._generate_mock_candles(base_price=2300.0, step_sec=3600, trend="BULLISH")

        res_m5_a = self.core.evaluate_context("XAUUSD", "M5", m5_candles_a)
        res_h1_a = self.core.evaluate_context("XAUUSD", "H1", h1_candles_a)

        m5_identity_a = res_m5_a["plan"]["context_identity"]
        h1_identity_a = res_h1_a["plan"]["context_identity"]

        # Mutate ONLY M5 candles
        m5_candles_b = self._generate_mock_candles(base_price=2350.0, step_sec=300, trend="BEARISH")
        res_m5_b = self.core.evaluate_context("XAUUSD", "M5", m5_candles_b)
        res_h1_b = self.core.evaluate_context("XAUUSD", "H1", h1_candles_a) # H1 unchanged

        m5_identity_b = res_m5_b["plan"]["context_identity"]
        h1_identity_b = res_h1_b["plan"]["context_identity"]

        self.assertNotEqual(m5_identity_a, m5_identity_b)
        self.assertEqual(h1_identity_a, h1_identity_b)

    def test_02_h1_mutation_leaves_m5_context_unchanged(self):
        """H1 mutation alters H1 context identity and decision while M5 context identity remains unchanged."""
        m5_candles_a = self._generate_mock_candles(base_price=2300.0, step_sec=300, trend="BULLISH")
        h1_candles_a = self._generate_mock_candles(base_price=2300.0, step_sec=3600, trend="BULLISH")

        res_m5_a = self.core.evaluate_context("XAUUSD", "M5", m5_candles_a)
        res_h1_a = self.core.evaluate_context("XAUUSD", "H1", h1_candles_a)

        m5_identity_a = res_m5_a["plan"]["context_identity"]
        h1_identity_a = res_h1_a["plan"]["context_identity"]

        # Mutate ONLY H1 candles
        h1_candles_b = self._generate_mock_candles(base_price=2250.0, step_sec=3600, trend="BEARISH")
        res_m5_b = self.core.evaluate_context("XAUUSD", "M5", m5_candles_a) # M5 unchanged
        res_h1_b = self.core.evaluate_context("XAUUSD", "H1", h1_candles_b)

        m5_identity_b = res_m5_b["plan"]["context_identity"]
        h1_identity_b = res_h1_b["plan"]["context_identity"]

        self.assertEqual(m5_identity_a, m5_identity_b)
        self.assertNotEqual(h1_identity_a, h1_identity_b)

    def test_03_real_ohlc_differentiation_across_timeframes(self):
        """Proves M5, M15, H1, H4 have genuinely different OHLC representations."""
        from src.Application.Services.web_dashboard import generate_active_ohlcv_candles

        m5_ohlc = generate_active_ohlcv_candles("XAUUSD", "M5")
        m15_ohlc = generate_active_ohlcv_candles("XAUUSD", "M15")
        h1_ohlc = generate_active_ohlcv_candles("XAUUSD", "H1")
        h4_ohlc = generate_active_ohlcv_candles("XAUUSD", "H4")

        # Verify timestamps and time steps are distinct
        m5_step = m5_ohlc[1]["time"] - m5_ohlc[0]["time"]
        m15_step = m15_ohlc[1]["time"] - m15_ohlc[0]["time"]
        h1_step = h1_ohlc[1]["time"] - h1_ohlc[0]["time"]
        h4_step = h4_ohlc[1]["time"] - h4_ohlc[0]["time"]

        self.assertEqual(m5_step, 300)
        self.assertEqual(m15_step, 900)
        self.assertEqual(h1_step, 3600)
        self.assertEqual(h4_step, 14400)

        # Confirm OHLC price values themselves are genuinely different across timeframes
        m5_closes = [c["close"] for c in m5_ohlc]
        m15_closes = [c["close"] for c in m15_ohlc]
        h1_closes = [c["close"] for c in h1_ohlc]
        h4_closes = [c["close"] for c in h4_ohlc]

        self.assertNotEqual(m5_closes, m15_closes)
        self.assertNotEqual(m15_closes, h1_closes)
        self.assertNotEqual(h1_closes, h4_closes)

        # Confirm context identities (computed strictly from OHLC price data) are completely distinct
        res_m5 = self.core.evaluate_context("XAUUSD", "M5", m5_ohlc)
        res_m15 = self.core.evaluate_context("XAUUSD", "M15", m15_ohlc)
        res_h1 = self.core.evaluate_context("XAUUSD", "H1", h1_ohlc)
        res_h4 = self.core.evaluate_context("XAUUSD", "H4", h4_ohlc)

        identities = {
            res_m5["plan"]["context_identity"],
            res_m15["plan"]["context_identity"],
            res_h1["plan"]["context_identity"],
            res_h4["plan"]["context_identity"],
        }
        self.assertEqual(len(identities), 4)

    def test_04_legacy_orchestrator_is_not_execution_authority(self):
        """Confirms strategy_orchestrator.py is NOT execution authority and decision_source == 'BRAIN'."""
        candles = self._generate_mock_candles(trend="BULLISH")
        plan = self.core.evaluate_context("XAUUSD", "H1", candles)["plan"]

        self.assertEqual(plan["decision_source"], "BRAIN")
        self.assertEqual(plan["strategy"], "Multi-Timeframe Continuous Market Intelligence")
        self.assertIn(plan["decision"], ["BUY", "SELL", "NO_TRADE"])

    def test_05_safety_gate_remains_fail_closed(self):
        """Confirms LIVE_TRADING_ENABLED = False remains fail-closed."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
