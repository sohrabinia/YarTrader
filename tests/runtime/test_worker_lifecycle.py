import time
import unittest
from app.workers.research_worker import ResearchWorker
from app.workers.intelligence_worker import IntelligenceWorker
from app.workers.shadow_worker import ShadowWorker
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
        self.assertIn(worker.status, ["RUNNING", "RECOVERING"])
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

    def test_shadow_worker_start_stop_idle_state(self):
        """Verifies ShadowWorker startup transitions to IDLE when there is no active shadow session/positions."""
        # Ensure account has no open positions
        worker = ShadowWorker(interval_sec=1.0)
        worker.engine.reset_account()
        self.assertEqual(len(worker.engine.account.get_open_positions()), 0)

        worker.start()
        self.assertTrue(worker.is_running)

        # Give loop thread a tiny fraction of time to run one tick
        time.sleep(0.2)

        # Must be IDLE, NOT Recovering because tick_update skips gracefully!
        self.assertEqual(central_runtime_state.get_key("shadow_status"), "IDLE")
        self.assertEqual(worker.status, "IDLE")

        worker.stop()
        self.assertFalse(worker.is_running)
        self.assertEqual(central_runtime_state.get_key("shadow_status"), "Stopped")

    def test_shadow_worker_running_state_with_positions(self):
        """Verifies ShadowWorker transitions to Running when active shadow positions exist."""
        worker = ShadowWorker(interval_sec=1.0)
        worker.engine.reset_account()

        # Mock open virtual position
        worker.engine.handle_decision("BUY", current_price=1900.0, symbol="XAUUSD")
        self.assertEqual(len(worker.engine.account.get_open_positions()), 1)

        worker.start()
        self.assertTrue(worker.is_running)

        time.sleep(0.2)

        # Must be RUNNING because there is an active trade!
        self.assertEqual(central_runtime_state.get_key("shadow_status"), "Running")
        self.assertEqual(worker.status, "RUNNING")

        worker.stop()
        worker.engine.reset_account()
