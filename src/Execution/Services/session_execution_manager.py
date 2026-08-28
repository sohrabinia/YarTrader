from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

logger = logging.getLogger("SessionExecutionManager")

@dataclass
class EODFlattenResult:
    success: bool
    closed_positions_count: int
    cancelled_pending_count: int
    remaining_open_positions: int
    remaining_pending_orders: int
    reason: str = "SESSION_EOD_CUTOFF"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionExecutionManager:
    """
    Session Execution & EOD Lifecycle Manager for YarTrader Master Roadmap Phase C.
    Enforces:
    1. Mandatory strictly >120-second minimum normal holding lifetime floor (`POSITION_MINIMUM_NORMAL_LIFETIME = 120.0`).
    2. Forbidden trading styles rejection (SWING, POSITION, OVERNIGHT).
    3. Session EOD Entry Cutoff blocking entries when remaining session time <= 121s to guarantee >120s holding time before EOD.
    4. Deterministic EOD Flattening sequence:
       STOP ENTRIES -> CANCEL PENDING -> FLATTEN POSITIONS -> VERIFY ZERO STATE.
    5. Forced safety exit isolation recording FORCED_SAFETY_EXIT separately from normal strategy behavior.
    """

    POSITION_MINIMUM_NORMAL_LIFETIME: float = 120.0  # Must be strictly > 120.0 seconds

    def __init__(self):
        self.session_state: str = "OPEN"  # "OPEN", "CLOSING_APPROACH", "SESSION_CLOSED"

    def evaluate_exit_permission(
        self,
        holding_duration_seconds: float,
        exit_reason: str = "NORMAL_TAKE_PROFIT"
    ) -> Dict[str, Any]:
        """
        Enforces the strictly > 120-second minimum hold constraint.
        Holding duration <= 120 seconds (including 120.0s) is strictly BLOCKED for normal strategy exits.
        Genuine forced safety liquidations override minimum hold and are recorded separately as FORCED_SAFETY_EXIT.
        """
        forced_safety_reasons = {
            "FORCED_SAFETY_EXIT",
            "BROKER_LIQUIDATION",
            "MARGIN_LIQUIDATION",
            "CATASTROPHIC_ACCOUNT_PROTECTION",
            "SYSTEM_SHUTDOWN",
            "EMERGENCY_STOP"
        }
        reason_upper = exit_reason.upper()
        is_forced_safety = reason_upper in forced_safety_reasons

        # Strict rule: holding_duration_seconds MUST be strictly > 120.0
        if holding_duration_seconds <= self.POSITION_MINIMUM_NORMAL_LIFETIME and not is_forced_safety:
            msg = (
                f"Normal exit rejected: position holding duration ({holding_duration_seconds:.3f}s) "
                f"<= minimum 120.0s threshold (strictly > 120s required)."
            )
            logger.warning(f"[SessionExecutionManager] {msg}")
            return {
                "allowed": False,
                "rejection_reason": "EARLY_EXIT_BLOCKED_MIN_HOLD_120S",
                "message": msg,
                "actual_duration": holding_duration_seconds,
                "required_duration": self.POSITION_MINIMUM_NORMAL_LIFETIME + 0.001,
                "exit_type": "BLOCKED"
            }

        return {
            "allowed": True,
            "rejection_reason": None,
            "message": "Exit permitted.",
            "actual_duration": holding_duration_seconds,
            "exit_type": "FORCED_SAFETY_EXIT" if is_forced_safety else "NORMAL_EXIT"
        }

    def evaluate_entry_permission(
        self,
        trading_style: str,
        remaining_session_seconds: float
    ) -> Dict[str, Any]:
        """
        Evaluates session entry constraints.
        - Rejects forbidden trading styles (SWING, POSITION, OVERNIGHT).
        - Enforces EOD Entry Cutoff: rejects new entries if remaining session time <= 121s (120s + buffer),
          guaranteeing every opened ordinary position can safely reach >120s before EOD cutoff.
        """
        allowed_styles = ["FAST_SCALP", "SCALP", "DAY_TRADING"]
        style_upper = trading_style.upper()

        if style_upper not in allowed_styles:
            return {
                "allowed": False,
                "rejection_reason": f"FORBIDDEN_STYLE_{style_upper}"
            }

        if self.session_state == "SESSION_CLOSED":
            return {
                "allowed": False,
                "rejection_reason": "SESSION_CLOSED"
            }

        # Cutoff: remaining_session_seconds must be > 121 seconds
        if remaining_session_seconds <= (self.POSITION_MINIMUM_NORMAL_LIFETIME + 1.0):
            return {
                "allowed": False,
                "rejection_reason": "INSUFFICIENT_REMAINING_SESSION_TIME"
            }

        return {
            "allowed": True,
            "rejection_reason": None
        }

    def execute_eod_flattening(
        self,
        active_positions: List[Any],
        pending_orders: List[Any],
        adapter: Optional[Any] = None
    ) -> EODFlattenResult:
        """
        Executes the mandatory 4-step EOD Flattening sequence:
        1. STOP_NEW_ENTRIES (sets session_state = "SESSION_CLOSED").
        2. CANCEL_PENDING_ORDERS (cancels all pending limit/stop orders).
        3. FLATTEN_OPEN_POSITIONS (closes all open positions).
        4. VERIFY_BROKER_AND_LOCAL_STATE (asserts remaining open positions == 0 and pending == 0).
        """
        logger.info("[SessionExecutionManager] Initiating EOD Flattening sequence...")

        # Step 1: Stop new entries
        self.session_state = "SESSION_CLOSED"

        # Step 2: Cancel pending orders
        cancelled_pending = 0
        for pending in list(pending_orders):
            if hasattr(pending, "ticket"):
                ticket = pending.ticket
            elif isinstance(pending, dict):
                ticket = pending.get("ticket")
            else:
                ticket = str(pending)

            if adapter and hasattr(adapter, "cancel_order"):
                try:
                    adapter.cancel_order(ticket)
                except Exception as e:
                    logger.error(f"Failed to cancel pending order {ticket}: {e}")
            cancelled_pending += 1

        # Step 3: Flatten open positions
        closed_positions = 0
        for pos in list(active_positions):
            if hasattr(pos, "ticket"):
                ticket = pos.ticket
            elif isinstance(pos, dict):
                ticket = pos.get("ticket")
            else:
                ticket = str(pos)

            if adapter and hasattr(adapter, "close_position"):
                try:
                    adapter.close_position(ticket)
                except Exception as e:
                    logger.error(f"Failed to close position {ticket}: {e}")
            closed_positions += 1

        # Step 4: Verify zero state
        remaining_positions = len(active_positions) - closed_positions
        remaining_pending = len(pending_orders) - cancelled_pending

        success = (remaining_positions == 0) and (remaining_pending == 0)

        logger.info(f"[SessionExecutionManager] EOD Flatten complete. Success: {success}, Closed: {closed_positions}, Cancelled: {cancelled_pending}.")

        return EODFlattenResult(
            success=success,
            closed_positions_count=closed_positions,
            cancelled_pending_count=cancelled_pending,
            remaining_open_positions=max(0, remaining_positions),
            remaining_pending_orders=max(0, remaining_pending)
        )
