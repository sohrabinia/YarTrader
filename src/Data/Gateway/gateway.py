from typing import Dict, List, Optional
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.External.interfaces import IDataProvider
from src.Infrastructure.exceptions import ValidationException


class ProviderRegistry:
    """Manages provider registrations in memory."""
    def __init__(self) -> None:
        self._providers: Dict[str, IDataProvider] = {}

    def register_provider(self, provider: IDataProvider) -> None:
        if not provider or not provider.metadata:
            raise ValidationException("Registry Error: Provider and metadata must not be None.")
        provider_id = provider.metadata.provider_id
        if not provider_id:
            raise ValidationException("Registry Error: Provider ID must not be empty.")
        self._providers[provider_id] = provider

    def unregister_provider(self, provider_id: str) -> None:
        if provider_id in self._providers:
            del self._providers[provider_id]

    def get_provider(self, provider_id: str) -> Optional[IDataProvider]:
        return self._providers.get(provider_id)

    def list_providers(self) -> List[IDataProvider]:
        return list(self._providers.values())


class ProviderResolver:
    """Resolves providers dynamically based on health and capabilities."""
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def resolve_provider(self, symbol: str) -> Optional[IDataProvider]:
        """Resolves the best healthy provider supporting the symbol."""
        providers = self._registry.list_providers()
        # Find healthy providers that support the symbol
        candidates = []
        for p in providers:
            if symbol in p.metadata.supported_symbols:
                status = p.check_health()
                if status == ProviderHealthStatus.HEALTHY:
                    candidates.append((p, 0))  # Highest preference
                elif status == ProviderHealthStatus.DEGRADED:
                    candidates.append((p, 1))  # Lower preference

        # Sort by preference
        candidates.sort(key=lambda x: x[1])
        if candidates:
            return candidates[0][0]
        return None

    def get_alternate_provider(self, symbol: str, exclude_provider_id: str) -> Optional[IDataProvider]:
        """Retrieves an alternate healthy provider for failover."""
        providers = self._registry.list_providers()
        for p in providers:
            if p.metadata.provider_id == exclude_provider_id:
                continue
            if symbol in p.metadata.supported_symbols:
                if p.check_health() in (ProviderHealthStatus.HEALTHY, ProviderHealthStatus.DEGRADED):
                    return p
        return None


class DataRequestRouter:
    """Routes data request payloads to resolved providers, supporting failover."""
    def __init__(self, resolver: ProviderResolver) -> None:
        self._resolver = resolver

    def route_request(self, request: ExternalDataRequest) -> ExternalDataResponse:
        provider = self._resolver.resolve_provider(request.symbol)
        if not provider:
            raise ValidationException(f"Routing Error: No healthy provider available for symbol '{request.symbol}'.")

        try:
            resp = provider.fetch_data(request)
            if resp.is_success:
                return resp
        except Exception:
            pass  # Fallback to alternate on exception

        # Failover behavior: Try alternate provider
        alt_provider = self._resolver.get_alternate_provider(request.symbol, provider.metadata.provider_id)
        if alt_provider:
            try:
                resp = alt_provider.fetch_data(request)
                if resp.is_success:
                    return resp
            except Exception:
                pass

        return ExternalDataResponse(
            request_id=request.request_id or "unknown",
            provider_id=provider.metadata.provider_id,
            raw_data=[],
            is_success=False,
            error_message="Data request failed across primary and secondary providers."
        )


class ExternalDataGateway:
    """Façade gateway coordinating provider registries, resolvers, and routers."""
    def __init__(self) -> None:
        self.registry = ProviderRegistry()
        self.resolver = ProviderResolver(self.registry)
        self.router = DataRequestRouter(self.resolver)

    def fetch(self, request: ExternalDataRequest) -> ExternalDataResponse:
        return self.router.route_request(request)
