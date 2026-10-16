"""
Base-hierarchy reversal handoff and risk checks.
Only a previously confirmed Base structure with an explicit destination Base may qualify.
"""

from typing import Dict, Any, Optional
import math
from dataclasses import dataclass

from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, PositionSizingResult, ProductionRiskPolicy

@dataclass
class ReversalCandidateResult:
    is_candidate: bool
    reversal_direction: str  # "BUY" or "SELL"
    reversal_price: float
    reason: str
    risk_evaluation: Optional[Dict[str, Any]] = None

class ReversalHandoffManager:
    """
    Evaluates a possible opposite-direction handoff only when the canonical
    Base hierarchy and destination Base are explicitly supplied.
    """

    def __init__(self, risk_engine: Optional[ProfessionalRiskEngine] = None):
        self.risk_engine = risk_engine or ProfessionalRiskEngine()

    def evaluate_reversal_candidate(
        self,
        closed_position: Dict[str, Any],
        market_structure: Dict[str, Any],
        account_equity: float,
        free_margin: float,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5
    ) -> ReversalCandidateResult:
        """
        No legacy trading styles or alternate strategy confirmations are accepted.
        This method never submits orders.
        """
        trading_style = closed_position.get("trading_style", "BASE_HIERARCHY").upper()
        if trading_style != "BASE_HIERARCHY":
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=0.0,
                reason="Only BASE_HIERARCHY is supported; legacy trading styles are disabled."
            )

        exit_reason = closed_position.get("exit_reason", "").upper()
        structural_completion = any(token in exit_reason for token in (
            "STRUCTURAL_TARGET", "TAKE_PROFIT", "BASE_NODE"
        ))
        economic_wave_exit = exit_reason in {
            "ECONOMIC_WAVE_EXHAUSTION", "WAVE_REVERSAL_CONFIRMED",
            "STRUCTURAL_INVALIDATION", "TRAILING_STOP_REVERSAL"
        }
        if not (structural_completion or economic_wave_exit):
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=0.0,
                reason=f"Exit reason '{exit_reason}' is not eligible for reversal handoff."
            )

        if economic_wave_exit:
            reversal_confirmed = market_structure.get("reversal_confirmed") is True
            net_ev = market_structure.get("net_expected_value_r")
            net_rr = market_structure.get("net_reward_risk")
            try:
                economically_viable = (
                    net_ev is not None and float(net_ev) > 0.0
                    and net_rr is not None and float(net_rr) >= 1.2
                )
            except (TypeError, ValueError):
                economically_viable = False
            if not reversal_confirmed or not economically_viable:
                return ReversalCandidateResult(
                    is_candidate=False,
                    reversal_direction="WAIT",
                    reversal_price=0.0,
                    reason=(
                        "Economic reversal rejected: require confirmed opposite structure, "
                        "positive net expected value after costs, and net reward/risk >= 1.2."
                    ),
                    risk_evaluation={
                        "reversal_confirmed": reversal_confirmed,
                        "net_expected_value_r": net_ev,
                        "net_reward_risk": net_rr,
                    }
                )

        symbol = closed_position.get("symbol", "XAUUSD")
        closed_direction = closed_position.get("direction", "BUY").upper()
        reversal_direction = "SELL" if closed_direction == "BUY" else "BUY"
        exit_price = float(closed_position.get("exit_price", 0.0))

        if exit_price <= 0:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=0.0,
                reason="Invalid exit price on closed position."
            )

        # Require canonical Base evidence and a destination Base already identified
        # from closed data. No RTM/Fractal/FVG or fixed-pip fallback is permitted.
        try:
            base_width = float(market_structure["base_width"])
            target_base_price = float(market_structure["target_base_price"])
            base_confirmed = market_structure.get("base_hierarchy_confirmed") is True
        except (KeyError, TypeError, ValueError, OverflowError):
            base_width, target_base_price, base_confirmed = 0.0, 0.0, False
        target_is_ahead = (target_base_price > exit_price if reversal_direction == "BUY"
                           else 0.0 < target_base_price < exit_price)
        if not base_confirmed or not math.isfinite(base_width) or base_width <= 0 or not target_is_ahead:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=exit_price,
                reason="Base-only handoff requires confirmed Base hierarchy, positive Base width, and a valid destination Base."
            )
        spread_acceptable = spread_pip <= 3.0

        if not spread_acceptable:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction=reversal_direction,
                reversal_price=exit_price,
                reason=f"Spread ({spread_pip} pips) too wide for reversal scalp entry."
            )

        # Derive invalidation from this Base's width and target the explicit next Base.
        sl_distance = 0.15 * base_width
        rev_tp = target_base_price

        if reversal_direction == "BUY":
            rev_sl = exit_price - sl_distance
        else:
            rev_sl = exit_price + sl_distance

        risk_eval = self.risk_engine.evaluate_trade_risk(
            symbol=symbol,
            direction=reversal_direction,
            entry_price=exit_price,
            stop_loss=rev_sl,
            take_profit=rev_tp,
            account_balance=account_equity,
            risk_percentage=ProductionRiskPolicy.TARGET_RISK_PCT,
            spread_pip=spread_pip,
            commission_per_lot=commission_per_lot,
            estimated_slippage_pip=estimated_slippage_pip,
            win_probability=market_structure.get("win_probability", 0.55)
        )

        if not risk_eval.is_valid:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction=reversal_direction,
                reversal_price=exit_price,
                reason=f"Reversal candidate risk evaluation failed: {risk_eval.rejection_reason}",
                risk_evaluation={"is_valid": False, "reason": risk_eval.rejection_reason}
            )

        return ReversalCandidateResult(
            is_candidate=True,
            reversal_direction=reversal_direction,
            reversal_price=exit_price,
            reason="Valid opposite-direction entry candidate at structural exit level.",
            risk_evaluation={
                "is_valid": True,
                "real_rr": risk_eval.real_rr,
                "expected_value": risk_eval.expected_value,
                "stop_loss": rev_sl,
                "take_profit": rev_tp
            }
        )
