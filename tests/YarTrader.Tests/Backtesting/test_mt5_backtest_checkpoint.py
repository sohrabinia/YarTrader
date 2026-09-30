import json
import tempfile
import unittest
from pathlib import Path

from app.workers import mt5_backtest_worker as worker


class TestMt5BacktestCheckpoint(unittest.TestCase):
    def test_atomic_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            payload = {"schema": 1, "next_start": "2026-01-01T00:00:00+00:00"}
            worker.atomic_json(path, payload)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_years_contract_requires_ten_years(self):
        with self.assertRaises(ValueError):
            worker.run("XAUUSD", "D1", 9, 10000.0, 0.0)

    def test_chunk_sizes_are_resource_bounded(self):
        self.assertEqual(worker.chunk_days("M1"), 7)
        self.assertEqual(worker.chunk_days("M5"), 30)
        self.assertEqual(worker.chunk_days("D1"), 365)

    def test_single_flight_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root, old_lock = worker.ROOT, worker.LOCK
            worker.ROOT = Path(tmp)
            worker.LOCK = worker.ROOT / "mt5_backtest.lock"
            try:
                self.assertTrue(worker.acquire_lock())
                self.assertFalse(worker.acquire_lock())
                worker.release_lock()
                self.assertTrue(worker.acquire_lock())
                worker.release_lock()
            finally:
                worker.ROOT, worker.LOCK = old_root, old_lock


if __name__ == "__main__":
    unittest.main()
