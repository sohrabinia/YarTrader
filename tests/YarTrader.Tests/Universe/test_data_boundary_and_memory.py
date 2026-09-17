import unittest
from datetime import datetime, timedelta
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.External.models import ExternalDataRequest
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Data.Market.models import CompactMarketState

class TestDataBoundaryAndMemorySafety(unittest.TestCase):
    """
    Tests enforcing Non-Negotiable Data Architecture & Memory Safety:
    - Bounded requests (~300-600 candles max lookback)
    - Zero technical indicators in CompactMarketState (NO volatility_atr, NO momentum_rsi)
    - Strictly primitive market facts (current_price, high, low, volume, spread, timestamp, freshness, validity)
    - Zero bulk historical download pipeline / warehouse creation
    - Bounded memory footprint
    """

    def setUp(self):
        self.provider = MT5DataProvider()

    def test_compact_market_state_has_no_technical_indicators(self):
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=datetime.now() - timedelta(hours=5),
            end_time=datetime.now()
        )
        compact_state = self.provider.fetch_compact_market_state(req)
        self.assertIsInstance(compact_state, CompactMarketState)

        # Assert NO technical indicators exist in CompactMarketState fields
        self.assertFalse(hasattr(compact_state, "volatility_atr"), "CompactMarketState MUST NOT contain volatility_atr")
        self.assertFalse(hasattr(compact_state, "momentum_rsi"), "CompactMarketState MUST NOT contain momentum_rsi")
        self.assertFalse(hasattr(compact_state, "trend_state"), "CompactMarketState MUST NOT contain trend_state")

        # Assert primitive market facts exist
        self.assertTrue(hasattr(compact_state, "current_price"))
        self.assertTrue(hasattr(compact_state, "high"))
        self.assertTrue(hasattr(compact_state, "low"))
        self.assertTrue(hasattr(compact_state, "volume"))
        self.assertTrue(hasattr(compact_state, "spread"))
        self.assertTrue(hasattr(compact_state, "data_freshness_sec"))
        self.assertTrue(hasattr(compact_state, "is_valid"))

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
        self.assertLessEqual(len(resp.raw_data), 1000, "Fetch request payload must be strictly bounded")

    def test_stale_or_invalid_date_range_fails_closed(self):
        now = datetime.now()
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=now,
            end_time=now - timedelta(days=1)
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

if __name__ == "__main__":
    unittest.main()
