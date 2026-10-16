import json
import tempfile
import unittest
from pathlib import Path

from app.workers.intelligence_worker import IntelligenceWorker
from src.Application.Runtime.runtime_state import central_runtime_state


class FakeMemory:
    def __init__(self):
        self.loaded = False

    def load_all(self):
        self.loaded = True

    def get_learning_statistics(self):
        return {
            "total_experiences": 12,
            "patterns_created": 4,
            "concepts_learned": 1,
            "successful_patterns": 2,
            "failed_patterns": 1,
        }

    def promote_experiences_to_patterns(self):
        return [object()]

    def consolidate_patterns_to_concepts(self, min_samples, min_validation_score):
        assert min_samples == 4
        assert min_validation_score == 0.70
        return [object()]

    def get_patterns(self):
        return []


class TestIntelligenceWorker(unittest.TestCase):
    def test_cycle_refreshes_real_memory_and_writes_auditable_report(self):
        old_state = central_runtime_state.get_state()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                report_path = Path(temp_dir) / "active_learning_priorities.json"
                memory = FakeMemory()
                worker = IntelligenceWorker(memory_system=memory, report_path=str(report_path))

                report = worker.run_cycle()

                self.assertTrue(memory.loaded)
                self.assertEqual(report["status"], "COMPLETED")
                self.assertEqual(report["data_source"], "PERSISTED_BRAIN_MEMORY")
                self.assertFalse(report["market_data_fabricated"])
                self.assertEqual(report["broker_orders_submitted"], 0)
                self.assertEqual(report["new_patterns_promoted"], 1)
                self.assertEqual(report["concepts_consolidated"], 1)
                self.assertEqual(report["after"]["total_experiences"], 12)
                self.assertTrue(report_path.exists())
                saved = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["status"], "COMPLETED")
                self.assertEqual(central_runtime_state.get_key("intelligence_status"), "Running")
        finally:
            central_runtime_state.update_multiple(old_state)


if __name__ == "__main__":
    unittest.main()
