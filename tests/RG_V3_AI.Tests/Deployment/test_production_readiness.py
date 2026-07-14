import os
import unittest
import json
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.config import ProductionConfig, ConfigManager
from src.Application.Deployment.observability import StructuredLogger, PerformanceMetricsTracker
from src.Application.Deployment.health import ProductionHealthChecker
from src.Application.Services.api import ServiceRequestDTO, ServiceOrchestrator


class TestProductionReadinessFoundation(unittest.TestCase):
    """
    Unit and integration tests for Phase 35: Production Readiness & Deployment Foundation.
    Verifies configurations, structured logging, health checker diagnostics, API endpoints,
    and strict non-trading safety compliance.
    """

    def setUp(self) -> None:
        ConfigManager.reset()

    def tearDown(self) -> None:
        ConfigManager.reset()

    def test_production_config_validation_success(self) -> None:
        """Verify valid configurations load and validate successfully."""
        config = ProductionConfig({
            "ENVIRONMENT": "production",
            "LOOKBACK_DAYS": 20,
            "API_TIMEOUT": 10.0,
            "MAX_RETRIES": 5,
            "LOG_LEVEL": "INFO",
            "DB_SECURE_TOKEN": "valid-secure-database-token"
        })

        self.assertEqual(config.environment, "production")
        self.assertEqual(config.lookback_days, 20)
        self.assertEqual(config.api_timeout_sec, 10.0)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.log_level, "INFO")
        self.assertTrue(config.runtime_check())

    def test_production_config_validation_invalid_environment(self) -> None:
        """Verify invalid environments trigger ValidationExceptions."""
        with self.assertRaises(ValidationException) as context:
            ProductionConfig({"ENVIRONMENT": "invalid_env"})
        self.assertIn("Invalid environment", str(context.exception))

    def test_production_config_validation_out_of_bounds(self) -> None:
        """Verify that lookback days or timeout out-of-bounds trigger ValidationExceptions."""
        # 1. Invalid lookback days
        with self.assertRaises(ValidationException) as context:
            ProductionConfig({"LOOKBACK_DAYS": 400})
        self.assertIn("Lookback days must be within", str(context.exception))

        # 2. Invalid API timeout
        with self.assertRaises(ValidationException) as context:
            ProductionConfig({"API_TIMEOUT": 0.0})
        self.assertIn("API timeout must be within", str(context.exception))

        # 3. Invalid Max Retries
        with self.assertRaises(ValidationException) as context:
            ProductionConfig({"MAX_RETRIES": 15})
        self.assertIn("Max connection retries must be within", str(context.exception))

    def test_structured_logging_output(self) -> None:
        """Verify StructuredLogger generates correct JSON schema records."""
        logger = StructuredLogger(service_name="Test_Service")
        log_record = logger.info("ApplicationStarted", {"node_id": "node-12"})

        # Verify output is valid JSON
        record_dict = json.loads(log_record)
        self.assertEqual(record_dict["service"], "Test_Service")
        self.assertEqual(record_dict["level"], "INFO")
        self.assertEqual(record_dict["event"], "ApplicationStarted")
        self.assertEqual(record_dict["metadata"]["node_id"], "node-12")
        self.assertIn("timestamp", record_dict)

        # Verify stored logs
        self.assertEqual(len(logger.get_logs()), 1)

    def test_performance_metrics_tracker(self) -> None:
        """Verify PerformanceMetricsTracker correctly stores and averages latencies."""
        tracker = PerformanceMetricsTracker()
        tracker.record_pipeline_execution(100.0)
        tracker.record_pipeline_execution(150.0)
        tracker.record_agent_latency(20.0)
        tracker.record_warning("Slow response on news stream.")
        tracker.record_error("Failed to parse event.")

        summary = tracker.get_performance_summary()
        self.assertEqual(summary["average_pipeline_execution_ms"], 125.0)
        self.assertEqual(summary["average_agent_latency_ms"], 20.0)
        self.assertEqual(summary["warning_count"], 1)
        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(summary["recent_errors"], ["Failed to parse event."])

    def test_health_checker_diagnostics(self) -> None:
        """Verify health checker executes diagnostics on all subsystems."""
        checker = ProductionHealthChecker()
        diagnostics = checker.run_comprehensive_diagnostics()

        self.assertEqual(diagnostics["status"], "HEALTHY")
        self.assertIn("uptime_seconds", diagnostics)
        self.assertIn("timestamp", diagnostics)

        subsystems = diagnostics["subsystems"]
        self.assertEqual(subsystems["application"]["status"], "HEALTHY")
        self.assertEqual(subsystems["intelligence_pipeline"]["status"], "HEALTHY")
        self.assertEqual(subsystems["data_provider"]["status"], "HEALTHY")
        self.assertEqual(subsystems["agent_subsystem"]["status"], "HEALTHY")
        self.assertEqual(subsystems["memory_subsystem"]["status"], "HEALTHY")
        self.assertEqual(subsystems["dashboard_subsystem"]["status"], "HEALTHY")

    def test_health_api_orchestrator_integration(self) -> None:
        """Verify api.py routing handles /v1/health diagnostics request correctly."""
        orchestrator = ServiceOrchestrator()
        dto = ServiceRequestDTO("client_1", "secret_token_1")
        response = orchestrator.handle_request("/v1/health", dto)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "HEALTHY")
        self.assertIn("subsystems", response.data)

    def test_metrics_api_orchestrator_integration(self) -> None:
        """Verify api.py routing handles /v1/metrics requests correctly."""
        orchestrator = ServiceOrchestrator()
        dto = ServiceRequestDTO("client_1", "secret_token_1")
        response = orchestrator.handle_request("/v1/metrics", dto)

        self.assertEqual(response.status_code, 200)
        self.assertIn("production_metrics", response.data)
        metrics = response.data["production_metrics"]
        self.assertEqual(metrics["average_pipeline_execution_ms"], 125.4)

    def test_strict_non_trading_leakage_safety(self) -> None:
        """Verify that production config contains absolutely zero active trading triggers."""
        forbidden_keywords = ["buy_signal", "sell_signal", "place_order", "execute_trade", "open_position", "send_transaction"]

        # Scan our new config file
        path = "src/Application/Deployment/config.py"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for kw in forbidden_keywords:
                    self.assertNotIn(kw, content, f"Violation: Forbidden trading keyword '{kw}' found in configuration source code.")
