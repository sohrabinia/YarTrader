import unittest
import os
import shutil
import tempfile
from datetime import datetime
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory

class TestMemoryPersistenceLifecycle(unittest.TestCase):
    """
    Focused end-to-end unit test suite for Memory & Learning Persistence Lifecycle.
    Verifies:
    1. Experience creation & validation.
    2. Promotion to Pattern Memory.
    3. Atomic JSON save & reload survival across object re-instantiation.
    4. Schema field preservation (`pattern_id`, `sequence_signature`, `occurrences_count`, `continuation_count`, `reversal_count`, `outcomes`, `timestamps`).
    5. Idempotent re-promotion protection (zero duplicate outcomes).
    6. Corruption recovery & snapshot fallback.
    """

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="yartrader_test_memory_")
        self.memory = MarketMemorySystem(storage_dir=self.test_dir)

    def tearDown(self) -> None:
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_end_to_end_experience_pattern_persistence_and_reload(self) -> None:
        # Step 1: Create experience
        exp = ExperienceMemory(
            experience_id="exp-test-001",
            symbol="XAUUSD",
            timeframe="M5",
            timestamp=datetime.now(),
            situation_signature=[2000.0, 1990.0, 2020.0],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Breakout confirmed",
            max_favorable_excursion=20.0,
            max_adverse_excursion=-2.0,
            meta={"is_validated": True}
        )

        self.memory.add_experience(exp)
        self.assertIn("exp-test-001", self.memory.experiences)

        # Step 2: Pattern Memory (automatically promoted via add_experience)
        self.assertEqual(len(self.memory.patterns), 1)
        pat = list(self.memory.patterns.values())[0]
        pattern_id = pat.pattern_id
        self.assertEqual(pat.occurrences_count, 1)
        self.assertEqual(pat.continuation_count, 1)
        self.assertEqual(len(pat.outcomes), 1)
        self.assertEqual(pat.outcomes[0]["experience_id"], "exp-test-001")

        # Step 3 & 4: Re-instantiate MarketMemorySystem to verify disk persistence & reload
        memory_reloaded = MarketMemorySystem(storage_dir=self.test_dir)
        self.assertIn(pattern_id, memory_reloaded.patterns)

        reloaded_pat = memory_reloaded.patterns[pattern_id]
        self.assertEqual(reloaded_pat.pattern_id, pattern_id)
        self.assertEqual(reloaded_pat.sequence_signature, [2000.0, 1990.0, 2020.0])
        self.assertEqual(reloaded_pat.occurrences_count, 1)
        self.assertEqual(reloaded_pat.continuation_count, 1)
        self.assertEqual(reloaded_pat.reversal_count, 0)
        self.assertEqual(len(reloaded_pat.outcomes), 1)
        self.assertEqual(reloaded_pat.outcomes[0]["experience_id"], "exp-test-001")

        # Step 5: Test Idempotent re-promotion protection (zero duplicate outcomes)
        promoted_again = memory_reloaded.promote_experiences_to_patterns()
        self.assertEqual(len(promoted_again), 0, "Re-promoting the same experience must create ZERO new outcomes.")
        self.assertEqual(len(memory_reloaded.patterns[pattern_id].outcomes), 1, "Pattern outcomes count must remain 1.")

    def test_corruption_recovery_and_snapshot_fallback(self) -> None:
        # Step 1: Create snapshot
        exp = ExperienceMemory(
            experience_id="exp-snap-001",
            symbol="EURUSD",
            timeframe="M15",
            timestamp=datetime.now(),
            situation_signature=[1.08, 1.07, 1.10],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Valid setup",
            max_favorable_excursion=0.02,
            max_adverse_excursion=-0.005,
            meta={"is_validated": True}
        )
        self.memory.add_experience(exp)
        self.memory.promote_experiences_to_patterns()

        snapshot_meta = self.memory.create_snapshot("backup_test_001")
        self.assertIn("backup_tag", snapshot_meta)

        # Step 2: Corrupt patterns_memory.json
        patterns_file = os.path.join(self.test_dir, "patterns_memory.json")
        with open(patterns_file, "w") as f:
            f.write("{CORRUPT_JSON_MALFORMED")

        # Step 3: Reload memory system -> Should trigger emergency recovery from snapshot
        memory_recovered = MarketMemorySystem(storage_dir=self.test_dir)
        self.assertGreater(len(memory_recovered.patterns), 0, "Corrupted memory should safely recover from snapshot.")

if __name__ == "__main__":
    unittest.main()
