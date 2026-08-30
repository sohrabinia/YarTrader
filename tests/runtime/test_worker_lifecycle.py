import time
import unittest
from app.workers.research_worker import ResearchWorker
from app.workers.intelligence_worker import IntelligenceWorker
from src.Application.Runtime.runtime_state import central_runtime_state

class TestWorkerLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.old_central_state = central_runtime_state.get_state()

    def tearDown(self) -> None:
        central_runtime_state.update_multiple(self.old_central_state)

    def test_research_worker_start_stop(self):
        """Verifies ResearchWorker starting and stopping lifecycle cleanly and updating central state."""
        worker = ResearchWorker(interval_sec=1.0)
        self.assertFalse(worker.is_running)
        self.assertEqual(worker.status, "IDLE")

        worker.start()
        self.assertTrue(worker.is_running)
        self.assertEqual(worker.status, "RUNNING")
        self.assertIn(central_runtime_state.get_key("research_status"), ["Running", "Recovering"])

        worker.stop()
        self.assertFalse(worker.is_running)
        self.assertEqual(worker.status, "STOPPED")
        self.assertEqual(central_runtime_state.get_key("research_status"), "Stopped")

    def test_intelligence_worker_start_stop(self):
        """Verifies IntelligenceWorker lifecycle start/stop cleanly and updating central state."""
        worker = IntelligenceWorker(interval_sec=1.0)
        worker.start()
        self.assertTrue(worker.is_running)
        self.assertIn(central_runtime_state.get_key("intelligence_status"), ["Running", "Recovering"])

        worker.stop()
        self.assertFalse(worker.is_running)
        self.assertEqual(central_runtime_state.get_key("intelligence_status"), "Stopped")
