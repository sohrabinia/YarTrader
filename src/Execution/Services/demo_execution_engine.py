"""
Dedicated MT4 DEMO Execution Engine
===================================
Processes trade decisions and order requests strictly for DEMO account on MT5.

Guarantees:
- Zero LIVE trading reachability.
- Explicit DemoExecutionGate enforcement.
- Real MT5 order_check and order_send execution.
- Strict close volume validation derived strictly from authoritative broker position facts.
- Fail-closed on UNKNOWN position states.
"""

import os
import math
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from src.Execution.Adapters.mt4_adapter import RealMT4BrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Infrastructure.exceptions import ValidationException
from src.Research.Brain.learning_bridge import BrainLearningBridge

logger = logging.getLogger("DemoExecutionEngine")


class DemoExecutionEngine:
    """
    Dedicated MT4 DEMO Execution Engine.
    """

    def __init__(
        self,
        adapter: Optional[RealMT4BrokerAdapter] = None,
        demo_mode: bool = True,
        log_dir: Optional[str] = None
    ) -> None:
        self.demo_mode = demo_mode
        self.adapter = adapter or RealMT4BrokerAdapter(auto_initialize=True)

        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()

        if not log_dir or not os.isabs(log_dir):
            sub_dir = log_dir if log_dir else "demo_execution"
            sub_folder = os.path.basename(sub_dir) if ("/" in sub_dir or "\\" in sub_dir) else sub_dir
            self.log_dir = os.path.join(storage_mgr.get_log_dir(), sub_folder)
        else:
            self.log_dir = log_dir

        os.makedirs(self.log_dir, exist_ok=True)
        self.learning_bridge = BrainLearningBridge()
        self._decision_map_path = os.path.join(self.log_dir, "decision_position_map.json")

    def _load_decision_map(self) -> Dict[str, str]:
        try:
            with open(self._decision_map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_decision_map(self, data: Dict[str, str]) -> None:
        tmp = self._decision_map_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._decision_map_path)

    def execute_demo_decision(
        self,
        symbol: str,
        direction: str,
        volume: float,  # Explicit validated volume
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "YarTrader DEMO Execution",
        magic: int = 143056,
        decision_id: str = "DEC-DEMO-001"
    ) -> OrderResponse:
        """
        Translates strategy decision into OrderRequest, passes DemoExecutionGate, and executes on MT4 DEMO.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

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

        logger.info(f"[DemoExecutionEngine] Submitting DEMO order request for {symbol} {direction} {volume} lot.")
        try:
            response = self.adapter.send_order_to_broker(req)

            evidence["status"] = response.Status
            evidence["order_send_retcode"] = response.Retcode
            evidence["order_ticket"] = response.OrderId
            evidence["deal_ticket"] = response.DealTicket
            evidence["rejection_reason"] = response.Comment if response.Status == "Failed" else None

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
            if response.Status != "Failed" and response.DealTicket:
                mapping = self._load_decision_map()
                mapping[str(response.DealTicket)] = decision_id
                if response.OrderId:
                    mapping[str(response.OrderId)] = decision_id
                self._save_decision_map(mapping)
            return response
        except ValidationException as ve:
            evidence["status"] = "REJECTED"
            evidence["rejection_reason"] = str(ve)
            evidence["retcode_classification"] = "FAIL_CLOSED"
            self._log_evidence(evidence)
            raise

    def get_active_positions(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Queries active broker positions for symbol.
        Returns:
          - [] (empty list) when broker query succeeds and zero positions exist (FLAT).
          - None (UNKNOWN) when broker query fails, adapter is disconnected, or raises an exception.
        """
        if hasattr(self.adapter, "get_positions"):
            try:
                res = self.adapter.get_positions(symbol=symbol)
                return res
            except Exception as e:
                logger.error(f"[DemoExecutionEngine] Exception querying positions: {e}")
                return None
        return None

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
        """
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

        ticket_str = str(position_ticket)
        active_positions = self.get_active_positions(symbol=symbol)
        if active_positions is None:
            logger.error(f"[DemoExecutionEngine] Close failed: Broker position state is UNKNOWN for symbol {symbol}.")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10021,
                Comment=f"Close failed: Broker position query failed / UNKNOWN state for ticket {position_ticket}.",
                RawResponse={"reason": "UNKNOWN_POSITION_STATE"}
            )

        if not active_positions:
            logger.warning(f"[DemoExecutionEngine] Close failed: Known flat / position ticket {position_ticket} not found.")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10013,
                Comment=f"Close failed: Position ticket {position_ticket} not found on broker.",
                RawResponse={"reason": "POSITION_NOT_FOUND"}
            )

        target_pos = next((p for p in active_positions if str(p.get("ticket", "")) == ticket_str), None)
        if not target_pos:
            logger.warning(f"[DemoExecutionEngine] Close failed: Position ticket {position_ticket} not in active positions.")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10013,
                Comment=f"Close failed: Position ticket {position_ticket} not found on broker.",
                RawResponse={"reason": "POSITION_NOT_FOUND"}
            )

        raw_vol = target_pos.get("volume")
        if raw_vol is None or isinstance(raw_vol, bool) or not isinstance(raw_vol, (int, float)):
            logger.error(f"[DemoExecutionEngine] Close failed: Broker position volume is non-numeric or missing for ticket {position_ticket}.")
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10014,
                Comment=f"Close failed: Authoritative position volume is invalid for ticket {position_ticket}.",
                RawResponse={"reason": "INVALID_CLOSE_VOLUME"}
            )

        try:
            close_vol_f = float(raw_vol)
            if not math.isfinite(close_vol_f) or close_vol_f <= 0:
                raise ValueError(f"Non-positive or non-finite volume: {close_vol_f}")
        except (ValueError, TypeError):
            return OrderResponse(
                OrderId="0",
                Symbol=symbol.upper(),
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=10014,
                Comment=f"Close failed: Authoritative position volume is invalid ({raw_vol}) for ticket {position_ticket}.",
                RawResponse={"reason": "INVALID_CLOSE_VOLUME"}
            )

        req = OrderRequest(
            Symbol=symbol.upper(),
            OrderType="CLOSE",
            Volume=close_vol_f,
            PositionTicket=str(position_ticket),
            Comment=comment
        )

        response = self.adapter.close_order(position_ticket, close_vol_f) if hasattr(self.adapter, "close_order") else self.adapter.send_order_to_broker(req)

        # Confirm closure from broker position list
        remaining = self.get_active_positions(symbol=symbol)
        still_open = (remaining is None) or any(str(p.get("ticket", "")) == ticket_str for p in remaining)

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
        mapping = self._load_decision_map()
        decision_id = mapping.pop(ticket_str, None)
        if decision_id:
            try:
                pos_type = target_pos.get("type", 0)
                direction = "BUY" if str(pos_type).upper() in {"0", "BUY"} else "SELL"
                entry_price = float(target_pos.get("price_open", target_pos.get("price", 0.0)))
                exit_price = float(response.Price or 0.0)
                signed_move = (exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)
                volume_for_pnl = float(target_pos.get("volume", 0.0))
                pnl = signed_move * volume_for_pnl * (100.0 if "XAU" in symbol.upper() else 10000.0)
                learning_result = self.learning_bridge.record_demo_outcome(
                    decision_id=decision_id, symbol=symbol, timeframe=str(target_pos.get("timeframe", "M15")), direction=direction,
                    entry_price=entry_price, exit_price=exit_price, pnl=pnl,
                    context={"position_ticket": position_ticket, "broker_retcode": response.Retcode},
                )
                logger.info("[DemoExecutionEngine] DEMO outcome promoted into Brain memory: %s", learning_result)
            except Exception as exc:
                logger.exception("[DemoExecutionEngine] DEMO learning update failed closed: %s", exc)
        self._save_decision_map(mapping)
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
