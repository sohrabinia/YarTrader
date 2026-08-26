"""
YarTrader Autonomous Multi-Scale Position Intelligence & Session Lifecycle Management Module
Manages individual position lifecycles using multi-scale fractal perception, movement states, thesis tracking,
120-second minimum normal exit lifetime enforcement, session-aware state machine (NORMAL_SESSION, SESSION_APPROACHING_CUTOFF, ENTRY_RESTRICTED, POSITION_UNWIND, SESSION_FLAT), zero overnight open positions guarantee, adaptive structural invalidation exits, risk-budget sizing, re-entry eligibility, and symmetric direction transitions under strict read-only execution constraints (LIVE_TRADING_ENABLED=False).
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("YarTrader.FractalPositionIntelligence")

POSITION_MINIMUM_NORMAL_LIFETIME_SECONDS = 120  # 120-second normal intelligent exit floor

VALID_LIFECYCLE_STATES = [
    "FLAT",
    "ENTRY_CANDIDATE",
    "ENTERED",
    "ACTIVE",
    "HEALTHY_PULLBACK",
    "DANGEROUS_PULLBACK",
    "CONTINUATION",
    "HEALTHY_EXPANSION",
    "EXHAUSTION_WARNING",
    "THESIS_WEAKENING",
    "INVALIDATED",
    "EXITED",
    "REASSESSMENT",
    "REENTRY_CANDIDATE",
    "REENTRY",
    "OPPOSITE_ENTRY_CANDIDATE",
    "SESSION_UNWIND_EXIT"
]

VALID_SESSION_STATES = [
    "NORMAL_SESSION",
    "SESSION_APPROACHING_CUTOFF",
    "ENTRY_RESTRICTED",
    "POSITION_UNWIND",
    "SESSION_FLAT"
]


def _get_price(candle: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Helper to safely fetch price fields supporting both lowercase and uppercase keys."""
    val = candle.get(key, candle.get(key.capitalize(), default))
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_iso_timestamp(ts_val: Any) -> Optional[datetime]:
    """
    Helper to parse timestamp into UTC datetime.
    Supports ISO-8601 strings, numeric Epoch timestamps (seconds or milliseconds), and datetime objects.
    """
    if ts_val is None:
        return None
    if isinstance(ts_val, datetime):
        return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc)

    ts_str = str(ts_val).strip()
    if not ts_str:
        return None

    # Check for numeric Epoch timestamp (seconds or milliseconds)
    try:
        val_float = float(ts_str)
        if val_float > 1e11:  # Milliseconds
            val_float = val_float / 1000.0
        if val_float > 0:
            return datetime.fromtimestamp(val_float, tz=timezone.utc)
    except (ValueError, OverflowError):
        pass

    # Fallback to ISO string parsing
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


