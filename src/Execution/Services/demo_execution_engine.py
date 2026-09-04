import os
import math
import json
import time
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

    def __init__(self, adapter: Optional[RealMT5BrokerAdapter] = None, demo_mode: bool = True, log_dir: Optional[str] = None):
        self.demo_mode = demo_mode
        self.adapter = adapter or RealMT5BrokerAdapter(auto_initialize=True)

        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()

        if not log_dir or not os.isabs(log_dir):
            sub_dir = log_dir if log_dir else "demo_execution"
            sub_folder = os.path.basename(sub_dir) if ("/" in sub_dir or "\\" in sub_dir) else sub_dir
            self.log_dir = os.path.join(storage_mgr.get_log_dir(), sub_folder)
        else:
            self.log_dir = log_dir

        os.makedirs(self.log_dir, exist_ok=True)

    def execute_demo_decision(
        self,
        symbol: str,
        direction: str,
        volume: float,
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

        # 3. Submit to broker adapter with pre-check and retcode classification
        logger.info(f"[DemoExecutionEngine] Submitting DEMO order request for {symbol} {direction} {volume} lot.")
        try:
            response = self.adapter.send_order_to_broker(req)

            evidence["status"] = response.Status
            evidence["order_send_retcode"] = response.Retcode
            evidence["order_ticket"] = response.OrderId
            evidence["deal_ticket"] = response.DealTicket
            evidence["rejection_reason"] = response.Comment if response.Status == "Failed" else None

            # Retcode classification mapping
            if response.Retcode == 10018:
                evidence["retcode_classification"] = "MARKET_CLOSED"
                evidence["rejection_reason"] = "Market is closed (10018 MARKET_CLOSED). Recovering safely."
            elif response.Retcode == 10009:
                evidence["retcode_classification"] = "SUCCESS"
            elif response.Retcode == 10013:
                evidence["retcode_classification"] = "INVALID_STOPS"
            elif response.Retcode == 10014:
                evidence["retcode_classification"] = "INVALID_VOLUME"
            elif response.Retcode == 10019:
                evidence["retcode_classification"] = "INSUFFICIENT_MARGIN"
            elif response.Retcode == 10021:
                evidence["retcode_classification"] = "NO_CONNECTION"
            else:
                evidence["retcode_classification"] = f"RETCODE_{response.Retcode}"

            self._log_evidence(evidence)

            logger.info(
                f"[DemoExecutionEngine] DEMO execution result: Status={response.Status}, "
                f"Retcode={response.Retcode} ({evidence.get('retcode_classification')}), "
                f"OrderId={response.OrderId}, DealTicket={response.DealTicket}, Comment={response.Comment}"
            )

            return response
        except ValidationException as ve:
            evidence["status"] = "REJECTED"
            evidence["rejection_reason"] = str(ve)
            evidence["retcode_classification"] = "FAIL_CLOSED"
            self._log_evidence(evidence)
            raise

    def get_active_positions(self, symbol: Optional[str] = None) -> list:
        """Queries active broker positions for symbol."""
        if hasattr(self.adapter, "get_positions"):
            res = self.adapter.get_positions(symbol=symbol)
            return res if res is not None else []
        return []

    def close_position(
        self,
        symbol: str,
        position_ticket: int,
        volume: Optional[float] = None,
        comment: str = "YarTrader Close",
        open_timestamp: Optional[float] = None,
        is_eod_flatten: bool = False
    ) -> OrderResponse:
        """
        Submits CLOSE request for position ticket using authoritative broker-reported volume.
        Enforces 120-second minimum holding period unless overridden by EOD flattening.
        Fails closed with zero volume fallback if position volume is missing or invalid.
        """
        # 120-second Minimum Hold Invariant Guard
        if open_timestamp is not None and not is_eod_flatten:
            elapsed_sec = time.time() - open_timestamp
            if elapsed_sec < 120.0:
                logger.warning(f"[DemoExecutionEngine] Close blocked for ticket {position_ticket}: Hold time ({int(elapsed_sec)}s) < 120s minimum hold constraint.")
                return OrderResponse(
                    OrderId="0",
                    Symbol=symbol.upper(),
                    Status="Failed",
                    SubmittedAt=datetime.now(timezone.utc),
                    Retcode=10013,
                    Comment=f"Minimum holding time violation: {int(elapsed_sec)}s < 120s minimum constraint.",
                    RawResponse={"reason": "MINIMUM_HOLD_VIOLATION"}
                )

        # Retrieve authoritative position volume strictly from broker position lookup if volume not explicitly passed
        close_vol = volume
        ticket_str = str(position_ticket)

        if close_vol is None:
            active_positions = self.get_active_positions(symbol=symbol)
            target_pos = next((p for p in active_positions if str(p.get("ticket", "")) == ticket_str), None)
            if target_pos and "volume" in target_pos:
                close_vol = target_pos.get("volume")

        # Validate close volume strictly: MUST be finite positive float. ZERO FALLBACK TO 0.01!
        if close_vol is None or isinstance(close_vol, bool):
            logger.error(f"[DemoExecutionEngine] Close failed: Authoritative volume unavailable for ticket {position_ticket}.")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10014,
                Comment=f"Close failed: Authoritative position volume unavailable for ticket {position_ticket}.",
                RawResponse={"reason": "MISSING_POSITION_VOLUME"}
            )

        try:
            close_vol_f = float(close_vol)
            if not math.isfinite(close_vol_f) or close_vol_f <= 0:
                raise ValueError(f"Non-positive or non-finite volume: {close_vol_f}")
        except (ValueError, TypeError) as ve:
            logger.error(f"[DemoExecutionEngine] Close failed: Invalid position volume for ticket {position_ticket}: {ve}")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10014,
                Comment=f"Close failed: Authoritative position volume is invalid ({close_vol}) for ticket {position_ticket}.",
                RawResponse={"reason": "INVALID_CLOSE_VOLUME"}
            )

        req = OrderRequest(
            Symbol=symbol.upper(),
            OrderType="CLOSE",
            Volume=close_vol_f,
            PositionTicket=str(position_ticket),
            Comment=comment
        )

        response = self.adapter.send_order_to_broker(req)

        # Confirm closure from broker position list
        remaining = self.get_active_positions(symbol=symbol)
        still_open = any(str(p.get("ticket", "")) == ticket_str for p in remaining)

        if still_open:
            logger.warning(
                f"[DemoExecutionEngine] Position close requested for ticket {position_ticket}, "
                f"but position remains open on broker. State is CLOSE_PENDING/FAILED."
            )
            return OrderResponse(
                OrderId=response.OrderId,
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=response.SubmittedAt,
                Retcode=response.Retcode,
                Comment=f"Position close requested but broker confirmation pending/failed. Position {position_ticket} still active.",
                DealTicket=response.DealTicket,
                Price=response.Price,
                Volume=response.Volume,
                RawResponse=response.RawResponse
            )

        logger.info(f"[DemoExecutionEngine] Position {position_ticket} close CONFIRMED on broker.")
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
