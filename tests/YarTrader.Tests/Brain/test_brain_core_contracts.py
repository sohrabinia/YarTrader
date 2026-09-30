import sys
import tempfile
import shutil
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, r"C:\Projects\YarTrader")

from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.live_brain import LiveAnalysisBrain


class BrainPatternIdentityTests(unittest.TestCase):
    def _exp(self, eid, tf, action="BUY"):
        return ExperienceMemory(
            experience_id=eid, symbol="XAUUSD", timeframe=tf,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1),
            situation_signature=[1.0, 1.0, 1.0, 1.0],
            decision_action=action, outcome_result="SUCCESS",
            lesson_feedback="test", max_favorable_excursion=10.0,
            max_adverse_excursion=-4.0,
            meta={
                "is_validated": True, "pattern_symbol": "XAUUSD",
                "pattern_timeframe": tf, "timeframe_signature": [tf],
                "predicted_action": action, "favorable_excursion": 10.0,
                "adverse_excursion": 4.0, "judge_accuracy": 1.0,
            },
        )

    def test_pattern_identity_is_stable_and_timeframe_scoped(self):
        root = tempfile.mkdtemp(prefix="yt-pattern-test-")
        try:
            memory = MarketMemorySystem(storage_dir=root)
            memory.add_experience(self._exp("a", "M15"))
            memory.add_experience(self._exp("b", "M15"))
            memory.add_experience(self._exp("c", "H1", "SELL"))
            memory.promote_experiences_to_patterns()
            patterns = memory.get_patterns()
            self.assertEqual(len(patterns), 2)
            self.assertNotEqual(patterns[0].pattern_id, patterns[1].pattern_id)
            m15 = [p for p in patterns if p.timeframe == "M15"][0]
            self.assertEqual(m15.occurrences_count, 2)
            self.assertEqual(m15.version, 1)
            self.assertEqual(m15.status, "ACTIVE")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_discovery_never_crosses_symbol_or_timeframe_scope(self):
        root = tempfile.mkdtemp(prefix="yt-scope-test-")
        try:
            memory = MarketMemorySystem(storage_dir=root)
            memory.add_experience(self._exp("m15", "M15"))
            memory.add_experience(self._exp("h1", "H1", "SELL"))
            memory.promote_experiences_to_patterns()
            engine = PatternDiscoveryEngine()
            patterns = memory.get_patterns()
            m15 = engine.find_matches([1, 1, 1, 1], patterns, symbol="XAUUSD", timeframe="M15", timeframe_signature=["M15"])
            h1 = engine.find_matches([1, 1, 1, 1], patterns, symbol="XAUUSD", timeframe="H1", timeframe_signature=["H1"])
            self.assertEqual([p.timeframe for p, _ in m15], ["M15"])
            self.assertEqual([p.timeframe for p, _ in h1], ["H1"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_brain_uses_learned_excursions_for_trade_parameters(self):
        root = tempfile.mkdtemp(prefix="yt-brain-test-")
        try:
            memory = MarketMemorySystem(storage_dir=root)
            for i in range(3):
                memory.add_experience(self._exp(f"seed-{i}", "M15"))
            memory.promote_experiences_to_patterns()
            brain = LiveAnalysisBrain("XAUUSD", "M15", memory_system=memory)
            base = datetime.now(timezone.utc) - timedelta(minutes=4)
            report = None
            for i, price in enumerate([100, 101, 102, 103, 104]):
                report = brain.process_live_candle({
                    "timestamp": (base + timedelta(minutes=i)).isoformat(),
                    "open": price - 0.2, "high": price + 0.5,
                    "low": price - 0.5, "close": price, "volume": 100,
                }, simulate_virtual_trade=False)
            hypothesis = report.to_dict()["active_hypotheses"][0]
            self.assertEqual(hypothesis["suggested_virtual_action"], "BUY")
            self.assertGreaterEqual(hypothesis["hypothesis_confidence"], 50.0)
            self.assertGreaterEqual(hypothesis["trade_parameters"]["risk_reward"], 1.5)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
