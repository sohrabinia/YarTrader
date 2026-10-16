import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.workers.mt5_mtf_backtest_worker import closed_context_provider, MTF_TIMEFRAMES, MAX_HISTORY_YEARS, validate_or_migrate_checkpoint, SCHEMA
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

class TestMt5MtfBacktest(unittest.TestCase):
    def test_canonical_timeframes(self):
        self.assertEqual(MTF_TIMEFRAMES, ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"))

    def test_history_is_capped_at_ten_years_not_fixed_per_timeframe(self):
        self.assertEqual(MAX_HISTORY_YEARS, 10)

    def test_legacy_completed_checkpoint_migrates_and_resumes_without_reprocessing_history(self):
        end = datetime(2026, 10, 15, 6, 51, 59, tzinfo=timezone.utc)
        legacy = {
            "status": "COMPLETED", "symbol": "EURUSD", "timeframe": "MN1",
            "max_history_years": 10, "actual_history_start": "2016-10-01T00:00:00+00:00",
            "actual_history_end": end.isoformat(), "processed_bars": 120,
            "state": {"balance": 9000.0, "total_trades": 10, "open_position": None},
        }
        migrated, did_migrate = validate_or_migrate_checkpoint(
            legacy, "EURUSD", "MN1", end-timedelta(days=3650), end+timedelta(minutes=45)
        )
        self.assertTrue(did_migrate)
        self.assertEqual(migrated["schema"], SCHEMA)
        self.assertEqual(migrated["status"], "RUNNING")
        self.assertEqual(migrated["next_start"], end.isoformat())
        self.assertEqual(migrated["processed_bars"], 120)
        self.assertEqual(migrated["state"]["balance"], 9000.0)

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

    def test_backtest_engine_mtf_provider_excludes_unclosed_future_bars(self):
        class FakeMT5:
            TIMEFRAME_M1 = 1
            TIMEFRAME_M5 = 5
            TIMEFRAME_M15 = 15
            TIMEFRAME_M30 = 30
            TIMEFRAME_H1 = 60
            TIMEFRAME_H4 = 240
            TIMEFRAME_D1 = 1440
            TIMEFRAME_W1 = 10080
            TIMEFRAME_MN1 = 43200
            seconds = {1: 60, 5: 300, 15: 900, 30: 1800, 60: 3600, 240: 14400, 1440: 86400, 10080: 604800, 43200: 31 * 86400}

            @classmethod
            def copy_rates_range(cls, symbol, timeframe, start, end):
                step = cls.seconds[timeframe]
                end_epoch = int(end.timestamp())
                return [
                    {
                        "time": end_epoch - (60 - i) * step,
                        "open": 1.0 + i * 0.001,
                        "high": 1.01 + i * 0.001,
                        "low": 0.99 + i * 0.001,
                        "close": 1.005 + i * 0.001,
                        "tick_volume": 100 + i,
                    }
                    for i in range(60)
                ]

            @staticmethod
            def last_error():
                return (0, "ok")

        with tempfile.TemporaryDirectory(prefix="yartrader-mtf-provider-test-") as tmp:
            engine = BacktestAndLearningEngine(storage_dir=tmp)
            end = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
            provider, counts = engine.build_mt5_multitimeframe_provider(
                "EURUSD", "H1", end - timedelta(days=30), end, FakeMT5
            )
            self.assertEqual(set(counts), {"H4", "H1", "M30"})
            self.assertTrue(all(count == 60 for count in counts.values()))
            cutoff = end - timedelta(hours=2)
            context = provider(cutoff)
            self.assertTrue(context["H1"])
            last_open = datetime.fromisoformat(context["H1"][-1]["timestamp"])
            self.assertLessEqual(last_open + timedelta(hours=1), cutoff)
            self.assertLess(len(context["H1"]), counts["H1"])

if __name__ == "__main__":
    unittest.main()
