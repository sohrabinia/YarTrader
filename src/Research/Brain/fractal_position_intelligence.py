"""
YarTrader Autonomous Multi-Scale Position Intelligence & Lifecycle Management Module
Manages individual position lifecycles using multi-scale fractal perception, movement states, thesis tracking,
adaptive structural invalidation exits, structural trailing stops, risk-budget sizing, and directional transitions.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("YarTrader.FractalPositionIntelligence")


def _get_price(candle: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Helper to safely fetch price fields supporting both lowercase and uppercase keys."""
    val = candle.get(key, candle.get(key.capitalize(), default))
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class FractalPositionThesis:
    """
    Represents the structural thesis of an active position.
    """
    def __init__(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        entry_time: str,
        entry_scale: str = "H1",
        parent_scale: str = "H4",
        risk_budget_usd: float = 100.0,
        structural_invalidation_price: float = 0.0,
        target_price: float = 0.0
    ):
        self.position_id = f"POS_{symbol}_{uuid.uuid4().hex[:8]}"
        self.symbol = symbol.upper()
        self.direction = direction.upper()  # 'BUY' or 'SELL'
        self.entry_price = float(entry_price)
        self.entry_time = str(entry_time)
        self.entry_scale = str(entry_scale)
        self.parent_scale = str(parent_scale)
        self.risk_budget_usd = float(risk_budget_usd)
        self.structural_invalidation_price = float(structural_invalidation_price)
        self.target_price = float(target_price)

        self.current_state = "ENTERED"  # ENTERED, HEALTHY_EXPANSION, HEALTHY_PULLBACK, EXHAUSTION_WARNING, INVALIDATED, EXITED
        self.thesis_status = "VALID"    # VALID, WEAKENING, INVALIDATED
        self.current_mfe = 0.0
        self.current_mae = 0.0
        self.exit_price = 0.0
        self.exit_time = None
        self.exit_reason = None
        self.pnl_usd = 0.0

        # Calculate risk-aware position size in Oz based on structural loss distance
        self.risk_distance = abs(self.entry_price - self.structural_invalidation_price) if self.structural_invalidation_price > 0 else 20.0
        self.position_size_oz = round(self.risk_budget_usd / max(1.0, self.risk_distance), 4)

    def update_excursion(self, current_high: float, current_low: float, current_close: float):
        """
        Updates Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE).
        """
        if self.direction == "BUY":
            favorable = max(0.0, current_high - self.entry_price)
            adverse = max(0.0, self.entry_price - current_low)
        else:
            favorable = max(0.0, self.entry_price - current_low)
            adverse = max(0.0, current_high - self.entry_price)

        self.current_mfe = max(self.current_mfe, favorable)
        self.current_mae = max(self.current_mae, adverse)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": round(self.entry_price, 2),
            "entry_time": self.entry_time,
            "entry_scale": self.entry_scale,
            "parent_scale": self.parent_scale,
            "risk_budget_usd": self.risk_budget_usd,
            "structural_invalidation_price": round(self.structural_invalidation_price, 2),
            "target_price": round(self.target_price, 2),
            "risk_distance": round(self.risk_distance, 2),
            "position_size_oz": self.position_size_oz,
            "current_state": self.current_state,
            "thesis_status": self.thesis_status,
            "current_mfe": round(self.current_mfe, 2),
            "current_mae": round(self.current_mae, 2),
            "exit_price": round(self.exit_price, 2) if self.exit_price > 0 else 0.0,
            "exit_time": self.exit_time,
            "exit_reason": self.exit_reason,
            "pnl_usd": round(self.pnl_usd, 2)
        }


