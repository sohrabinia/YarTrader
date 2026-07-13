import uuid
from datetime import datetime
from src.Execution.Interfaces.interfaces import IBrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse

class MT5AdapterPlaceholder(IBrokerAdapter):
    """
    Placeholder adapter for MetaTrader 5 brokerage simulator.
    Strictly contains no platform-specific client connection logic or live orders.
    """
    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        # Mock-submit order and return response
        order_id = f"MT5-{uuid.uuid4().hex[:8]}"
        return OrderResponse(
            OrderId=order_id,
            Symbol=request.Symbol,
            Status="MockPlaced",
            SubmittedAt=datetime.now()
        )


class GenericBrokerAdapterPlaceholder(IBrokerAdapter):
    """
    Placeholder adapter for general REST/FIX standard broker gateways.
    Strictly contains no live network connections.
    """
    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        order_id = f"GEN-{uuid.uuid4().hex[:8]}"
        return OrderResponse(
            OrderId=order_id,
            Symbol=request.Symbol,
            Status="MockPlaced",
            SubmittedAt=datetime.now()
        )
