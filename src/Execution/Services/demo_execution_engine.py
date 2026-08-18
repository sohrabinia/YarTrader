import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("DemoExecutionEngine")


class DemoExecutionEngine:
    """
    Dedicated MT5 DEMO Execution Engine.
    Processes trade decisions and order requests strictly for DEMO account 52961173 on Alpari-MT5-Demo.

    Guarantees:
    - Zero LIVE trading reachability.
    - Explicit DemoExecutionGate enforcement.
    - Real MT5 order_check and order_send execution.
    - Full trade lifecycle evidence output.
    """

    def __init__(self, adapter: Optional[RealMT5BrokerAdapter] = None, demo_mode: bool = True, log_dir: str = "runtime_logs/demo_execution"):
        self.demo_mode = demo_mode
        self.adapter = adapter or RealMT5BrokerAdapter(auto_initialize=True)
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def execute_demo_decision(
        self,
        symbol: str,
        direction: str,
        volume: float = 0.01,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "YarTrader DEMO Execution",
        magic: int = 143056,
        decision_id: str = "DEC-DEMO-001"
    ) -> OrderResponse:
        """
        Translates strategy decision into OrderRequest, passes DemoExecutionGate, and executes on MT5 DEMO.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Construct OrderRequest
        req = OrderRequest(
            Symbol=symbol.upper(),
            OrderType=direction.upper(),
            Volume=float(volume),
            Price=price,
            StopLoss=sl,
            TakeProfit=tp,
            Comment=comment,
            Magic=magic
        )

        evidence = {
            "timestamp": timestamp,
            "decision_id": decision_id,
            "symbol": symbol.upper(),
            "direction": direction.upper(),
            "volume": float(volume),
            "magic": magic,
            "classification": "DEMO_ONLY",
            "live_trading_enabled": False,
            "gate_status": "PENDING",
            "order_check_retcode": None,
            "order_check_comment": None,
            "order_send_retcode": None,
            "order_ticket": None,
            "deal_ticket": None,
            "status": "INITIATED",
            "rejection_reason": None
        }

        # 2. Enforce DemoExecutionGate
        try:
            DemoExecutionGate.verify_demo_execution_eligibility(
                adapter_or_mt5=self.adapter,
                request=req,
                demo_mode_flag=self.demo_mode
            )
            evidence["gate_status"] = "PASSED"
        except ValidationException as ve:
            evidence["gate_status"] = "REJECTED"
            evidence["status"] = "REJECTED"
            evidence["rejection_reason"] = str(ve)
            self._log_evidence(evidence)
            raise

        # 3. Submit to broker adapter
        logger.info(f"[DemoExecutionEngine] Submitting DEMO order request for {symbol} {direction} {volume} lot.")
        response = self.adapter.send_order_to_broker(req)

        evidence["status"] = response.Status
        evidence["order_send_retcode"] = response.Retcode
        evidence["order_ticket"] = response.OrderId
        evidence["deal_ticket"] = response.DealTicket
        evidence["rejection_reason"] = response.Comment if response.Status == "Failed" else None

        self._log_evidence(evidence)

        logger.info(
            f"[DemoExecutionEngine] DEMO execution result: Status={response.Status}, "
            f"OrderId={response.OrderId}, DealTicket={response.DealTicket}, Comment={response.Comment}"
        )

        return response

    def _log_evidence(self, evidence: Dict[str, Any]) -> None:
        """Writes execution telemetry safely to disk without exposing credentials."""
        try:
            filename = f"demo_order_{int(datetime.now(timezone.utc).timestamp())}_{evidence['symbol']}.json"
            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(evidence, f, indent=2)
        except Exception as e:
            logger.warning(f"[DemoExecutionEngine] Failed to write evidence log: {e}")
