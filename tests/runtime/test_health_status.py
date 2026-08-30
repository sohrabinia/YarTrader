import unittest
from src.Application.Services.web_dashboard import get_production_health, research_tracker
from src.Application.Runtime.runtime_state import central_runtime_state

class TestHealthStatus(unittest.TestCase):
    def setUp(self) -> None:
        self.old_status = research_tracker.copy()
        self.old_central_state = central_runtime_state.get_state()

    def tearDown(self) -> None:
        research_tracker.clear()
        research_tracker.update(self.old_status)
        central_runtime_state.update_multiple(self.old_central_state)

    def test_health_online_status(self):
        """Checks health output when subsystems are fully running and connected."""
        from unittest.mock import patch

        # Configure central state
        central_runtime_state.update_multiple({
            "worker_status": "Running",
            "research_status": "Running",
            "intelligence_status": "Running",
            "shadow_status": "Disabled"
        })

        with patch.dict("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "CONNECTED", "worker_status": "RUNNING"}):
            health = get_production_health()
            self.assertIn(health["status"], ["Healthy", "healthy"])
            self.assertTrue(health["service"] == "TradeYar-AI" or health["service"] == "YarTrader")
            self.assertTrue(health["api"] == "Online" or health["api"] is True)
            self.assertEqual(health["mt5"], "Connected")
            self.assertEqual(health["worker"], "Running")
            self.assertEqual(health["research_worker"], "Running")
            self.assertEqual(health["intelligence_worker"], "Running")
            self.assertEqual(health["shadow_worker"], "Disabled")
            self.assertEqual(health["shadow_trading"], "Disabled")
            self.assertIn("timestamp", health)

    def test_health_disconnected_status(self):
        """Checks health output when MT5 is disconnected and worker is recovering."""
        from unittest.mock import patch

        # Configure central state
        central_runtime_state.update_multiple({
            "worker_status": "Stopped",
            "research_status": "Stopped",
            "intelligence_status": "Stopped",
            "shadow_status": "Stopped"
        })

        with patch.dict("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "DISCONNECTED", "worker_status": "STOPPED"}):
            health = get_production_health()
            self.assertIn(health["status"], ["Healthy", "healthy"])
            self.assertEqual(health["mt5"], "Disconnected")
            self.assertEqual(health["worker"], "Stopped")
