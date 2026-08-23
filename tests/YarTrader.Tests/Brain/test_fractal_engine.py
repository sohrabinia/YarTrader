import unittest
from datetime import datetime, timezone, timedelta
from src.Infrastructure.DI.container import DIContainer
from src.Infrastructure.DI.registrations import register_services
from src.Research.MarketAnalysis.Interfaces.interfaces import IFractalEngine
from src.Research.Brain.fractal_engine import FractalEngine
from src.Data.MarketData.Models.models import MarketDataPoint

class TestFractalEngineSubsystem(unittest.TestCase):

    def setUp(self):
        self.container = DIContainer()
        register_services(self.container)
        self.fractal_engine = self.container.resolve(IFractalEngine)

    def test_di_container_resolves_fractal_engine(self):
        """Verify IFractalEngine resolves to FractalEngine singleton instance."""
        self.assertIsInstance(self.fractal_engine, FractalEngine)

    def test_fractal_engine_analysis_pipeline(self):
        """Verify fractal analysis executes multi-timeframe containment, pattern memory, and scale construction."""
        now = datetime.now(timezone.utc)
        candles_h1 = []
        for i in range(20):
            ts = now - timedelta(hours=20-i)
            candles_h1.append(
                MarketDataPoint(
                    AssetId="XAUUSD",
                    Timestamp=ts,
                    Open=2000.0 + i,
                    High=2005.0 + i,
                    Low=1995.0 + i,
                    Close=2002.0 + i,
                    Volume=100.0
                )
            )

        candles_m15 = []
        for i in range(80):
            ts = now - timedelta(minutes=(80-i)*15)
            candles_m15.append(
                MarketDataPoint(
                    AssetId="XAUUSD",
                    Timestamp=ts,
                    Open=2000.0 + (i * 0.25),
                    High=2001.0 + (i * 0.25),
                    Low=1999.0 + (i * 0.25),
                    Close=2000.5 + (i * 0.25),
                    Volume=25.0
                )
            )

        candles_by_tf = {
            "H1": candles_h1,
            "M15": candles_m15
        }

        res = self.fractal_engine.analyze_fractals(
            symbol="XAUUSD",
            primary_timeframe="H1",
            candles_by_tf=candles_by_tf
        )

        self.assertEqual(res["symbol"], "XAUUSD")
        self.assertEqual(res["primary_timeframe"], "H1")
        self.assertEqual(res["fractal_status"], "ACTIVE")
        self.assertIn("containment_mapping", res)
        self.assertIn("matching_pattern_record", res)
        self.assertIn("similarity_analysis", res)
        self.assertGreaterEqual(res["scales_evaluated_count"], 1)

if __name__ == "__main__":
    unittest.main()
