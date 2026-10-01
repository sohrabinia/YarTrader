import sqlite3
from pathlib import Path

from src.Application.Backtesting.historical_dataset import (
    HistoricalDataset, cleanup_staged_dataset, stage_symbol_from_mt4
)


class FakeProvider:
    def __init__(self, root):
        self.root = Path(root)

    def _history_file(self, symbol, timeframe):
        return self.root / f"{symbol.upper()}_{timeframe.upper()}.hst"

    def _read_hst(self, path):
        return [
            {"time": 100, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
            {"time": 200, "open": 1.5, "high": 2.5, "low": 1, "close": 2, "volume": 11},
        ]


def test_historical_dataset_round_trip_and_cleanup(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "XAUUSD_D1.hst").write_bytes(b"fixture")
    dataset_path = tmp_path / "staging" / "XAUUSD" / "dataset.sqlite"
    ds = stage_symbol_from_mt4("XAUUSD", dataset_path, FakeProvider(source))
    try:
        assert ds.first_last("D1") == (100, 200, 2)
        rows = list(ds.range("D1", 100, 200))
        assert len(rows) == 2
        assert rows[0]["close"] == 1.5
        assert ds.manifest()["frames"]["D1"]["bars"] == 2
    finally:
        ds.close()
    assert dataset_path.exists()
    cleanup_staged_dataset(dataset_path)
    assert not dataset_path.exists()
    assert not Path(str(dataset_path) + "-wal").exists()
    assert not Path(str(dataset_path) + "-shm").exists()


def test_dataset_is_symbol_local_and_sqlite(tmp_path):
    path = tmp_path / "dataset.sqlite"
    ds = HistoricalDataset(path)
    try:
        ds.put("D1", [{"time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}])
        assert sqlite3.connect(path).execute(
            "select count(*) from candles where timeframe='D1'"
        ).fetchone()[0] == 1
    finally:
        ds.close()
