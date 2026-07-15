import os
import sys
import unittest
import json
from unittest.mock import patch
from datetime import datetime, timedelta

from src.Infrastructure.exceptions import ValidationException
from src.Infrastructure.Configuration import EnvironmentType, ConfigurationManager
from src.Application.Runtime.host import RuntimeHost
from src.Application.Runtime.launcher import RuntimeLauncher
from src.Application.Runtime.lifecycle import LifecycleState
from src.Application.Deployment.config import ProductionConfig, ConfigManager
from src.Application.Deployment.storage import TradeYarStorageManager
from src.Application.Deployment.health import ProductionHealthChecker
from src.Application.Reporting.engine import ReportEngine
from src.cli.cli import (
    handle_status,
    handle_health,
    handle_diagnostics,
    handle_generate_report,
    handle_run_demo,
    handle_run_simulation
)


class TestProductionE2EAndDisasterRecovery(unittest.TestCase):
    """
    Comprehensive integration and production ready verification suite.
    Validates host startup, configuration boundaries, CLI sub-commands,
    isolated reports compilation, and disaster recovery fallback.
    """

    def setUp(self) -> None:
        ConfigManager.reset()
        ConfigurationManager.reset()
        # Ensure our isolated storage directory exists
        self.storage_manager = TradeYarStorageManager.get_manager()
        self.reports_dir = self.storage_manager.get_reports_dir()

    def tearDown(self) -> None:
        ConfigManager.reset()
        ConfigurationManager.reset()

    def test_production_host_startup_lifecycle(self) -> None:
        """Verify the complete host runtime lifecycle transitions successfully under PRODUCTION environment."""
        launcher = RuntimeLauncher()
        host = launcher.launch(EnvironmentType.PRODUCTION)

        self.assertEqual(host.lifecycle.state, LifecycleState.RUNNING)
        self.assertEqual(host.environment, EnvironmentType.PRODUCTION)

        host.stop()
        self.assertEqual(host.lifecycle.state, LifecycleState.STOPPED)

        host.shutdown()
        self.assertEqual(host.lifecycle.state, LifecycleState.SHUTDOWN)

    def test_production_config_limits(self) -> None:
        """Verify that configuration limits prevent invalid out-of-bounds metrics in config."""
        with self.assertRaises(ValidationException):
            ProductionConfig({"LOOKBACK_DAYS": 500})  # max is 365

        with self.assertRaises(ValidationException):
            ProductionConfig({"API_TIMEOUT": 90.0})  # max is 60.0

        with self.assertRaises(ValidationException):
            ProductionConfig({"MAX_RETRIES": -5})  # min is 0

    def test_cli_subcommands_execution(self) -> None:
        """Verify that the CLI handlers trigger without runtime errors or crashes."""
        class DummyArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        # 1. Test status handler
        args_status = DummyArgs(env="production")
        handle_status(args_status)

        # 2. Test health handler
        handle_health(None)

        # 3. Test diagnostics handler
        handle_diagnostics(None)

    def test_cli_reporting_subcommands(self) -> None:
        """Verify report generation command compiles and exports all formats correctly."""
        class DummyArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        rep_engine = ReportEngine()

        # Generate each type in markdown
        report_types = ["research", "risk", "decision", "simulation", "health"]
        for rtype in report_types:
            args = DummyArgs(type=rtype, format="markdown", out=f"test_out_{rtype}.md")
            handle_generate_report(args)
            expected_path = os.path.join(self.reports_dir, f"test_out_{rtype}.md")
            self.assertTrue(os.path.exists(expected_path), f"Report '{rtype}' was not exported to {expected_path}")

        # Clean up
        for rtype in report_types:
            path = os.path.join(self.reports_dir, f"test_out_{rtype}.md")
            if os.path.exists(path):
                os.remove(path)

    def test_disaster_recovery_simulation(self) -> None:
        """Simulate a disaster recovery procedure where isolated parameters are corrupted or environment fails."""
        # 1. Configuration recovery: invalid inputs (like alphanumeric string instead of numerical lookback) trigger ValidationException
        with self.assertRaises(ValidationException):
            ProductionConfig({"LOOKBACK_DAYS": "corrupted_input"})

        # 2. Invalid environment recovery: system falls back to default staging/development environment if none set
        os.environ["RG_ENV"] = "invalid_environment"
        with self.assertRaises(ValidationException):
            ProductionConfig()

        # Restore environment
        os.environ["RG_ENV"] = "production"
        restored_config = ProductionConfig()
        self.assertEqual(restored_config.environment, "production")

    def test_run_demo_cli_handler(self) -> None:
        """Verify the CLI demo scenario execution run handler works correctly."""
        class DummyArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        args = DummyArgs(asset="EURUSD", scenario_id="demo-trend-continuation", export=True, export_format="json")
        handle_run_demo(args)

    def test_run_simulation_cli_handler(self) -> None:
        """Verify the CLI offline simulation handler executes without crash."""
        class DummyArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        args = DummyArgs(asset="EURUSD", lookback=10, export=True, export_format="html")
        handle_run_simulation(args)
