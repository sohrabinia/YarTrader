import unittest

from src.Research.Brain.fractal_base_detection_engine import Gate3BaseDetectorEngine


class TestIndicatorFreeFractalBaseDetection(unittest.TestCase):
    def test_detector_has_no_atr_runtime_helper(self):
        self.assertFalse(hasattr(Gate3BaseDetectorEngine, "_calculate_atr"))

    def test_online_detector_uses_observed_price_structure_only(self):
        bars = []
        for i in range(8):
            base = 2000.0 + (0.05 if i % 2 else -0.05)
            bars.append({
                "timestamp": f"2026-01-01T00:{i:02d}:00+00:00",
                "open": base,
                "high": base + 0.1,
                "low": base - 0.1,
                "close": base,
                "volume": 1.0,
            })
        engine = Gate3BaseDetectorEngine(min_duration_bars=4)
        result = engine.detect_bases_at_scale(bars)
        self.assertIsInstance(result, list)
        for base in result:
            self.assertNotIn("atr", base)
            self.assertNotIn("atr_period", base.get("thresholds", {}))


if __name__ == "__main__":
    unittest.main()
