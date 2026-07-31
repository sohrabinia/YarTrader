import unittest
from datetime import datetime
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.External.interfaces import IDataProvider
from src.Data.Gateway.gateway import ProviderRegistry, ProviderResolver, DataRequestRouter, ExternalDataGateway
from src.Data.Simulation.simulation import SimulationDataProvider
from src.Infrastructure.exceptions import ValidationException


class MockDataProvider(IDataProvider):
    def __init__(self, provider_id: str, supported: list, health: ProviderHealthStatus) -> None:
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.MT5,
            supported_symbols=supported
        )
        self._health = health

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def check_health(self) -> ProviderHealthStatus:
        return self._health

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        return ExternalDataResponse(
            request_id=request.request_id or "id",
            provider_id=self._metadata.provider_id,
            raw_data=[]
        )


class TestDataProviderGatewayAndRegistry(unittest.TestCase):
    """
    Test suite verifying external data provider registration, discovery,
    resolution, health status, and gateway routing. (25 unit tests)
    """

    def setUp(self) -> None:
        self.registry = ProviderRegistry()
        self.resolver = ProviderResolver(self.registry)
        self.router = DataRequestRouter(self.resolver)
        self.p_healthy = MockDataProvider("primary-mt5", ["AAPL", "BTCUSD"], ProviderHealthStatus.HEALTHY)
        self.p_degraded = MockDataProvider("backup-mt5", ["AAPL"], ProviderHealthStatus.DEGRADED)
        self.p_unhealthy = MockDataProvider("unhealthy-mt5", ["BTCUSD"], ProviderHealthStatus.UNHEALTHY)

    # 1. Registry Tests (8 tests)
    def test_registry_1_register_valid_provider(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.assertEqual(self.registry.get_provider("primary-mt5"), self.p_healthy)

    def test_registry_2_list_providers_reflects_registration(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.registry.register_provider(self.p_degraded)
        self.assertEqual(len(self.registry.list_providers()), 2)

    def test_registry_3_unregister_removes_provider(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.registry.unregister_provider("primary-mt5")
        self.assertIsNone(self.registry.get_provider("primary-mt5"))

    def test_registry_4_get_unregistered_returns_none(self) -> None:
        self.assertIsNone(self.registry.get_provider("nonexistent"))

    def test_registry_5_register_none_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.registry.register_provider(None)

    def test_registry_6_register_missing_metadata_fails(self) -> None:
        class BrokenProvider(IDataProvider):
            @property
            def metadata(self): return None
            def check_health(self): return ProviderHealthStatus.HEALTHY
            def fetch_data(self, r): return None
        with self.assertRaises(ValidationException):
            self.registry.register_provider(BrokenProvider())

    def test_registry_7_register_empty_provider_id_fails(self) -> None:
        class BrokenIDProvider(IDataProvider):
            @property
            def metadata(self): return DataProviderMetadata(provider_id="", source_type=DataSourceType.MT5)
            def check_health(self): return ProviderHealthStatus.HEALTHY
            def fetch_data(self, r): return None
        with self.assertRaises(ValidationException):
            self.registry.register_provider(BrokenIDProvider())

    def test_registry_8_multiple_unregisters_are_safe(self) -> None:
        self.registry.unregister_provider("unknown")
        self.registry.unregister_provider("unknown")

    # 2. Resolver Tests (8 tests)
    def test_resolver_1_resolves_healthy_primary(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.registry.register_provider(self.p_degraded)
        # Both support AAPL, but healthy is preferred over degraded
        resolved = self.resolver.resolve_provider("AAPL")
        self.assertEqual(resolved, self.p_healthy)

    def test_resolver_2_resolves_degraded_fallback(self) -> None:
        self.registry.register_provider(self.p_degraded)
        resolved = self.resolver.resolve_provider("AAPL")
        self.assertEqual(resolved, self.p_degraded)

    def test_resolver_3_unhealthy_is_never_resolved(self) -> None:
        self.registry.register_provider(self.p_unhealthy)
        resolved = self.resolver.resolve_provider("BTCUSD")
        self.assertIsNone(resolved)

    def test_resolver_4_no_provider_available_returns_none(self) -> None:
        resolved = self.resolver.resolve_provider("MSFT")
        self.assertIsNone(resolved)

    def test_resolver_5_get_alternate_resolves_correct_fallback(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.registry.register_provider(self.p_degraded)
        # Alternate for AAPL excluding healthy should be degraded
        alt = self.resolver.get_alternate_provider("AAPL", exclude_provider_id="primary-mt5")
        self.assertEqual(alt, self.p_degraded)

    def test_resolver_6_get_alternate_returns_none_if_no_other_healthy_exists(self) -> None:
        self.registry.register_provider(self.p_healthy)
        alt = self.resolver.get_alternate_provider("AAPL", exclude_provider_id="primary-mt5")
        self.assertIsNone(alt)

    def test_resolver_7_get_alternate_ignores_unhealthy_providers(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.registry.register_provider(self.p_unhealthy)
        alt = self.resolver.get_alternate_provider("BTCUSD", exclude_provider_id="primary-mt5")
        self.assertIsNone(alt)

    def test_resolver_8_resolves_correctly_after_changes(self) -> None:
        self.registry.register_provider(self.p_healthy)
        self.assertEqual(self.resolver.resolve_provider("AAPL"), self.p_healthy)
        self.registry.unregister_provider("primary-mt5")
        self.assertIsNone(self.resolver.resolve_provider("AAPL"))

    # 3. Router Tests (9 tests)
    def test_router_1_routes_correctly(self) -> None:
        self.registry.register_provider(self.p_healthy)
        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        resp = self.router.route_request(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.provider_id, "primary-mt5")

    def test_router_2_throws_validation_exception_if_no_provider(self) -> None:
        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        with self.assertRaises(ValidationException):
            self.router.route_request(req)

    def test_router_3_failover_triggers_on_unsuccessful_fetch(self) -> None:
        class FailingProvider(IDataProvider):
            @property
            def metadata(self): return DataProviderMetadata("failing", DataSourceType.MT5, ["AAPL"])
            def check_health(self): return ProviderHealthStatus.HEALTHY
            def fetch_data(self, r): return ExternalDataResponse("id", "failing", [], is_success=False)

        self.registry.register_provider(FailingProvider())
        self.registry.register_provider(self.p_degraded) # supports AAPL and is healthy/degraded

        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        resp = self.router.route_request(req)
        # Should fallback to degraded mt5
        self.assertEqual(resp.provider_id, "backup-mt5")

    def test_router_4_failover_triggers_on_exception(self) -> None:
        class CrashingProvider(IDataProvider):
            @property
            def metadata(self): return DataProviderMetadata("crashing", DataSourceType.MT5, ["AAPL"])
            def check_health(self): return ProviderHealthStatus.HEALTHY
            def fetch_data(self, r): raise RuntimeError("Crashed")

        self.registry.register_provider(CrashingProvider())
        self.registry.register_provider(self.p_degraded)

        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        resp = self.router.route_request(req)
        self.assertEqual(resp.provider_id, "backup-mt5")

    def test_router_5_failover_returns_failure_if_alternate_also_fails(self) -> None:
        class CrashingProvider(IDataProvider):
            @property
            def metadata(self): return DataProviderMetadata("crashing", DataSourceType.MT5, ["AAPL"])
            def check_health(self): return ProviderHealthStatus.HEALTHY
            def fetch_data(self, r): raise RuntimeError("Crashed")

        self.registry.register_provider(CrashingProvider())
        # No other healthy provider registered

        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        resp = self.router.route_request(req)
        self.assertFalse(resp.is_success)

    def test_router_6_default_request_id_assigned_if_missing(self) -> None:
        self.registry.register_provider(self.p_healthy)
        req = ExternalDataRequest("AAPL", "H4", datetime.now(), datetime.now())
        resp = self.router.route_request(req)
        self.assertEqual(resp.request_id, "id")

    def test_router_7_health_checks_reported_accurately(self) -> None:
        self.assertEqual(self.p_healthy.check_health(), ProviderHealthStatus.HEALTHY)
        self.assertEqual(self.p_degraded.check_health(), ProviderHealthStatus.DEGRADED)
        self.assertEqual(self.p_unhealthy.check_health(), ProviderHealthStatus.UNHEALTHY)

    def test_router_8_rate_limit_field_exists(self) -> None:
        self.assertEqual(self.p_healthy.metadata.rate_limit_per_minute, 60)

    def test_router_9_additional_info_default_empty(self) -> None:
        self.assertEqual(self.p_healthy.metadata.additional_info, {})
