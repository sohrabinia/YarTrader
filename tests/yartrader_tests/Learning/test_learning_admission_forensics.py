import unittest
import tempfile
import shutil
from datetime import datetime

from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory


class TestLearningAdmissionForensics(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mem_sys = MarketMemorySystem(storage_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_positive_learning_admission(self):
        """Verifies that a valid closed experience is admitted into ExperienceMemory."""
        exp = ExperienceMemory(
            experience_id="exp-valid-001",
            symbol="XAUUSD",
            timeframe="M15",
            timestamp=datetime.now(),
            situation_signature=[1.5, 10.0, 0.5],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Valid historical trade lesson",
            max_favorable_excursion=2.0,
            max_adverse_excursion=-0.5,
            meta={"is_validated": True, "judge_accuracy": 0.85}
        )

        self.mem_sys.add_experience(exp)
        exps = self.mem_sys.get_experiences()

        self.assertEqual(len(exps), 1)
        self.assertEqual(exps[0].experience_id, "exp-valid-001")

    def test_sample_threshold_concept_promotion(self):
        """Verifies concept promotion gate requires minimum samples (N >= 5)."""
        # Add 3 experiences (below N=5 threshold)
        for i in range(3):
            exp = ExperienceMemory(
                experience_id=f"exp-sample-{i}",
                symbol="XAUUSD",
                timeframe="M15",
                timestamp=datetime.now(),
                situation_signature=[2.0, 10.0, 0.5],
                decision_action="BUY",
                outcome_result="SUCCESS",
                lesson_feedback="Sample test",
                max_favorable_excursion=2.0,
                max_adverse_excursion=-0.5,
                meta={"is_validated": True, "judge_accuracy": 0.85}
            )
            self.mem_sys.add_experience(exp)

        self.mem_sys.promote_experiences_to_patterns()
        concepts = self.mem_sys.consolidate_patterns_to_concepts(min_samples=5)

        # N=3 should NOT produce consolidated concept
        self.assertEqual(len(concepts), 0)

        # Add 3 more experiences to reach N=6 >= 5
        for i in range(3, 6):
            exp = ExperienceMemory(
                experience_id=f"exp-sample-{i}",
                symbol="XAUUSD",
                timeframe="M15",
                timestamp=datetime.now(),
                situation_signature=[2.0, 10.0, 0.5],
                decision_action="BUY",
                outcome_result="SUCCESS",
                lesson_feedback="Sample test",
                max_favorable_excursion=2.0,
                max_adverse_excursion=-0.5,
                meta={"is_validated": True, "judge_accuracy": 0.85}
            )
            self.mem_sys.add_experience(exp)

        self.mem_sys.promote_experiences_to_patterns()
        concepts = self.mem_sys.consolidate_patterns_to_concepts(min_samples=5)

        # N=6 >= 5 MUST consolidate into concept
        self.assertEqual(len(concepts), 1)
        self.assertTrue(concepts[0].is_approved)


if __name__ == "__main__":
    unittest.main()
