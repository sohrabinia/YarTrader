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


def test_history_acquisition_binds_hst_reads_to_demo_terminal_data_path(tmp_path):
    from src.Application.Backtesting.mt4_history_acquisition import MT4HistoryAcquisition

    class DemoBridge:
        def heartbeat(self):
            return {
                "login": "252031952", "server": "Alpari-Pro.ECN-Demo",
                "is_demo": True, "terminal_path": str(tmp_path),
            }

    acquisition = MT4HistoryAcquisition(DemoBridge())
    assert acquisition.provider.data_root.resolve() == tmp_path.resolve()
    assert acquisition.demo_data_root == tmp_path.resolve()


def test_history_acquisition_rejects_signal_account_and_signal_hst_root(tmp_path):
    import pytest
    from src.Application.Backtesting.mt4_history_acquisition import MT4HistoryAcquisition
    from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider

    class SignalBridge:
        def heartbeat(self):
            return {
                "login": "143056202", "server": "Alpari-Pro.ECN",
                "is_demo": False, "terminal_path": str(tmp_path / "signal"),
            }

    with pytest.raises(RuntimeError, match="authorized DEMO"):
        MT4HistoryAcquisition(SignalBridge())

    class DemoBridge:
        def heartbeat(self):
            return {
                "login": "252031952", "server": "Alpari-Pro.ECN-Demo",
                "is_demo": True, "terminal_path": str(tmp_path / "demo"),
            }

    signal_provider = MT4HistoricalDataProvider(data_root=str(tmp_path / "signal"))
    with pytest.raises(RuntimeError, match="HST root is not the authorized DEMO"):
        MT4HistoryAcquisition(DemoBridge(), signal_provider)
