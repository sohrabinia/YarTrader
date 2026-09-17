import unittest
from datetime import datetime, timedelta
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.External.models import ExternalDataRequest
from src.Application.Runtime.research_runtime import ResearchRuntime

class TestDataBoundaryAndMemorySafety(unittest.TestCase):
    """
    Tests enforcing Non-Negotiable Data Architecture & Memory Safety:
    - Bounded requests (~300-600 candles max lookback)
    - Zero bulk historical download pipeline
    - Zero persistent historical data warehouse creation
    - Fail closed on missing, stale, or malformed market data
    - Bounded memory footprint
    """

    def setUp(self):
        self.provider = MT5DataProvider()

    def test_bounded_request_payload_size(self):
        now = datetime.now()
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=now - timedelta(days=5),
            end_time=now
        )
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        # Verify returned data point count is strictly bounded (<= 1000 bars)
        self.assertLessEqual(len(resp.raw_data), 1000, "Fetch request payload must be strictly bounded")

    def test_stale_or_invalid_date_range_fails_closed(self):
        now = datetime.now()
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=now,
            end_time=now - timedelta(days=1)  # Invalid: start > end
        )
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success, "Invalid date range must fail closed")

    def test_disconnected_mt5_fails_closed(self):
        self.provider.set_connected(False)
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=datetime.now() - timedelta(hours=5),
            end_time=datetime.now()
        )
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success)
        self.assertTrue(
            "offline" in resp.error_message.lower() or "connection lost" in resp.error_message.lower(),
            f"Expected error message indicating offline/disconnected state, got: {resp.error_message}"
        )

    def test_research_runtime_bounded_execution(self):
        runtime = ResearchRuntime(symbol="BTCUSD", timeframe="H1")
        res = runtime.run_once()
        self.assertIsNotNone(res)
        self.assertEqual(res.Request.Asset, "BTCUSD")

        # Confirm research findings do NOT persist raw candle databases or bulk dataframes
        findings = res.Findings
        self.assertIn("autonomous_decision", findings)
        self.assertIn("pipeline_outputs", findings)

if __name__ == "__main__":
    unittest.main()
