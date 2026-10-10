import unittest

from src.Research.Brain.fractal_nested_range_discovery import FractalNestedRangeDiscovery


def make_bars(n=120, start=1700000000, step=60):
    bars = []
    for i in range(n):
        # Bounded oscillation with deterministic timestamps and valid OHLC.
        close = 100.0 + ((i % 8) - 3.5) * 0.08
        bars.append({
            "time": start + i * step,
            "open": close,
            "high": close + 0.12,
            "low": close - 0.12,
            "close": close + (0.025 if i % 2 else -0.025),
        })
    return bars


class TestFractalNestedRangeDiscovery(unittest.TestCase):
    def test_discovers_multiple_variable_durations_causally(self):
        engine = FractalNestedRangeDiscovery(min_duration=8, max_duration=48, candidate_lengths=7)
        report = engine.discover_at(make_bars(), "M1", top_k=7)
        self.assertEqual(report["status"], "CANDIDATES_FOUND")
        durations = {c["duration_bars"] for c in report["candidates"]}
        self.assertGreaterEqual(len(durations), 4)
        self.assertTrue(all(c["end_index"] == 119 for c in report["candidates"]))
        self.assertTrue(all(c["evidence_mode"] == "CAUSAL_CANDIDATE" for c in report["candidates"]))

    def test_appending_future_bars_does_not_change_past_candidate(self):
        engine = FractalNestedRangeDiscovery(min_duration=8, max_duration=40, candidate_lengths=6)
        bars = make_bars(100)
        before = engine.discover_at(bars[:80], "M5", top_k=6)
        after = engine.discover_at(bars[:80] + bars[80:], "M5", top_k=6)
        # The decision timestamp differs because the second call intentionally moves forward;
        # compare a walk-forward result at the same historical endpoint instead.
        history = engine.discover_history(bars, "M5", step=1, top_k=6)
        at_80 = next(x for x in history if x["decision_time"] == bars[79]["time"])
        self.assertEqual(before["candidates"], at_80["candidates"])
        self.assertEqual(before["candidates"], engine.discover_at(bars[:80], "M5", top_k=6)["candidates"])

    def test_future_outcome_labels_are_separate_and_explicit(self):
        engine = FractalNestedRangeDiscovery(min_duration=8, max_duration=32, candidate_lengths=5)
        bars = make_bars()
        candidate = engine.discover_at(bars[:80], "M1")["candidates"][0]
        labeled = engine.label_outcome(candidate, bars, horizon=12)
        self.assertEqual(labeled["evidence_mode"], "OFFLINE_LABEL_ONLY")
        self.assertIn("RETROSPECTIVE_EXTREME_PROXY", labeled["label_semantics"])
        self.assertGreaterEqual(labeled["up_target_bars"], labeled["up_origin_proxy_bars"])

    def test_invalid_bars_do_not_create_candidates(self):
        engine = FractalNestedRangeDiscovery(min_duration=8, max_duration=16)
        self.assertEqual(engine.discover_at([], "M1")["status"], "INSUFFICIENT_DATA")


if __name__ == "__main__":
    unittest.main()