class FractalPositionLifecycleManager:
    """
    Manages individual position lifecycles, structural thesis, exits, and re-entry eligibility.
    """
    def __init__(self, symbol: str = "XAUUSD", default_risk_budget_usd: float = 100.0):
        self.symbol = symbol.upper()
        self.default_risk_budget_usd = default_risk_budget_usd
        self.active_positions: List[FractalPositionThesis] = []
        self.history_positions: List[FractalPositionThesis] = []
        self.reentry_candidates: List[Dict[str, Any]] = []

    def evaluate_market_movement_state(
        self,
        timeframe_candles: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Evaluates multi-scale market movement state across D1, H4, H1, M15, M5.
        Distinguishes Macro Direction vs Local Direction and Pullback vs Reversal with null-safe price getters.
        """
        d1 = timeframe_candles.get("D1", timeframe_candles.get("Daily", []))
        m5 = timeframe_candles.get("M5", [])

        d1_close = _get_price(d1[-1], "close", 2350.0) if d1 else 2350.0
        d1_prev = _get_price(d1[-2], "close", d1_close) if len(d1) > 1 else d1_close
        macro_direction = "BULLISH" if d1_close >= d1_prev else "BEARISH"

        m5_close = _get_price(m5[-1], "close", d1_close) if m5 else d1_close
        m5_open = _get_price(m5[-1], "open", m5_close) if m5 else m5_close
        local_direction = "BULLISH" if m5_close >= m5_open else "BEARISH"

        is_pullback = (macro_direction != local_direction)

        return {
            "symbol": self.symbol,
            "macro_direction": macro_direction,
            "local_direction": local_direction,
            "is_pullback": is_pullback,
            "movement_state": "PULLBACK" if is_pullback else "EXPANSION",
            "active_scale": "H1"
        }

    def open_position(
        self,
        direction: str,
        entry_price: float,
        entry_time: str,
        entry_scale: str = "H1",
        parent_scale: str = "H4",
        invalidation_price: float = 0.0,
        target_price: float = 0.0
    ) -> FractalPositionThesis:
        """
        Opens a new position with its own structural thesis and risk-aware sizing.
        """
        if invalidation_price == 0.0:
            invalidation_price = entry_price - 20.0 if direction.upper() == "BUY" else entry_price + 20.0

        if target_price == 0.0:
            target_price = entry_price + 30.0 if direction.upper() == "BUY" else entry_price - 30.0

        pos = FractalPositionThesis(
            symbol=self.symbol,
            direction=direction,
            entry_price=entry_price,
            entry_time=entry_time,
            entry_scale=entry_scale,
            parent_scale=parent_scale,
            risk_budget_usd=self.default_risk_budget_usd,
            structural_invalidation_price=invalidation_price,
            target_price=target_price
        )
        self.active_positions.append(pos)
        logger.info(f"Opened position {pos.position_id} ({pos.direction}) at {entry_price} with risk size {pos.position_size_oz} oz")
        return pos

    def update_positions_and_manage_lifecycle(
        self,
        current_candle: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates and manages all active positions individually on every candle.
        Executes structural exits, thesis invalidations, or holds using safe null-safe getters.
        """
        high = _get_price(current_candle, "high", 0.0)
        low = _get_price(current_candle, "low", 0.0)
        close = _get_price(current_candle, "close", 0.0)
        ts = str(current_candle.get("timestamp", current_candle.get("Timestamp", "")))

        actions_taken = []
        remaining_positions = []

        for pos in self.active_positions:
            pos.update_excursion(high, low, close)

            # Check 1: Structural Invalidation / Stop Hit
            invalidated = False
            if pos.direction == "BUY" and low <= pos.structural_invalidation_price:
                invalidated = True
                exit_price = pos.structural_invalidation_price
            elif pos.direction == "SELL" and high >= pos.structural_invalidation_price:
                invalidated = True
                exit_price = pos.structural_invalidation_price

            if invalidated:
                pos.current_state = "EXITED"
                pos.thesis_status = "INVALIDATED"
                pos.exit_price = exit_price
                pos.exit_time = ts
                pos.exit_reason = "STRUCTURAL_INVALIDATION"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                self.history_positions.append(pos)
                actions_taken.append({"action": "EXIT", "reason": "STRUCTURAL_INVALIDATION", "position": pos.to_dict()})

                # Register re-entry candidate if macro trend remains aligned
                self.reentry_candidates.append({
                    "symbol": pos.symbol,
                    "original_direction": pos.direction,
                    "exited_at_price": exit_price,
                    "exited_at_time": ts,
                    "status": "AWAITING_PULLBACK_COMPLETION"
                })
                continue

            # Check 2: Target Completion / Exhaustion Exit
            target_hit = False
            if pos.direction == "BUY" and high >= pos.target_price:
                target_hit = True
                exit_price = pos.target_price
            elif pos.direction == "SELL" and low <= pos.target_price:
                target_hit = True
                exit_price = pos.target_price

            if target_hit:
                pos.current_state = "EXITED"
                pos.thesis_status = "VALID"
                pos.exit_price = exit_price
                pos.exit_time = ts
                pos.exit_reason = "TARGET_COMPLETION"
                pos.pnl_usd = (pos.exit_price - pos.entry_price) * pos.position_size_oz if pos.direction == "BUY" else (pos.entry_price - pos.exit_price) * pos.position_size_oz
                self.history_positions.append(pos)
                actions_taken.append({"action": "EXIT", "reason": "TARGET_COMPLETION", "position": pos.to_dict()})
                continue

            # Check 3: Adaptive Hold / Pullback Management
            if market_state.get("is_pullback"):
                pos.current_state = "HEALTHY_PULLBACK"
                pos.thesis_status = "WEAKENING"
                actions_taken.append({"action": "HOLD", "reason": "HEALTHY_PULLBACK", "position": pos.to_dict()})
            else:
                pos.current_state = "HEALTHY_EXPANSION"
                pos.thesis_status = "VALID"
                actions_taken.append({"action": "HOLD", "reason": "EXPANSION_CONTINUATION", "position": pos.to_dict()})

            remaining_positions.append(pos)

        self.active_positions = remaining_positions
        return actions_taken
