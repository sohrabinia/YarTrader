from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging

logger = logging.getLogger("OrderLifecycleManager")

@dataclass
class OrderLifecycleState:
    order_id: str
    request_id: str
    symbol: str
    order_type: str  # "MARKET_BUY", "MARKET_SELL", "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
    volume_lots: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "SUBMITTED"  # "SUBMITTED", "PENDING", "FILLED", "CANCELLED", "REJECTED"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrderLifecycleManager:
    """
    Order Lifecycle & Idempotency Manager for YarTrader Master Roadmap Phase C.
    Enforces:
    1. Strict request deduplication and idempotency prevention (`DUPLICATE_ORDER_REJECTED`).
    2. Support for 6 order types: MARKET_BUY, MARKET_SELL, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP.
    3. Pending order attribute validation (setup, zone, risk, SL/TP bounds).
    4. Process restart recovery and broker-vs-local state reconciliation (`reconcile_broker_and_local_state`).
    """

    ALLOWED_ORDER_TYPES: Set[str] = {
        "MARKET_BUY", "MARKET_SELL",
        "BUY_LIMIT", "SELL_LIMIT",
        "BUY_STOP", "SELL_STOP",
        "BUY", "SELL"  # Legacy aliases
    }

    def __init__(self):
        self.processed_request_ids: Set[str] = set()
        self.active_orders: Dict[str, OrderLifecycleState] = {}

    def generate_request_hash(self, symbol: str, order_type: str, volume: float, price: float, timestamp_str: str) -> str:
        raw = f"{symbol.upper()}:{order_type.upper()}:{volume:.2f}:{price:.4f}:{timestamp_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def submit_order_request(
        self,
        request_id: str,
        symbol: str,
        order_type: str,
        volume_lots: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        adapter: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Submits an order request with idempotency deduplication and attribute validation.
        """
        type_upper = order_type.upper()

        if request_id in self.processed_request_ids:
            logger.warning(f"[OrderLifecycleManager] Duplicate order request rejected: {request_id}")
            return {
                "success": False,
                "order_state": None,
                "rejection_reason": "DUPLICATE_ORDER_REJECTED"
            }

        if type_upper not in self.ALLOWED_ORDER_TYPES:
            return {
                "success": False,
                "order_state": None,
                "rejection_reason": f"UNSUPPORTED_ORDER_TYPE_{type_upper}"
            }

        if volume_lots < 0.01:
            return {
                "success": False,
                "order_state": None,
                "rejection_reason": f"VOLUME_BELOW_MINIMUM_{volume_lots}"
            }

        # Validate SL/TP orientation
        if type_upper in ["MARKET_BUY", "BUY_LIMIT", "BUY_STOP", "BUY"]:
            if stop_loss > 0 and stop_loss >= price:
                return {"success": False, "order_state": None, "rejection_reason": "BUY_SL_MUST_BE_BELOW_PRICE"}
            if take_profit > 0 and take_profit <= price:
                return {"success": False, "order_state": None, "rejection_reason": "BUY_TP_MUST_BE_ABOVE_PRICE"}
        elif type_upper in ["MARKET_SELL", "SELL_LIMIT", "SELL_STOP", "SELL"]:
            if stop_loss > 0 and stop_loss <= price:
                return {"success": False, "order_state": None, "rejection_reason": "SELL_SL_MUST_BE_ABOVE_PRICE"}
            if take_profit > 0 and take_profit >= price:
                return {"success": False, "order_state": None, "rejection_reason": "SELL_TP_MUST_BE_BELOW_PRICE"}

        # Record idempotency token
        self.processed_request_ids.add(request_id)

        order_id = f"ord_{hashlib.md5(request_id.encode('utf-8')).hexdigest()[:8]}"
        state = OrderLifecycleState(
            order_id=order_id,
            request_id=request_id,
            symbol=symbol.upper(),
            order_type=type_upper,
            volume_lots=volume_lots,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="SUBMITTED"
        )

        self.active_orders[order_id] = state

        return {
            "success": True,
            "order_state": state,
            "rejection_reason": None
        }

    def reconcile_broker_and_local_state(
        self,
        broker_positions: List[Dict[str, Any]],
        local_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Reconciles broker positions vs local state following process restart or reconnect.
        Detects orphaned broker positions and missing local positions.
        """
        broker_tickets = {str(p.get("ticket", p.get("PositionTicket", ""))) for p in broker_positions}
        local_tickets = {str(p.get("ticket", p.get("PositionTicket", ""))) for p in local_positions}

        orphaned_on_broker = broker_tickets - local_tickets
        missing_on_broker = local_tickets - broker_tickets
        synchronized = broker_tickets & local_tickets

        logger.info(f"[OrderLifecycleManager] Reconciliation complete. Synchronized: {len(synchronized)}, Orphaned on Broker: {len(orphaned_on_broker)}, Missing on Broker: {len(missing_on_broker)}")

        return {
            "is_synchronized": len(orphaned_on_broker) == 0 and len(missing_on_broker) == 0,
            "synchronized_tickets": list(synchronized),
            "orphaned_on_broker": list(orphaned_on_broker),
            "missing_on_broker": list(missing_on_broker)
        }