class FractalPositionThesis:
    """
    Represents an independent, stateful position thesis with multi-scale structural attributes.
    """
    def __init__(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        entry_time: Any,
        entry_scale: str = "H1",
        parent_scale: str = "H4",
        macro_scale: str = "D1",
        risk_budget_usd: float = 100.0,
        structural_invalidation_price: float = 0.0,
        target_price: float = 0.0,
        parent_structure_id: Optional[str] = None
    ):
        self.position_id = f"POS_{symbol.upper()}_{uuid.uuid4().hex[:8]}"
        self.symbol = symbol.upper()
        self.direction = direction.upper()  # 'BUY' or 'SELL'
        self.entry_price = float(entry_price)
        self.entry_time = str(entry_time)
        self.entry_dt = parse_iso_timestamp(entry_time) or datetime.now(timezone.utc)
        self.entry_scale = str(entry_scale)
        self.parent_scale = str(parent_scale)
        self.macro_scale = str(macro_scale)
        self.risk_budget_usd = float(risk_budget_usd)

        # Directions
        self.macro_direction = "BULLISH" if self.direction == "BUY" else "BEARISH"
        self.local_direction = self.direction
        self.trade_direction = self.direction

        # Structural stops and targets (Derived strictly from multi-scale structure)
        if structural_invalidation_price <= 0.0:
            structural_invalidation_price = self.entry_price - 20.0 if self.direction == "BUY" else self.entry_price + 20.0
        if target_price <= 0.0:
            target_price = self.entry_price + 30.0 if self.direction == "BUY" else self.entry_price - 30.0

        self.structural_invalidation_price = float(structural_invalidation_price)
        self.initial_invalidation_price = float(structural_invalidation_price)
        self.target_price = float(target_price)
        self.parent_structure_id = parent_structure_id or f"BASE_{self.parent_scale}_{uuid.uuid4().hex[:6]}"

        # Lifecycle & State Machine
        self.current_state = "ENTERED"
        self.thesis_status = "VALID"        # VALID, WEAKENING, INVALIDATED
        self.movement_state = "FORMATION"   # FORMATION, EXPANSION, PULLBACK, CONTINUATION, EXHAUSTION, REVERSAL
        self.structural_regime = "TRENDING"
        self.active_fractal_scale = self.entry_scale

        # Excursion & Performance Tracking
        self.current_mfe = 0.0
        self.current_mae = 0.0
        self.peak_price = self.entry_price
        self.trough_price = self.entry_price

        self.exit_price = 0.0
        self.exit_time: Optional[str] = None
        self.exit_reason: Optional[str] = None
        self.pnl_usd = 0.0

        # Eligibility & Transitions
        self.reentry_eligible = False
        self.direction_transition_eligible = False
        self.state_history: List[Dict[str, Any]] = []

        # Risk-aware position sizing in Oz based strictly on structural loss distance
        self.risk_distance = max(0.5, abs(self.entry_price - self.structural_invalidation_price))
        self.position_size_oz = round(self.risk_budget_usd / self.risk_distance, 4)

        self.record_state_change("ENTERED", "Position initialized with structural thesis")

    def record_state_change(self, new_state: str, reason: str):
        """Records state machine transitions deterministically."""
        if new_state in VALID_LIFECYCLE_STATES:
            self.current_state = new_state
        self.state_history.append({
            "state": self.current_state,
            "thesis_status": self.thesis_status,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_age_seconds(self, current_time_val: Any) -> float:
        """Calculates age in seconds relative to current_time_val."""
        c_dt = parse_iso_timestamp(current_time_val)
        if not c_dt or not self.entry_dt:
            return 0.0
        return max(0.0, (c_dt - self.entry_dt).total_seconds())

    def update_excursion(self, current_high: float, current_low: float, current_close: float):
        """Updates MFE, MAE, peak, and trough prices."""
        self.peak_price = max(self.peak_price, current_high)
        self.trough_price = min(self.trough_price, current_low)

        if self.direction == "BUY":
            favorable = max(0.0, current_high - self.entry_price)
            adverse = max(0.0, self.entry_price - current_low)
        else:
            favorable = max(0.0, self.entry_price - current_low)
            adverse = max(0.0, current_high - self.entry_price)

        self.current_mfe = max(self.current_mfe, favorable)
        self.current_mae = max(self.current_mae, adverse)

    def update_structural_trailing_stop(self, new_structural_invalidation: float):
        """
        Updates trailing invalidation level based strictly on structural base/pivot progression.
        Never moves stop backward.
        """
        if self.direction == "BUY":
            if new_structural_invalidation > self.structural_invalidation_price:
                self.structural_invalidation_price = float(new_structural_invalidation)
                self.risk_distance = max(0.5, abs(self.entry_price - self.structural_invalidation_price))
        else:
            if new_structural_invalidation < self.structural_invalidation_price:
                self.structural_invalidation_price = float(new_structural_invalidation)
                self.risk_distance = max(0.5, abs(self.entry_price - self.structural_invalidation_price))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": round(self.entry_price, 2),
            "entry_time": self.entry_time,
            "entry_scale": self.entry_scale,
            "parent_scale": self.parent_scale,
            "macro_scale": self.macro_scale,
            "risk_budget_usd": self.risk_budget_usd,
            "structural_invalidation_price": round(self.structural_invalidation_price, 2),
            "initial_invalidation_price": round(self.initial_invalidation_price, 2),
            "target_price": round(self.target_price, 2),
            "risk_distance": round(self.risk_distance, 2),
            "position_size_oz": self.position_size_oz,
            "current_state": self.current_state,
            "thesis_status": self.thesis_status,
            "movement_state": self.movement_state,
            "macro_direction": self.macro_direction,
            "local_direction": self.local_direction,
            "current_mfe": round(self.current_mfe, 2),
            "current_mae": round(self.current_mae, 2),
            "peak_price": round(self.peak_price, 2),
            "trough_price": round(self.trough_price, 2),
            "exit_price": round(self.exit_price, 2) if self.exit_price > 0 else 0.0,
            "exit_time": self.exit_time,
            "exit_reason": self.exit_reason,
            "pnl_usd": round(self.pnl_usd, 2),
            "reentry_eligible": self.reentry_eligible,
            "direction_transition_eligible": self.direction_transition_eligible
        }


class FractalPositionLifecycleManager:
    """
    Manages individual position lifecycles, structural thesis, exits, re-entries, session-aware state management,
    and 120-second normal intelligent exit lifetime enforcement.
    """
    def __init__(self, symbol: str = "XAUUSD", default_risk_budget_usd: float = 100.0, session_cutoff_hour: int = 21, session_cutoff_minute: int = 45):
        self.symbol = symbol.upper()
        self.default_risk_budget_usd = default_risk_budget_usd
        self.session_cutoff_hour = session_cutoff_hour
        self.session_cutoff_minute = session_cutoff_minute
        self.session_state = "NORMAL_SESSION"

        self.active_positions: List[FractalPositionThesis] = []
        self.history_positions: List[FractalPositionThesis] = []
        self.reentry_candidates: List[Dict[str, Any]] = []
        self.direction_transition_candidates: List[Dict[str, Any]] = []

    def evaluate_session_state(self, current_time_val: Any) -> str:
        """
        Evaluates session state deterministically based on hour/minute:
        NORMAL_SESSION -> SESSION_APPROACHING_CUTOFF -> ENTRY_RESTRICTED -> POSITION_UNWIND -> SESSION_FLAT
        """
        dt = parse_iso_timestamp(current_time_val)
        if not dt:
            self.session_state = "NORMAL_SESSION"
            return self.session_state

        hour, minute = dt.hour, dt.minute

        # Cutoff occurs at session_cutoff_hour:session_cutoff_minute (e.g. 21:45 UTC)
        if hour > self.session_cutoff_hour or (hour == self.session_cutoff_hour and minute >= self.session_cutoff_minute):
            self.session_state = "SESSION_FLAT"
        elif hour == self.session_cutoff_hour and minute >= self.session_cutoff_minute - 15:
            self.session_state = "POSITION_UNWIND"
        elif hour == self.session_cutoff_hour and minute >= self.session_cutoff_minute - 30:
            self.session_state = "ENTRY_RESTRICTED"
        elif hour == self.session_cutoff_hour - 1:
            self.session_state = "SESSION_APPROACHING_CUTOFF"
        else:
            self.session_state = "NORMAL_SESSION"

        return self.session_state

    def evaluate_market_movement_state(
        self,
        timeframe_candles: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Evaluates multi-scale market movement state across D1, H4, H1, M15, M5.
        Enforces macro/micro scale arbitration to prevent M5 noise from invalidating parent (H4/D1) thesis.
        """
        d1 = timeframe_candles.get("D1", timeframe_candles.get("Daily", []))
        h4 = timeframe_candles.get("H4", [])
        m5 = timeframe_candles.get("M5", [])

        d1_close = _get_price(d1[-1], "close", 2350.0) if d1 else 2350.0
        d1_prev = _get_price(d1[-2], "close", d1_close) if len(d1) > 1 else d1_close
        macro_direction = "BULLISH" if d1_close >= d1_prev else "BEARISH"

        h4_close = _get_price(h4[-1], "close", d1_close) if h4 else d1_close
        h4_open = _get_price(h4[-1], "open", h4_close) if h4 else h4_close
        parent_direction = "BULLISH" if h4_close >= h4_open else "BEARISH"

        m5_close = _get_price(m5[-1], "close", d1_close) if m5 else d1_close
        m5_open = _get_price(m5[-1], "open", m5_close) if m5 else m5_close
        local_direction = "BULLISH" if m5_close >= m5_open else "BEARISH"

        # Multi-scale arbitration: Lower scale counter-movement inside intact parent trend is a HEALTHY_PULLBACK
        is_pullback = (macro_direction != local_direction)

        if is_pullback:
            if parent_direction == macro_direction:
                movement_state = "HEALTHY_PULLBACK"
            else:
                movement_state = "DANGEROUS_PULLBACK"
        else:
            if parent_direction == macro_direction and local_direction == macro_direction:
                movement_state = "EXPANSION"
            else:
                movement_state = "CONTINUATION"

        return {
            "symbol": self.symbol,
            "macro_direction": macro_direction,
            "parent_direction": parent_direction,
            "local_direction": local_direction,
            "is_pullback": is_pullback,
            "movement_state": movement_state,
            "active_scale": "H1",
            "recent_structural_base_low": _get_price(m5[-1], "low", d1_close - 20.0) if m5 else d1_close - 20.0,
            "recent_structural_base_high": _get_price(m5[-1], "high", d1_close + 20.0) if m5 else d1_close + 20.0
        }

    def open_position(
        self,
        direction: str,
        entry_price: float,
        entry_time: Any,
        entry_scale: str = "H1",
        parent_scale: str = "H4",
        macro_scale: str = "D1",
        invalidation_price: float = 0.0,
        target_price: float = 0.0,
        parent_structure_id: Optional[str] = None
    ) -> Optional[FractalPositionThesis]:
        """
        Opens a new position with structural thesis and risk-aware sizing.
        Rejects entry if current session state restricts new entries.
        """
        session_st = self.evaluate_session_state(entry_time)
        if session_st in ["ENTRY_RESTRICTED", "POSITION_UNWIND", "SESSION_FLAT"]:
            logger.warning(f"Position entry rejected for {self.symbol} due to session state {session_st}")
            return None

        pos = FractalPositionThesis(
            symbol=self.symbol,
            direction=direction,
            entry_price=entry_price,
            entry_time=str(entry_time),
            entry_scale=entry_scale,
            parent_scale=parent_scale,
            macro_scale=macro_scale,
            risk_budget_usd=self.default_risk_budget_usd,
            structural_invalidation_price=invalidation_price,
            target_price=target_price,
            parent_structure_id=parent_structure_id
        )
        self.active_positions.append(pos)
        logger.info(f"Opened position {pos.position_id} ({pos.direction}) at {entry_price} with size {pos.position_size_oz} oz")
        return pos

    def update_positions_and_manage_lifecycle(
        self,
        current_candle: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates and manages active positions on every candle.
        Enforces 120-second minimum normal intelligent exit lifetime floor.
        Executes session unwinds to guarantee zero overnight open positions.
        """
        high = _get_price(current_candle, "high", 0.0)
        low = _get_price(current_candle, "low", 0.0)
        close = _get_price(current_candle, "close", 0.0)
        ts = current_candle.get("timestamp", current_candle.get("Timestamp", ""))

        session_st = self.evaluate_session_state(ts)
        actions_taken = []
        remaining_positions = []

        for pos in self.active_positions:
            pos.update_excursion(high, low, close)
            pos_age = pos.get_age_seconds(ts)

            # Check 1: Mandatory Session Unwind (At or near session cutoff, force close all positions to achieve ZERO overnight positions)
            if session_st in ["POSITION_UNWIND", "SESSION_FLAT"]:
                pos.thesis_status = "VALID"
                pos.exit_price = close
                pos.exit_time = str(ts)
                pos.exit_reason = "SESSION_UNWIND"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                pos.record_state_change("SESSION_UNWIND_EXIT", f"Session cutoff reached ({session_st}); forcing flat position")

                self.history_positions.append(pos)
                actions_taken.append({"action": "SESSION_UNWIND_EXIT", "reason": "SESSION_UNWIND", "position": pos.to_dict()})
                continue

            # Check 2: Hard-Risk Emergency Protection (Bypasses 120s floor for catastrophic risk breaches > 3x initial risk distance)
            hard_risk_breached = False
            catastrophic_stop = pos.entry_price - (3.0 * pos.risk_distance) if pos.direction == "BUY" else pos.entry_price + (3.0 * pos.risk_distance)
            if pos.direction == "BUY" and low <= catastrophic_stop:
                hard_risk_breached = True
            elif pos.direction == "SELL" and high >= catastrophic_stop:
                hard_risk_breached = True

            if hard_risk_breached:
                pos.thesis_status = "INVALIDATED"
                pos.exit_price = catastrophic_stop
                pos.exit_time = str(ts)
                pos.exit_reason = "HARD_RISK_EMERGENCY"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                pos.record_state_change("EXITED", "Hard risk emergency breach executed")
                self.history_positions.append(pos)
                actions_taken.append({"action": "HARD_RISK_EXIT", "reason": "HARD_RISK_EMERGENCY", "position": pos.to_dict()})
                continue

            # Check 3: Normal Intelligent Exit Rules (Enforce 120-second minimum lifetime floor)
            if pos_age < POSITION_MINIMUM_NORMAL_LIFETIME_SECONDS:
                # Normal intelligent exits are BLOCKED before 120 seconds
                pos.record_state_change("ACTIVE", f"Normal intelligent exit blocked: age {pos_age:.0f}s < 120s floor")
                remaining_positions.append(pos)
                actions_taken.append({"action": "HOLD", "reason": "AGE_BELOW_120S_FLOOR", "position": pos.to_dict()})
                continue

            # Check 4: Structural Invalidation Exit (Allowed after 120s)
            invalidated = False
            macro_dir = market_state.get("macro_direction", pos.macro_direction)
            parent_dir = market_state.get("parent_direction", pos.macro_direction)

            # Structural invalidation requires local invalidation AND parent scale divergence
            if pos.direction == "BUY" and low <= pos.structural_invalidation_price and parent_dir != "BULLISH":
                invalidated = True
                exit_price = pos.structural_invalidation_price
            elif pos.direction == "SELL" and high >= pos.structural_invalidation_price and parent_dir != "BEARISH":
                invalidated = True
                exit_price = pos.structural_invalidation_price

            if invalidated:
                pos.thesis_status = "INVALIDATED"
                pos.exit_price = exit_price
                pos.exit_time = str(ts)
                pos.exit_reason = "STRUCTURAL_INVALIDATION"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                pos.reentry_eligible = True
                pos.direction_transition_eligible = True
                pos.record_state_change("EXITED", "Structural invalidation price hit with parent scale confirmation")

                self.history_positions.append(pos)
                actions_taken.append({"action": "EXIT", "reason": "STRUCTURAL_INVALIDATION", "position": pos.to_dict()})

                # Register Re-Entry & Direction Transition Candidates
                opposite_dir = "SELL" if pos.direction == "BUY" else "BUY"
                self.reentry_candidates.append({
                    "symbol": pos.symbol,
                    "original_direction": pos.direction,
                    "exited_at_price": exit_price,
                    "exited_at_time": str(ts),
                    "status": "AWAITING_PULLBACK_COMPLETION"
                })
                self.direction_transition_candidates.append({
                    "symbol": pos.symbol,
                    "from_direction": pos.direction,
                    "to_direction": opposite_dir,
                    "invalidated_price": exit_price,
                    "status": "AWAITING_OPPOSITE_BASE_CONFIRMATION"
                })
                continue

            # Check 5: Target Completion Exit (Allowed after 120s)
            target_hit = False
            if pos.direction == "BUY" and high >= pos.target_price:
                target_hit = True
                exit_price = pos.target_price
            elif pos.direction == "SELL" and low <= pos.target_price:
                target_hit = True
                exit_price = pos.target_price

            if target_hit:
                pos.thesis_status = "VALID"
                pos.exit_price = exit_price
                pos.exit_time = str(ts)
                pos.exit_reason = "TARGET_COMPLETION"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                pos.record_state_change("EXITED", "Target zone reached successfully")

                self.history_positions.append(pos)
                actions_taken.append({"action": "EXIT", "reason": "TARGET_COMPLETION", "position": pos.to_dict()})
                continue

            # Check 6: Structural Trailing Stop Update
            struct_low = market_state.get("recent_structural_base_low", 0.0)
            struct_high = market_state.get("recent_structural_base_high", 0.0)
            if pos.direction == "BUY" and struct_low > pos.structural_invalidation_price and struct_low < close:
                pos.update_structural_trailing_stop(struct_low)
            elif pos.direction == "SELL" and struct_high < pos.structural_invalidation_price and struct_high > close:
                pos.update_structural_trailing_stop(struct_high)

            # Check 7: Adaptive Hold / Pullback Management
            mv_state = market_state.get("movement_state", "EXPANSION")
            if mv_state == "DANGEROUS_PULLBACK":
                pos.thesis_status = "WEAKENING"
                pos.record_state_change("DANGEROUS_PULLBACK", "Parent/local directional divergence")
                actions_taken.append({"action": "HOLD", "reason": "DANGEROUS_PULLBACK_WARNING", "position": pos.to_dict()})
            elif mv_state == "HEALTHY_PULLBACK":
                pos.thesis_status = "VALID"
                pos.record_state_change("HEALTHY_PULLBACK", "Healthy structural pullback in progress")
                actions_taken.append({"action": "HOLD", "reason": "HEALTHY_PULLBACK", "position": pos.to_dict()})
            else:
                pos.thesis_status = "VALID"
                pos.record_state_change("HEALTHY_EXPANSION", "Structural expansion continuing")
                actions_taken.append({"action": "HOLD", "reason": "EXPANSION_CONTINUATION", "position": pos.to_dict()})

            remaining_positions.append(pos)

        self.active_positions = remaining_positions

        # Enforce Zero Overnight Position Assertion at Session Cutoff
        if session_st in ["POSITION_UNWIND", "SESSION_FLAT"]:
            assert len(self.active_positions) == 0, f"Session Cutoff Violation: {len(self.active_positions)} open positions remaining in {session_st}"

        # Check 8: Automated Evaluation of Direction Transition & Re-entry Candidates (Only in NORMAL_SESSION)
        if not self.active_positions and self.direction_transition_candidates and session_st == "NORMAL_SESSION":
            macro_dir = market_state.get("macro_direction", "")
            for i, cand in enumerate(list(self.direction_transition_candidates)):
                if cand["to_direction"] == "SELL" and macro_dir == "BEARISH":
                    new_pos = self.execute_direction_transition(
                        candidate_idx=i,
                        entry_price=close,
                        entry_time=str(ts),
                        invalidation_price=close + 20.0,
                        target_price=close - 35.0
                    )
                    if new_pos:
                        actions_taken.append({"action": "AUTO_DIRECTION_TRANSITION", "position": new_pos.to_dict()})
                        break
                elif cand["to_direction"] == "BUY" and macro_dir == "BULLISH":
                    new_pos = self.execute_direction_transition(
                        candidate_idx=i,
                        entry_price=close,
                        entry_time=str(ts),
                        invalidation_price=close - 20.0,
                        target_price=close + 35.0
                    )
                    if new_pos:
                        actions_taken.append({"action": "AUTO_DIRECTION_TRANSITION", "position": new_pos.to_dict()})
                        break

        return actions_taken

    def execute_reentry(
        self,
        candidate_idx: int,
        entry_price: float,
        entry_time: Any,
        invalidation_price: float,
        target_price: float
    ) -> Optional[FractalPositionThesis]:
        """
        Executes structural re-entry after pullback completion.
        """
        if candidate_idx < 0 or candidate_idx >= len(self.reentry_candidates):
            return None

        session_st = self.evaluate_session_state(entry_time)
        if session_st in ["ENTRY_RESTRICTED", "POSITION_UNWIND", "SESSION_FLAT"]:
            return None

        cand = self.reentry_candidates.pop(candidate_idx)
        pos = self.open_position(
            direction=cand["original_direction"],
            entry_price=entry_price,
            entry_time=str(entry_time),
            invalidation_price=invalidation_price,
            target_price=target_price
        )
        if pos:
            pos.record_state_change("REENTRY", "Re-entry executed following pullback completion")
        return pos

    def execute_direction_transition(
        self,
        candidate_idx: int,
        entry_price: float,
        entry_time: Any,
        invalidation_price: float,
        target_price: float
    ) -> Optional[FractalPositionThesis]:
        """
        Executes symmetric direction transition (BUY -> EXIT -> SELL or SELL -> EXIT -> BUY).
        """
        if candidate_idx < 0 or candidate_idx >= len(self.direction_transition_candidates):
            return None

        session_st = self.evaluate_session_state(entry_time)
        if session_st in ["ENTRY_RESTRICTED", "POSITION_UNWIND", "SESSION_FLAT"]:
            return None

        cand = self.direction_transition_candidates.pop(candidate_idx)
        pos = self.open_position(
            direction=cand["to_direction"],
            entry_price=entry_price,
            entry_time=str(entry_time),
            invalidation_price=invalidation_price,
            target_price=target_price
        )
        if pos:
            pos.record_state_change("OPPOSITE_ENTRY_CANDIDATE", f"Symmetric direction transition executed to {cand['to_direction']}")
        return pos
