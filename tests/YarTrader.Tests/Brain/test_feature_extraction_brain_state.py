import unittest
from unittest.mock import patch

from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine


class FeatureExtractionBrainStateTests(unittest.TestCase):
    def test_brain_is_reused_per_symbol_and_timeframe(self):
        engine = FeatureExtractionResearchEngine.__new__(FeatureExtractionResearchEngine)
        engine._live_brains = {}

        class FakeBrain:
            def __init__(self, asset, timeframe):
                self.asset = asset
                self.timeframe = timeframe

        with patch("src.Research.Brain.live_brain.LiveAnalysisBrain", FakeBrain):
            first = engine._get_live_brain("XAUUSD", "D1")
            second = engine._get_live_brain("xauusd", "d1")
            other_tf = engine._get_live_brain("XAUUSD", "H1")
            other_symbol = engine._get_live_brain("EURUSD", "D1")

        self.assertIs(first, second)
        self.assertIsNot(first, other_tf)
        self.assertIsNot(first, other_symbol)
        self.assertEqual(set(engine._live_brains), {("XAUUSD", "D1"), ("XAUUSD", "H1"), ("EURUSD", "D1")})


if __name__ == "__main__":
    unittest.main()
