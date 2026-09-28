import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app, val_state, state_lock

class TestProductionReadinessContract(unittest.TestCase):
    """Production readiness follows the active Research/DEMO architecture; Shadow is not a prerequisite."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_mt5_disconnected_blocks_production_readiness(self) -> None:
        with patch("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "DISCONNECTED"}):
            resp = self.client.get("/api/production-readiness")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("MT5 connector is disconnected" in r for r in data["blocking_reasons"]))

    def test_simulated_fallback_blocks_production_readiness(self) -> None:
        with patch("platform.system", return_value="Linux"):
            resp = self.client.get("/api/production-readiness")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("Simulated fallback active" in r for r in data["blocking_reasons"]))

    def test_stopped_research_worker_blocks_production_readiness(self) -> None:
        with patch("src.Application.Runtime.runtime_state.central_runtime_state.get_state", return_value={
            "research_status": "Stopped",
            "intelligence_status": "Stopped",
            "shadow_status": "Disabled"
        }):
            resp = self.client.get("/api/production-readiness")
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("research_worker" in r for r in data["blocking_reasons"]))

    def test_failed_validation_blocks_production_readiness(self) -> None:
        with state_lock:
            old_status = val_state.readiness_status
            old_failed = val_state.failed_count
            val_state.readiness_status = "Not Ready"
            val_state.failed_count = 1
        try:
            resp = self.client.get("/api/production-readiness")
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("Acceptance validation status" in r for r in data["blocking_reasons"]))
        finally:
            with state_lock:
                val_state.readiness_status = old_status
                val_state.failed_count = old_failed

    def test_all_active_architecture_blockers_clear(self) -> None:
        conn_mock = MagicMock()
        conn_mock.connected = True
        with patch("src.Application.Services.web_dashboard.global_research_runtime.provider.delegate.get_connection_health", return_value=conn_mock), \
             patch("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "CONNECTED"}), \
             patch("platform.system", return_value="Windows"), \
             patch("src.Application.Runtime.runtime_state.central_runtime_state.get_state", return_value={
                 "research_status": "Running",
                 "intelligence_status": "Stopped",
                 "shadow_status": "Disabled"
             }), \
             patch.dict(os.environ, {"LIVE_TRADING_ENABLED": "False"}):
            with state_lock:
                old_status = val_state.readiness_status
                old_failed = val_state.failed_count
                val_state.readiness_status = "Production Ready"
                val_state.failed_count = 0
            try:
                resp = self.client.get("/api/production-readiness")
                data = resp.json()
                self.assertEqual(data["status"], "Production Ready")
                self.assertEqual(data["production_readiness_score"], 100.0)
                self.assertEqual(data["blocking_reasons"], [])
            finally:
                with state_lock:
                    val_state.readiness_status = old_status
                    val_state.failed_count = old_failed

    def test_health_and_runtime_semantics_consistency(self) -> None:
        health_ready = self.client.get("/health/ready").json()
        prod_readiness = self.client.get("/api/production-readiness").json()
        runtime_status = self.client.get("/v1/runtime").json()
        if health_ready.get("status") == "NOT_READY":
            self.assertEqual(prod_readiness["status"], "Not Ready")
            self.assertFalse(runtime_status["production_ready"])
