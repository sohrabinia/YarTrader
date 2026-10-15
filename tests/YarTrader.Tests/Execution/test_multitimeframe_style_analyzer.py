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
        self.assertEqual(set(results), {"RTM", "PRICE_ACTION", "SCALP", "BASE_ENGULF_REVERSAL"})
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


    def test_base_engulf_reversal_detects_opposite_close_after_trend_departure(self):
        from src.Intelligence.Execution.multi_timeframe_style_analyzer import _base_engulf_reversal
        bars = []
        stamp = 1_700_000_000
        # Clear uptrend into a compact three-candle Base.
        for i in range(9):
            close = 100.0 + i
            bars.append({"time": stamp+i*60, "open": close-0.4, "high": close+0.1,
                         "low": close-0.5, "close": close})
        bars.extend([
            {"time": stamp+9*60, "open":108.8,"high":109.3,"low":108.7,"close":109.0},
            {"time": stamp+10*60,"open":109.0,"high":109.25,"low":108.85,"close":109.1},
            {"time": stamp+11*60,"open":109.1,"high":109.3,"low":108.8,"close":109.0},
            {"time": stamp+12*60,"open":109.0,"high":110.0,"low":108.95,"close":109.9},
        ])
        # Continue up without forming another compact Base, then engulf the whole
        # prior Base range and close below it on a completed bearish candle.
        for i in range(8):
            op = 110.0 + i*0.8
            bars.append({"time":stamp+(13+i)*60,"open":op,"high":op+0.9,"low":op-0.1,"close":op+0.8})
        for i in range(3):
            bars.append({"time":stamp+(21+i)*60,"open":116.0+i*0.1,"high":116.5+i*0.1,
                         "low":108.6,"close":108.7-i*0.05})
        result = _base_engulf_reversal(bars, now=bars[-1]["time"]+1)
        self.assertTrue(result["engulfed"])
        self.assertEqual(result["status"], "ENTRY_CANDIDATE")
        self.assertEqual(result["direction"], "SELL")
        self.assertEqual(result["trend_direction"], 1)

    def test_base_engulf_reversal_is_exposed_as_demo_proposal_on_its_own_timeframe(self):
        bars = []
        stamp = 1_700_000_000
        for i in range(9):
            close = 100.0 + i
            bars.append({"timestamp":stamp+i*60,"open":close-.4,"high":close+.1,"low":close-.5,"close":close})
        bars.extend([
            {"timestamp":stamp+9*60,"open":108.8,"high":109.3,"low":108.7,"close":109.0},
            {"timestamp":stamp+10*60,"open":109.0,"high":109.25,"low":108.85,"close":109.1},
            {"timestamp":stamp+11*60,"open":109.1,"high":109.3,"low":108.8,"close":109.0},
            {"timestamp":stamp+12*60,"open":109.0,"high":110.0,"low":108.95,"close":109.9},
        ])
        for i in range(8):
            op = 110.0+i*.8
            bars.append({"timestamp":stamp+(13+i)*60,"open":op,"high":op+.9,"low":op-.1,"close":op+.8})
        for i in range(3):
            bars.append({"timestamp":stamp+(21+i)*60,"open":116.0+i*.1,"high":116.5+i*.1,"low":108.6,"close":108.7-i*.05})
        now = bars[-1]["timestamp"]+1
        result = MultiTimeframeStyleAnalyzer().evaluate(
            "EURUSD", {"M5":bars}, {"bid":108.60,"ask":108.61}, now, spread_allowance=.01
        )["BASE_ENGULF_REVERSAL"]
        self.assertEqual(result["status"], "ENTRY_PROPOSAL")
        self.assertEqual(result["direction"], "SELL")
        self.assertEqual(result["setup_timeframe"], "M5")
        self.assertEqual(result["order_plan"]["status"], "PROPOSED")
        self.assertGreater(result["order_plan"]["stop_loss"], result["engulf_high"])
        self.assertEqual(set(result["timeframe_results"]), set(MultiTimeframeStyleAnalyzer.BASE_TFS))

    def test_base_engulf_reversal_waits_when_no_closed_candle_engulfs_base(self):
        from src.Intelligence.Execution.multi_timeframe_style_analyzer import _base_engulf_reversal
        bars = []
        stamp = 1_700_000_000
        for i in range(9):
            close = 100.0 + i
            bars.append({"time":stamp+i*60,"open":close-0.4,"high":close+0.1,"low":close-0.5,"close":close})
        bars.extend([
            {"time":stamp+9*60,"open":108.8,"high":109.3,"low":108.7,"close":109.0},
            {"time":stamp+10*60,"open":109.0,"high":109.25,"low":108.85,"close":109.1},
            {"time":stamp+11*60,"open":109.1,"high":109.3,"low":108.8,"close":109.0},
            {"time":stamp+12*60,"open":109.0,"high":110.0,"low":108.95,"close":109.9},
        ])
        for i in range(11):
            op = 110.0 + i*0.8
            bars.append({"time":stamp+(13+i)*60,"open":op,"high":op+0.9,"low":op-0.1,"close":op+0.8})
        result = _base_engulf_reversal(bars, now=bars[-1]["time"]+1)
        self.assertFalse(result["engulfed"])
        self.assertEqual(result["status"], "WAIT")

    def test_future_candle_frame_is_not_used(self):
        frames = {tf: self._flat_bars() for tf in
                  ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")}
        now = max(row["timestamp"] for row in frames["M1"]) - 1
        results = MultiTimeframeStyleAnalyzer().evaluate(
            "XAUUSD", frames, {"bid": 1999.9, "ask": 2000.1}, now
        )
        self.assertEqual(set(results), {"RTM", "PRICE_ACTION", "SCALP", "BASE_ENGULF_REVERSAL"})
        self.assertTrue(all(item["status"] == "WAIT" for item in results.values()))


if __name__ == "__main__":
    unittest.main()
