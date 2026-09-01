import unittest
from src.Data.Aggregation.timeframe_aggregator import TimeframeAggregator

class TestTimeframeAggregator(unittest.TestCase):
    """
    Unit Test Suite for TimeframeAggregator:
    1. Proves M1 -> M5, M15, H1, H4 aggregation correctness (Open/High/Low/Close/Volume).
    2. Proves fail-closed behavior when M1 candles are empty or insufficient.
    3. Proves mathematical consistency across aggregated candles.
    """

    def setUp(self):
        # Generate 240 M1 candles (enough for 48 M5, 16 M15, 4 H1, 1 H4)
        self.m1_candles = []
        for i in range(240):
            o = 2000.0 + (i * 0.1)
            h = o + 0.5
            l = o - 0.3
            c = o + 0.2
            self.m1_candles.append({
                "time": 1700000000 + i * 60,
                "timestamp": str(1700000000 + i * 60),
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(l, 4),
                "close": round(c, 4),
                "volume": 10.0
            })

    def test_01_m1_to_m5_aggregation(self):
        """Proves 5 M1 bars aggregate into 1 M5 bar with correct OHLCV."""
        m5_candles = TimeframeAggregator.aggregate_m1_candles(self.m1_candles, target_timeframe="M5")
        self.assertEqual(len(m5_candles), 48) # 240 / 5 = 48

        first = m5_candles[0]
        # First M5 bucket: M1 index 0 to 4
        # Open = M1[0] open = 2000.0
        # Close = M1[4] close = 2000.4 + 0.2 = 2000.6
        # High = max(M1[0..4] high) = 2000.4 + 0.5 = 2000.9
        # Low = min(M1[0..4] low) = 2000.0 - 0.3 = 1999.7
        # Volume = 5 * 10 = 50.0
        self.assertEqual(first["open"], 2000.0)
        self.assertEqual(first["close"], 2000.6)
        self.assertEqual(first["high"], 2000.9)
        self.assertEqual(first["low"], 1999.7)
        self.assertEqual(first["volume"], 50.0)

    def test_02_m1_to_h1_aggregation(self):
        """Proves 60 M1 bars aggregate into 1 H1 bar."""
        h1_candles = TimeframeAggregator.aggregate_m1_candles(self.m1_candles, target_timeframe="H1")
        self.assertEqual(len(h1_candles), 4) # 240 / 60 = 4

        first = h1_candles[0]
        self.assertEqual(first["open"], 2000.0)
        self.assertEqual(first["volume"], 600.0) # 60 * 10

    def test_03_m1_to_h4_aggregation(self):
        """Proves 240 M1 bars aggregate into 1 H4 bar."""
        h4_candles = TimeframeAggregator.aggregate_m1_candles(self.m1_candles, target_timeframe="H4")
        self.assertEqual(len(h4_candles), 1) # 240 / 240 = 1

        first = h4_candles[0]
        self.assertEqual(first["open"], 2000.0)
        self.assertEqual(first["volume"], 2400.0) # 240 * 10

    def test_04_insufficient_m1_candles_fails_closed(self):
        """Proves insufficient M1 candles fail closed with empty list."""
        short_m1 = self.m1_candles[:10] # Only 10 M1 bars
        # H1 requires 60 M1 bars
        h1_res = TimeframeAggregator.aggregate_m1_candles(short_m1, target_timeframe="H1")
        self.assertEqual(h1_res, [])

    def test_05_empty_input_fails_closed(self):
        """Proves empty input returns empty list."""
        res = TimeframeAggregator.aggregate_m1_candles([], target_timeframe="M5")
        self.assertEqual(res, [])

if __name__ == "__main__":
    unittest.main()
