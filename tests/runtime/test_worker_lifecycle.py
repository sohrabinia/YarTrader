import time
import unittest
from app.workers.research_worker import ResearchWorker
from app.workers.intelligence_worker import IntelligenceWorker
from app.workers.shadow_worker import ShadowWorker

class TestWorkerLifecycle(unittest.TestCase):
    def test_research_worker_start_stop(self):
        """Verifies ResearchWorker starting and stopping lifecycle cleanly."""
        worker = ResearchWorker(interval_sec=1.0)
        self.assertFalse(worker.is_running)
        self.assertEqual(worker.status, "IDLE")

        worker.start()
        self.assertTrue(worker.is_running)
        self.assertEqual(worker.status, "RUNNING")

        worker.stop()
        self.assertFalse(worker.is_running)
        self.assertEqual(worker.status, "STOPPED")

    def test_intelligence_worker_start_stop(self):
        """Verifies IntelligenceWorker lifecycle start/stop cleanly."""
        worker = IntelligenceWorker(interval_sec=1.0)
        worker.start()
        self.assertTrue(worker.is_running)
        worker.stop()
        self.assertFalse(worker.is_running)

    def test_shadow_worker_start_stop(self):
        """Verifies ShadowWorker lifecycle start/stop cleanly."""
        worker = ShadowWorker(interval_sec=1.0)
        worker.start()
        self.assertTrue(worker.is_running)
        worker.stop()
        self.assertFalse(worker.is_running)
