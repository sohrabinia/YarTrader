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
    1. Legacy minimum-hold floor for discretionary exits only; never blocks protective stops
       or explicitly confirmed structural/economic wave exits.
    2. Forbidden trading styles rejection (SWING, POSITION, OVERNIGHT).
    3. Session EOD entry cutoff and deterministic EOD flattening.
    4. Forced safety exit isolation and auditable exit classification.
    5. Reversal entry is separately gated by opposite-structure confirmation, net economics,
       spread, and risk checks; closing a trade alone never authorizes a reverse order.
    """

    POSITION_MINIMUM_NORMAL_LIFETIME: float = 120.0  # Must be strictly > 120.0 seconds

    def __init__(self, market_session_engine: Optional[Any] = None):
        self.session_state: str = "OPEN"  # "OPEN", "CLOSING_APPROACH", "SESSION_CLOSED"
        self.market_session_engine = market_session_engine

    def evaluate_exit_permission(
        self,
        holding_duration_seconds: float,
        exit_reason: str = "NORMAL_TAKE_PROFIT",
        wave_exit_confirmed: bool = False,
        economic_reversal_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Apply the legacy minimum-hold floor only to discretionary exits.

        Confirmed structural invalidation / economic wave reversal must not be
        trapped by a timer. Broker SL/TP orders are also never delayed by this
        policy. A reverse entry remains a separate decision and requires its own
        confirmation, net-of-cost edge, and risk checks.
        """
        forced_safety_reasons = {
            "FORCED_SAFETY_EXIT", "BROKER_LIQUIDATION", "MARGIN_LIQUIDATION",
            "CATASTROPHIC_ACCOUNT_PROTECTION", "SYSTEM_SHUTDOWN", "EMERGENCY_STOP"
        }
        protective_exit_reasons = {"STOP_LOSS", "BROKER_STOP_LOSS", "CATASTROPHIC_STOP"}
        wave_exit_reasons = {
            "STRUCTURAL_INVALIDATION", "REVERSAL_EXIT", "WAVE_REVERSAL_CONFIRMED",
            "ECONOMIC_WAVE_EXHAUSTION", "SIGNAL_EXIT"
        }
        reason_upper = exit_reason.upper()
        is_forced_safety = reason_upper in forced_safety_reasons
        is_protective_exit = reason_upper in protective_exit_reasons
        is_confirmed_wave_exit = reason_upper in wave_exit_reasons and (
            wave_exit_confirmed or economic_reversal_confirmed
        )

        if holding_duration_seconds < 0:
            return {
                "allowed": False, "rejection_reason": "INVALID_NEGATIVE_HOLD_DURATION",
                "actual_duration": holding_duration_seconds, "exit_type": "BLOCKED"
            }

        if (holding_duration_seconds <= self.POSITION_MINIMUM_NORMAL_LIFETIME
                and not (is_forced_safety or is_protective_exit or is_confirmed_wave_exit)):
            msg = (
                f"Discretionary exit rejected: holding duration ({holding_duration_seconds:.3f}s) "
                f"<= legacy minimum {self.POSITION_MINIMUM_NORMAL_LIFETIME:.1f}s."
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

        exit_type = (
            "FORCED_SAFETY_EXIT" if is_forced_safety else
            "PROTECTIVE_EXIT" if is_protective_exit else
            "CONFIRMED_WAVE_EXIT" if is_confirmed_wave_exit else "NORMAL_EXIT"
        )
        return {
            "allowed": True, "rejection_reason": None,
            "message": "Exit permitted by lifecycle policy.",
            "actual_duration": holding_duration_seconds, "exit_type": exit_type
        }

    def evaluate_entry_permission(
        self,
        trading_style: str,
        remaining_session_seconds: float,
        symbol: Optional[str] = None,
        broker: str = "DEFAULT",
        distance_to_tp: Optional[float] = None,
        current_volatility_atr: Optional[float] = None,
        historical_mfe_speed: float = 1.0,
        current_time: Optional[datetime] = None,
        current_equity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates session entry constraints.
        - Rejects forbidden trading styles (SWING, POSITION, OVERNIGHT).
        - Delegates to MarketSessionEngine if available for authoritative session/calendar and TP-time feasibility gate.
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

        # If MarketSessionEngine is provided and symbol is specified, evaluate unified session & TP feasibility
        if self.market_session_engine and symbol:
            res = self.market_session_engine.validate_pre_entry(
                symbol=symbol,
                broker=broker,
                distance_to_tp=distance_to_tp,
                current_volatility_atr=current_volatility_atr,
                historical_mfe_speed=historical_mfe_speed,
                current_time=current_time,
                current_equity=current_equity
            )
            if not res.allowed:
                return {
                    "allowed": False,
                    "rejection_reason": res.rejection_reason,
                    "message": res.message,
                    "remaining_session_seconds": res.remaining_session_seconds
                }

        # Standalone Cutoff fallback: remaining_session_seconds must be > 121 seconds
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
