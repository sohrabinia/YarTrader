import os
import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_research_runtime

class TestMTFDataProvenanceRegression(unittest.TestCase):
    """
    Forensic regression test suite verifying real market data provenance,
    fail-closed behavior on disconnected MT5 provider, and symbol contamination prevention.
    """
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_mtf_disconnected_fails_closed_data_unavailable(self) -> None:
        """Confirms that when MT5 provider is disconnected, /api/intelligence/multi-timeframe returns 400 DATA UNAVAILABLE."""
        delegate = global_research_runtime.provider.delegate
        orig_state = getattr(delegate, "_connected", True)
        try:
            delegate.set_connected(False)
            response = self.client.get("/api/intelligence/multi-timeframe")
            self.assertEqual(response.status_code, 400)
            self.assertIn("DATA UNAVAILABLE", response.json()["detail"])
        finally:
            delegate.set_connected(orig_state)

    def test_current_vs_historical_signal_separation(self) -> None:
        """Confirms that completed signals (TARGET_HIT/STOP_HIT) do not leak into active /api/user/signals."""
        response_active = self.client.get("/api/user/signals")
        self.assertEqual(response_active.status_code, 200)
        active_signals = response_active.json()

        for sig in active_signals:
            self.assertIn(sig["status"], ["ACTIVE", "CREATED", "RUNNING"])
            self.assertNotIn(sig["status"], ["TARGET_HIT", "STOP_HIT", "COMPLETED"])

        response_history = self.client.get("/api/user/history")
        self.assertEqual(response_history.status_code, 200)
        history_signals = response_history.json()

        for sig in history_signals:
            self.assertNotIn(sig["status"], ["ACTIVE", "CREATED", "RUNNING"])

if __name__ == "__main__":
    unittest.main()
