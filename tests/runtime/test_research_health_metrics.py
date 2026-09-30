import unittest
from unittest.mock import MagicMock, patch

from src.Application.Runtime.runtime_state import central_runtime_state
from src.Application.Services.web_dashboard import get_research_health


class TestResearchHealthMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.old_state = central_runtime_state.get_state()

    def tearDown(self) -> None:
        central_runtime_state.update_multiple(self.old_state)

    def test_production_health_reads_central_research_worker_metrics(self):
        central_runtime_state.update_multiple({
            "research_status": "Running",
            "research_cycle_count": 7,
            "research_last_successful_cycle": "2026-09-30T12:00:00",
            "research_last_error": None,
        })

        fake_runtime = MagicMock()
        fake_runtime.provider.delegate.get_connection_health.return_value.connected = True
        fake_runtime.symbol = "XAUUSD"
        fake_runtime.timeframe = "H1"
        fake_runtime.worker_started_at = None

        with patch("src.Application.Services.web_dashboard.global_research_runtime", fake_runtime):
            health = get_research_health()

        self.assertTrue(health["worker_running"])
        self.assertEqual(health["cycle_count"], 7)
        self.assertEqual(
            health["last_successful_cycle"],
            "2026-09-30T12:00:00",
        )
        self.assertIsNone(health["last_error"])


if __name__ == "__main__":
    unittest.main()
