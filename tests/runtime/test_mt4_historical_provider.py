import struct
import tempfile
import unittest
from pathlib import Path

from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
from src.Application.Backtesting.historical_dataset import stage_symbol_from_mt4


class TestMT4HistoricalProviderMissingFiles(unittest.TestCase):
    def test_missing_or_unsupported_timeframe_never_resolves_to_current_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT4HistoricalDataProvider(data_root=temp_dir)
            missing = provider._history_file("XAUUSD", "M30")
            unsupported = provider._history_file("XAUUSD", "MTF")

            self.assertNotEqual(missing, Path())
            self.assertNotEqual(unsupported, Path())
            self.assertFalse(missing.exists())
            self.assertFalse(unsupported.exists())

    def test_staging_skips_missing_timeframes_without_reading_dot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history = root / "history" / "DemoServer"
            history.mkdir(parents=True)
            header = struct.pack("<i", 401) + bytes(144)
            candle = struct.pack(
                "<qddddqiq",
                1_759_000_000,
                2500.0,
                2510.0,
                2490.0,
                2505.0,
                100,
                10,
                100,
            )
            (history / "XAUUSD1.hst").write_bytes(header + candle)
            provider = MT4HistoricalDataProvider(data_root=str(root))
            staged = stage_symbol_from_mt4("XAUUSD", root / "staged" / "dataset.sqlite", provider)
            try:
                self.assertEqual(staged.manifest()["frames"]["M1"]["bars"], 1)
                self.assertNotIn("M30", staged.manifest()["frames"])
            finally:
                staged.close()


if __name__ == "__main__":
    unittest.main()
