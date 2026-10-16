import unittest

from src.Research.Brain.multiscale_range_behavior_engine import MultiscaleRangeBehaviorEngine


def make_bars(scale=1.0, drift=0.0, count=24):
    bars = []
    price = 100.0 * scale
    for i in range(count):
        center = price + drift * i * scale
        bars.append({
            "open": center,
            "high": center + 0.8 * scale,
            "low": center - 0.7 * scale,
            "close": center + (0.2 if i % 2 == 0 else -0.1) * scale,
        })
    return bars


class TestMultiscaleRangeBehaviorEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MultiscaleRangeBehaviorEngine(window=16, min_bars=8)

    def test_compares_all_supplied_timeframes_not_only_adjacent_pairs(self):
        frames = {
            "M1": make_bars(0.01),
            "M5": make_bars(0.02),
            "M15": make_bars(0.03),
            "H1": make_bars(0.04),
            "H4": make_bars(0.05),
            "D1": make_bars(0.06),
            "W1": make_bars(0.07),
            "MN1": make_bars(0.08),
        }
        result = self.engine.analyze(frames)
        self.assertEqual(result["valid_timeframe_count"], 8)
        self.assertEqual(result["comparison_count"], 28)
        self.assertEqual(len(result["all_timeframe_comparisons"]), 28)
        self.assertFalse(result["prediction_claim"])

    def test_insufficient_data_fails_closed(self):
        result = self.engine.analyze({"M1": make_bars(count=5)})
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["comparison_count"], 0)

    def test_features_are_scale_normalized(self):
        small = self.engine.describe_timeframe("M1", make_bars(scale=0.01))
        large = self.engine.describe_timeframe("D1", make_bars(scale=100.0))
        self.assertEqual(small["status"], "DESCRIBED")
        self.assertEqual(large["status"], "DESCRIBED")
        for key in ("range_width_over_atr", "close_position_0_1",
                    "net_displacement_over_range", "path_efficiency_0_1"):
            self.assertAlmostEqual(small["features"][key], large["features"][key], places=6)

    def test_invalid_or_zero_price_bars_are_not_fabricated(self):
        bars = [{"open": 0, "high": 0, "low": 0, "close": 0}] * 12
        result = self.engine.describe_timeframe("M5", bars)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["evidence_state"], "NO_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
