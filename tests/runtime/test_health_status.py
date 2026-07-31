import unittest
from src.Application.Services.web_dashboard import get_production_health, research_tracker

class TestHealthStatus(unittest.TestCase):
    def setUp(self) -> None:
        self.old_status = research_tracker.copy()

    def tearDown(self) -> None:
        research_tracker.clear()
        research_tracker.update(self.old_status)

    def test_health_online_status(self):
        """Checks health output when subsystems are fully running and connected."""
        research_tracker["mt5_status"] = "CONNECTED"
        research_tracker["worker_status"] = "RUNNING"

        health = get_production_health()
        self.assertEqual(health["status"], "Healthy")
        self.assertEqual(health["service"], "TradeYar-AI")
        self.assertEqual(health["api"], "Online")
        self.assertEqual(health["mt5"], "Connected")
        self.assertEqual(health["worker"], "Running")
        self.assertEqual(health["intelligence"], "Ready")
        self.assertIn("timestamp", health)

    def test_health_disconnected_status(self):
        """Checks health output when MT5 is disconnected and worker is recovering."""
        research_tracker["mt5_status"] = "DISCONNECTED"
        research_tracker["worker_status"] = "RECOVERING"

        health = get_production_health()
        self.assertEqual(health["status"], "Healthy")
        self.assertEqual(health["mt5"], "Disconnected")
        self.assertEqual(health["worker"], "Stopped")
