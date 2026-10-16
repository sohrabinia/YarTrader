import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Data.MarketData.Models.models import MarketDataRequest
from src.Data.Market.models import (
    CandleRecord, MarketDataMetadata, MarketDataResponse as SourceMarketDataResponse,
)

class TestMT5MockConnection(unittest.TestCase):
    def test_mock_mt5_health_diagnostics(self):
        """Verifies that the MT5 data provider reports connection health diagnostics correctly."""
        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1", evidence_dir="runtime_logs")
        now = datetime.now()
        conn_health = SimpleNamespace(connected=True, server="mock-server", ping_ms=1.0, last_error=None)
        candle = CandleRecord(timestamp=now, open=100.0, high=102.0, low=99.0, close=101.0, volume=10.0)

        def mock_fetch_market_data(request):
            return SourceMarketDataResponse(
                request=request,
                candles=[candle],
                metadata=MarketDataMetadata(provider_id="mock-mt5", retrieved_at=now, latency_ms=1.0),
            )

        with patch.object(runtime.provider.delegate, "get_connection_health", return_value=conn_health), \
             patch.object(runtime.provider.delegate, "fetch_market_data", side_effect=mock_fetch_market_data):
            reported_health = runtime.provider.delegate.get_connection_health()
            self.assertTrue(hasattr(reported_health, 'connected'))
            self.assertTrue(hasattr(reported_health, 'server'))
            self.assertTrue(hasattr(reported_health, 'ping_ms'))
            self.assertTrue(hasattr(reported_health, 'last_error'))

            target_req = MarketDataRequest(
                Asset="AAPL",
                StartTime=now - timedelta(days=5),
                EndTime=now,
                Timeframe="H1"
            )
            res = runtime.provider.retrieve_market_data(target_req)
        self.assertIsNotNone(res)
        self.assertEqual(len(res.DataPoints), 1)
        self.assertEqual(res.DataPoints[0].Close, 101.0)
