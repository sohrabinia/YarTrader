from abc import ABC, abstractmethod
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus, DataProviderMetadata


class IDataProvider(ABC):
    """
    Standard core contract for external intelligence data providers.
    Providers should contain no complex business logic.
    """

    @property
    @abstractmethod
    def metadata(self) -> DataProviderMetadata:
        """Returns metadata about the provider."""
        pass

    @abstractmethod
    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        """Fetches data from the external source."""
        pass

    @abstractmethod
    def check_health(self) -> ProviderHealthStatus:
        """Determines health of the provider."""
        pass
