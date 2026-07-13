from abc import ABC, abstractmethod

class IDataStreamProvider(ABC):
    """Interface defining abstractions for real-time streaming market data channels."""
    @abstractmethod
    def connect_stream(self, asset_id: str) -> None:
        """Establishes stream connection for the specified asset."""
        pass

    @abstractmethod
    def disconnect_stream(self, asset_id: str) -> None:
        """Terminates stream connection for the specified asset."""
        pass

    @abstractmethod
    def is_stream_active(self, asset_id: str) -> bool:
        """Checks whether stream connection is active for the specified asset."""
        pass
