import unittest
from datetime import datetime, timedelta
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Data.MarketData.Models.models import MarketDataRequest

class TestMT5MockConnection(unittest.TestCase):
    def test_mock_mt5_health_diagnostics(self):
        """Verifies that the MT5 data provider reports connection health diagnostics correctly."""
        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1", evidence_dir="runtime_logs")
        conn_health = runtime.provider.delegate.get_connection_health()

        self.assertTrue(hasattr(conn_health, 'connected'))
        self.assertTrue(hasattr(conn_health, 'server'))
        self.assertTrue(hasattr(conn_health, 'ping_ms'))
        self.assertTrue(hasattr(conn_health, 'last_error'))

        target_req = MarketDataRequest(
            Asset="AAPL",
            StartTime=datetime.now() - timedelta(days=5),
            EndTime=datetime.now(),
            Timeframe="H1"
        )
        res = runtime.provider.retrieve_market_data(target_req)
        self.assertIsNotNone(res)
        self.assertTrue(len(res.DataPoints) > 0)
