import unittest
import tempfile
import shutil
from datetime import datetime

from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory, PatternMemory


class TestSingleTradeLearningProtection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mem_sys = MarketMemorySystem(storage_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_single_trade_rejected_from_concept_memory(self):
        """Verifies a single trade (N=1) cannot promote to Concept Memory."""
        exp = ExperienceMemory(
            experience_id="exp-single-001",
            symbol="XAUUSD",
            timeframe="M15",
            timestamp=datetime.now(),
            situation_signature=[1.5, 10.0, 0.5],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Single trade test",
            max_favorable_excursion=2.0,
            max_adverse_excursion=-0.5,
            meta={"is_validated": True, "judge_accuracy": 0.90}
        )

        self.mem_sys.add_experience(exp)
        self.mem_sys.promote_experiences_to_patterns()
        concepts = self.mem_sys.consolidate_patterns_to_concepts(min_samples=5)

        # Single trade (N=1 < min_samples 5) MUST be rejected from concept memory
        self.assertEqual(len(concepts), 0)

    def test_n8_sample_protection_gate(self):
        """Verifies N=8 sample gate evaluates Judge accuracy and consistency before promotion."""
        # Add N=8 experiences with high Judge accuracy
        for i in range(8):
            exp = ExperienceMemory(
                experience_id=f"exp-n8-{i}",
                symbol="XAUUSD",
                timeframe="M15",
                timestamp=datetime.now(),
                situation_signature=[2.5, 12.0, 0.8],
                decision_action="BUY",
                outcome_result="SUCCESS",
                lesson_feedback="N8 test",
                max_favorable_excursion=2.5,
                max_adverse_excursion=-0.2,
                meta={"is_validated": True, "judge_accuracy": 0.80}
            )
            self.mem_sys.add_experience(exp)

        self.mem_sys.promote_experiences_to_patterns()
        concepts = self.mem_sys.consolidate_patterns_to_concepts(min_samples=5, min_validation_score=0.75)

        # N=8 with high accuracy and 100% continuation consistency MUST be approved
        self.assertEqual(len(concepts), 1)
        self.assertTrue(concepts[0].is_approved)


if __name__ == "__main__":
    unittest.main()
