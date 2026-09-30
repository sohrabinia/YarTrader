import unittest
from app.workers.mt5_mtf_backtest_worker import closed_context_provider, MTF_TIMEFRAMES

class TestMt5MtfBacktest(unittest.TestCase):
    def test_canonical_timeframes(self):
        self.assertEqual(MTF_TIMEFRAMES, ("M1", "M5", "M15", "M30", "H1", "H4", "D1"))

    def test_no_future_higher_timeframe_bar(self):
        series = {"H1": [
            {"timestamp": "2026-01-01T00:00:00+00:00", "close": 100},
            {"timestamp": "2026-01-01T01:00:00+00:00", "close": 200},
        ]}
        ctx = closed_context_provider(series, "2026-01-01T00:30:00+00:00")
        self.assertEqual(len(ctx["H1"]), 1)
        self.assertEqual(ctx["H1"][-1]["close"], 100)
    def test_boundary_uses_current_closed_bar(self):
        series = {"H1": [
            {"timestamp": "2026-01-01T00:00:00+00:00", "close": 100},
            {"timestamp": "2026-01-01T01:00:00+00:00", "close": 200},
        ]}
        ctx = closed_context_provider(series, "2026-01-01T01:00:00+00:00")
        self.assertEqual(ctx["H1"][-1]["close"], 200)

    def test_context_is_bounded(self):
        series = {"H1": [
            {"timestamp": f"2026-01-01T{i:02d}:00:00+00:00", "close": i}
            for i in range(24)
        ]}
        ctx = closed_context_provider(series, "2026-01-01T23:00:00+00:00")
        self.assertLessEqual(len(ctx["H1"]), 500)

if __name__ == "__main__":
    unittest.main()
