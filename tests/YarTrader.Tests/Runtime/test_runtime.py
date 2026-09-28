import os
import unittest
from src.Infrastructure.exceptions import ValidationException
from src.Infrastructure.Configuration import (
    EnvironmentType,
    get_current_environment,
    ConfigurationManager,
    BaseSettings,
    DevelopmentSettings,
    SandboxSettings,
    ProductionSettings,
    SimulationSettings
)
from src.Infrastructure.DI import DIContainer, container_instance, register_services
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Learning.Interfaces.interfaces import ILearningEngine

from src.Application.Runtime import (
    RuntimeLifecycle,
    LifecycleState,
    RuntimeHost,
    RuntimeLauncher
)


class TestTradeYarRuntimeAndConfiguration(unittest.TestCase):
    """
    Unit and integration tests for the TradeYar AI Runtime Foundation.
    Verifies environment config, DI registrations, lifecycle transitions, and host execution.
    """

    def setUp(self) -> None:
        ConfigurationManager.reset()
        container_instance.clear()

    def tearDown(self) -> None:
        ConfigurationManager.reset()
        container_instance.clear()

    # --- Configuration Subsystem Tests ---

    def test_environment_resolution(self) -> None:
        """Verify fallback and resolution of EnvironmentType from env vars."""
        os.environ["TRADEYAR_ENV"] = "simulation"
        self.assertEqual(get_current_environment(), EnvironmentType.SIMULATION)

        os.environ["TRADEYAR_ENV"] = "invalid_environment"
        self.assertEqual(get_current_environment(), EnvironmentType.DEVELOPMENT)

    def test_settings_by_environment(self) -> None:
        """Verify environment-specific settings load with appropriate defaults."""
        dev_config = ConfigurationManager.get_config(EnvironmentType.DEVELOPMENT)
        self.assertEqual(dev_config.log_level, "DEBUG")
        self.assertEqual(dev_config.lookback_days, 5)

        ConfigurationManager.reset()
        # Set a dummy secure token to satisfy the new production fail-closed security contract
        old_token = os.environ.get("RG_DB_SECURE_TOKEN")
        os.environ["RG_DB_SECURE_TOKEN"] = "prod-token-super-secret-unique-key-12345"
        try:
            prod_config = ConfigurationManager.get_config(EnvironmentType.PRODUCTION)
            self.assertEqual(prod_config.log_level, "INFO")
            self.assertEqual(prod_config.lookback_days, 15)
        finally:
            if old_token is not None:
                os.environ["RG_DB_SECURE_TOKEN"] = old_token
            else:
                os.environ.pop("RG_DB_SECURE_TOKEN", None)

    def test_settings_validation_boundaries(self) -> None:
        """Verify settings parameter boundaries raising validation errors."""
        with self.assertRaises(ValidationException):
            BaseSettings({"lookback_days": 400})

        with self.assertRaises(ValidationException):
            BaseSettings({"api_timeout_sec": 70.0})

        with self.assertRaises(ValidationException):
            BaseSettings({"max_retries": 15})

    def test_settings_compliance_and_safety(self) -> None:
        """Verify that simulation mode is strictly enforced and forbidden keywords are blocked."""
        # 1. Enforce simulation mode only
        with self.assertRaises(ValidationException):
            BaseSettings({"simulation_mode": False})

        # 2. Scanner blocking active-trading indicators
        with self.assertRaises(ValidationException):
            BaseSettings({"some_other_key": "place_order"})

    # --- Dependency Injection (DI) Tests ---

    def test_di_container_singleton_vs_transient(self) -> None:
        """Verify DIContainer correctly resolves singletons and transients."""
        container = DIContainer()

        class DummyService:
            pass

        # Singleton resolution
        container.register_singleton(DummyService, DummyService)
        inst1 = container.resolve(DummyService)
        inst2 = container.resolve(DummyService)
        self.assertIs(inst1, inst2)

        # Transient resolution
        container.register_transient(DummyService, DummyService)
        inst3 = container.resolve(DummyService)
        inst4 = container.resolve(DummyService)
        self.assertIsNot(inst3, inst4)

    def test_di_registrations_by_environment(self) -> None:
        """Verify register_services configures expected interfaces into the container."""
        register_services(container=container_instance, environment=EnvironmentType.TEST)

        # Verify resolution
        dp = container_instance.resolve(IMarketDataProvider)
        re = container_instance.resolve(IResearchEngine)
        strat = container_instance.resolve(IStrategyEvaluator)
        risk = container_instance.resolve(IRiskEngine)
        dec = container_instance.resolve(IDecisionEngine)
        learn = container_instance.resolve(ILearningEngine)

        self.assertIsNotNone(dp)
        self.assertIsNotNone(re)
        self.assertIsNotNone(strat)
        self.assertIsNotNone(risk)
        self.assertIsNotNone(dec)
        self.assertIsNotNone(learn)

    # --- Runtime Lifecycle & Host Tests ---

    def test_runtime_lifecycle_transitions(self) -> None:
        """Verify step-by-step state transitions and invalid transition blocks."""
        lc = RuntimeLifecycle()
        self.assertEqual(lc.state, LifecycleState.UNINITIALIZED)

        # Valid transitions
        lc.initialize()
        self.assertEqual(lc.state, LifecycleState.INITIALIZED)

        lc.start()
        self.assertEqual(lc.state, LifecycleState.RUNNING)

        lc.stop()
        self.assertEqual(lc.state, LifecycleState.STOPPED)

        lc.shutdown()
        self.assertEqual(lc.state, LifecycleState.SHUTDOWN)

        # Invalid transition checks
        lc_err = RuntimeLifecycle()
        with self.assertRaises(ValueError):
            lc_err.start()  # Cannot start before initialize

    def test_runtime_host_and_launcher_execution(self) -> None:
        """Verify launcher starting the host, configuring environment, and shutting down successfully."""
        launcher = RuntimeLauncher()
        host = launcher.launch(EnvironmentType.DEVELOPMENT, overrides={"lookback_days": 8})

        self.assertEqual(host.lifecycle.state, LifecycleState.RUNNING)
        self.assertEqual(host.config.lookback_days, 8)

        # Stop and Shutdown
        host.stop()
        self.assertEqual(host.lifecycle.state, LifecycleState.STOPPED)

        host.shutdown()
        self.assertEqual(host.lifecycle.state, LifecycleState.SHUTDOWN)
