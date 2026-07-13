from abc import ABC, abstractmethod
from src.Execution.Models.models import OrderRequest, OrderResponse, ExecutionResult

class IExecutionProvider(ABC):
    """Interface defining operations for mock transaction routing."""
    @abstractmethod
    def execute_order(self, request: OrderRequest) -> ExecutionResult:
        """Executes the order in mock mode and returns an ExecutionResult."""
        pass


class IOrderManager(ABC):
    """Interface defining basic order lifecycle management."""
    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderResponse:
        """Submits an order request cleanly."""
        pass


class IBrokerAdapter(ABC):
    """Interface defining adapter contracts to connect to external brokers or providers in mock mode."""
    @abstractmethod
    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        """Translates and routes order parameters to broker simulator."""
        pass
