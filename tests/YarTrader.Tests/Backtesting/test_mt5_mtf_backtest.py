import unittest
from app.workers.mt5_mtf_backtest_worker import closed_context_provider, MTF_TIMEFRAMES, MAX_HISTORY_YEARS

class TestMt5MtfBacktest(unittest.TestCase):
    def test_canonical_timeframes(self):
        self.assertEqual(MTF_TIMEFRAMES, ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"))

    def test_history_is_capped_at_ten_years_not_fixed_per_timeframe(self):
        self.assertEqual(MAX_HISTORY_YEARS, 10)

    def test_alignment_uses_same_decision_timestamp_across_timeframes(self):
        series = {
            "M1": [{"timestamp": "2026-01-01T10:37:00+00:00", "close": 1}],
            "M5": [{"timestamp": "2026-01-01T10:30:00+00:00", "close": 4}, {"timestamp": "2026-01-01T10:35:00+00:00", "close": 5}],
            "M15": [{"timestamp": "2026-01-01T10:15:00+00:00", "close": 14}, {"timestamp": "2026-01-01T10:30:00+00:00", "close": 15}],
            "H1": [{"timestamp": "2026-01-01T09:00:00+00:00", "close": 100}],
            "H4": [{"timestamp": "2026-01-01T04:00:00+00:00", "close": 399}, {"timestamp": "2026-01-01T08:00:00+00:00", "close": 400}],
            "D1": [{"timestamp": "2025-12-31T00:00:00+00:00", "close": 1000}],
        }
        ctx = closed_context_provider(series, "2026-01-01T10:37:00+00:00")
        self.assertEqual(ctx["M5"][-1]["timestamp"], "2026-01-01T10:30:00+00:00")
        self.assertEqual(ctx["M15"][-1]["timestamp"], "2026-01-01T10:15:00+00:00")
        self.assertEqual(ctx["H1"][-1]["timestamp"], "2026-01-01T09:00:00+00:00")
        self.assertEqual(ctx["H4"][-1]["timestamp"], "2026-01-01T04:00:00+00:00")
        self.assertEqual(ctx["D1"][-1]["timestamp"], "2025-12-31T00:00:00+00:00")

    def test_no_future_higher_timeframe_bar(self):
        series = {"H1": [
            {"timestamp": "2026-01-01T00:00:00+00:00", "close": 100},
            {"timestamp": "2026-01-01T01:00:00+00:00", "close": 200},
        ]}
        ctx = closed_context_provider(series, "2026-01-01T00:30:00+00:00")
        self.assertEqual(len(ctx.get("H1", [])), 0)
        ctx = closed_context_provider(series, "2026-01-01T01:00:00+00:00")
        self.assertEqual(len(ctx["H1"]), 1)
        self.assertEqual(ctx["H1"][-1]["close"], 100)
    def test_boundary_uses_current_closed_bar(self):
        series = {"H1": [
            {"timestamp": "2026-01-01T00:00:00+00:00", "close": 100},
            {"timestamp": "2026-01-01T01:00:00+00:00", "close": 200},
        ]}
        ctx = closed_context_provider(series, "2026-01-01T02:00:00+00:00")
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
