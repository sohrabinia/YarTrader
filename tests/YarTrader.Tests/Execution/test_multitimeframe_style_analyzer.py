import unittest

from src.Intelligence.Execution.multi_timeframe_style_analyzer import (
    MultiTimeframeStyleAnalyzer,
    _candle_trigger,
)


class TestMultiTimeframeStyleAnalyzer(unittest.TestCase):
    @staticmethod
    def _flat_bars(count=80, start=1_700_000_000, step=60):
        rows = []
        for i in range(count):
            price = 100.0
            rows.append({"timestamp": start + i * step, "open": price,
                         "high": price + 0.5, "low": price - 0.5,
                         "close": price + (0.05 if i % 2 else -0.05)})
        return rows

    def test_both_styles_are_exposed_and_fail_closed_without_macro_context(self):
        frames = {tf: self._flat_bars() for tf in
                  ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")}
        now = max(row["timestamp"] for row in frames["M1"]) + 1
        results = MultiTimeframeStyleAnalyzer().evaluate(
            "EURUSD", frames, {"bid": 99.99, "ask": 100.01}, now
        )
        self.assertEqual(set(results), {"RTM", "PRICE_ACTION", "SCALP"})
        for name in ("RTM", "PRICE_ACTION"):
            self.assertEqual(results[name]["status"], "WAIT")
            self.assertFalse(results[name]["execution_enabled"])
            self.assertIsNone(results[name]["order_plan"])
            self.assertIn("context", results[name]["reason"].lower())

    def test_directional_engulfing_trigger_uses_closed_candle_geometry(self):
        bullish = [
            {"time": 0, "open": 101, "high": 102, "low": 100, "close": 101.5},
            {"time": 1, "open": 102, "high": 103, "low": 99, "close": 100},
            {"time": 2, "open": 99.5, "high": 104, "low": 99, "close": 103.5},
        ]
        bearish = [
            {"time": 0, "open": 101, "high": 102, "low": 100, "close": 101.5},
            {"time": 1, "open": 100, "high": 103, "low": 99, "close": 102},
            {"time": 2, "open": 102.5, "high": 103, "low": 98, "close": 98.5},
        ]
        self.assertEqual(_candle_trigger(bullish), 1)
        self.assertEqual(_candle_trigger(bearish), -1)

    def test_future_candle_frame_is_not_used(self):
        frames = {tf: self._flat_bars() for tf in
                  ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")}
        now = max(row["timestamp"] for row in frames["M1"]) - 1
        results = MultiTimeframeStyleAnalyzer().evaluate(
            "XAUUSD", frames, {"bid": 1999.9, "ask": 2000.1}, now
        )
        self.assertEqual(set(results), {"RTM", "PRICE_ACTION", "SCALP"})
        self.assertTrue(all(item["status"] == "WAIT" for item in results.values()))


if __name__ == "__main__":
    unittest.main()
