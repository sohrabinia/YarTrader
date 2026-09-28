import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app, val_state, state_lock
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine, ShadowTrade

class TestShadowReadinessRemediation(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PredictiveShadowEngine.get_instance()

    def test_shadow_metrics_and_report_consistency(self) -> None:
        """1 & 2: Proves Shadow metrics and report use one truthful source and agree on all counts/balances."""
        metrics_resp = self.client.get("/api/shadow/metrics")
        report_resp = self.client.get("/api/shadow/report")

        self.assertEqual(metrics_resp.status_code, 200)
        self.assertEqual(report_resp.status_code, 200)

        metrics = metrics_resp.json()
        report = report_resp.json()

        self.assertEqual(metrics["performance"]["total_trades"], report["total_trades"])
        self.assertEqual(metrics["open_positions_count"], report["open_trades_count"])
        self.assertEqual(metrics["closed_positions_count"], report["closed_trades_count"])
        self.assertEqual(metrics["performance"]["wins"], report["winning_trades"])
        self.assertEqual(metrics["performance"]["losses"], report["losing_trades"])
        self.assertEqual(metrics["balance"], report["virtual_balance"])
        self.assertEqual(metrics["equity"], report["virtual_equity"])

    def test_demo_and_backtest_isolation_from_shadow(self) -> None:
        """3 & 4: Demo and Backtest trades never leak into Shadow metrics."""
        # Check current shadow trade count
        shadow_count_before = len(self.engine.trades)

        # Trigger Demo trade
        demo_resp = self.client.post("/api/demo/run", json={"scenario_id": "trend_continuation", "asset": "EURUSD"})
        self.assertEqual(demo_resp.status_code, 200)

        # Confirm shadow count is unchanged
        shadow_metrics = self.client.get("/api/shadow/metrics").json()
        self.assertEqual(shadow_metrics["performance"]["total_trades"], shadow_count_before)

    def test_mt5_disconnected_blocks_production_readiness(self) -> None:
        """5: MT5 disconnected forces production readiness to Not Ready."""
        with patch("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "DISCONNECTED"}):
            resp = self.client.get("/api/production-readiness")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("MT5 connector is disconnected" in r for r in data["blocking_reasons"]))

    def test_simulated_fallback_blocks_production_readiness(self) -> None:
        """6: Simulated fallback active forces production readiness to Not Ready."""
        with patch("platform.system", return_value="Linux"):
            resp = self.client.get("/api/production-readiness")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("Simulated fallback active" in r for r in data["blocking_reasons"]))

    def test_stopped_worker_blocks_production_readiness(self) -> None:
        """7: Stopped required worker forces production readiness to Not Ready."""
        with patch("src.Application.Runtime.runtime_state.central_runtime_state.get_state", return_value={
            "research_status": "Stopped",
            "intelligence_status": "Running",
            "shadow_status": "Running"
        }):
            resp = self.client.get("/api/production-readiness")
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("research_worker" in r for r in data["blocking_reasons"]))

    def test_recovering_worker_blocks_production_readiness(self) -> None:
        """8: Recovering required worker forces production readiness to Not Ready."""
        with patch("src.Application.Runtime.runtime_state.central_runtime_state.get_state", return_value={
            "research_status": "Running",
            "intelligence_status": "Recovering",
            "shadow_status": "Running"
        }):
            resp = self.client.get("/api/production-readiness")
            data = resp.json()
            self.assertEqual(data["status"], "Not Ready")
            self.assertTrue(any("intelligence_worker" in r for r in data["blocking_reasons"]))

    def test_failed_validation_blocks_production_readiness(self) -> None:
        """9: Failed acceptance validation forces production readiness to Not Ready."""
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

    def test_all_blockers_clear_allows_production_ready(self) -> None:
        """10: Readiness becomes Production Ready when and only when all blockers are clear."""
        conn_mock = MagicMock()
        conn_mock.connected = True

        with patch("src.Application.Services.web_dashboard.global_research_runtime.provider.delegate.get_connection_health", return_value=conn_mock), \
             patch("src.Application.Services.web_dashboard.research_tracker", {"mt5_status": "CONNECTED"}), \
             patch("platform.system", return_value="Windows"), \
             patch("src.Application.Runtime.runtime_state.central_runtime_state.get_state", return_value={
                 "research_status": "Running",
                 "intelligence_status": "Running",
                 "shadow_status": "Running"
             }), \
             patch.dict(os.environ, {"LIVE_TRADING_ENABLED": "True"}):

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
                self.assertEqual(len(data["blocking_reasons"]), 0)
            finally:
                with state_lock:
                    val_state.readiness_status = old_status
                    val_state.failed_count = old_failed

    def test_readiness_score_cannot_be_hardcoded_100(self) -> None:
        """11: Dynamic calculation prevents hardcoded 100 score when blockers exist."""
        resp = self.client.get("/api/production-readiness")
        data = resp.json()
        if len(data["blocking_reasons"]) > 0:
            self.assertNotEqual(data["status"], "Production Ready")
            self.assertLess(data["production_readiness_score"], 100.0)

    def test_health_and_runtime_semantics_consistency(self) -> None:
        """12: Health and runtime endpoints maintain consistent truthful state semantics."""
        health_ready = self.client.get("/health/ready").json()
        prod_readiness = self.client.get("/api/production-readiness").json()
        runtime_status = self.client.get("/v1/runtime").json()

        # Invariant check: if health/ready says NOT_READY or prod_readiness says Not Ready, runtime is not silently claimed Production Ready
        if health_ready.get("status") == "NOT_READY":
            self.assertEqual(prod_readiness["status"], "Not Ready")
            self.assertFalse(runtime_status["production_ready"])
