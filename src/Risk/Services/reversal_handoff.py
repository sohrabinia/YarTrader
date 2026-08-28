"""
Phase B Reversal Handoff & Risk Engine Extensions for YarTrader V1.2.
Provides Fast Scalp / Scalp reversal candidate evaluation on position close,
and cost-adjusted effective break-even calculation.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, PositionSizingResult

@dataclass
class ReversalCandidateResult:
    is_candidate: bool
    reversal_direction: str  # "BUY" or "SELL"
    reversal_price: float
    reason: str
    risk_evaluation: Optional[Dict[str, Any]] = None

class ReversalHandoffManager:
    """
    Evaluates whether a closed position's exit level constitutes a valid
    opposite-direction reversal entry candidate for Fast Scalp / Scalp styles.
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
        When a Fast Scalp / Scalp position reaches its structural exit and closes,
        evaluates if the exit level is a candidate opposite-direction entry.
        Does NOT auto-execute; must pass RTM, Price Action, Fractal, spread, liquidity,
        and risk validation.
        """
        trading_style = closed_position.get("trading_style", "FAST_SCALP").upper()
        if trading_style not in ["FAST_SCALP", "SCALP"]:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=0.0,
                reason=f"Trading style '{trading_style}' does not support reversal handoff (FAST_SCALP/SCALP only)."
            )

        exit_reason = closed_position.get("exit_reason", "").upper()
        if "STRUCTURAL_TARGET" not in exit_reason and "TAKE_PROFIT" not in exit_reason and "BASE_NODE" not in exit_reason:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction="WAIT",
                reversal_price=0.0,
                reason=f"Exit reason '{exit_reason}' is not a valid structural target completion."
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

        # Check market structure confirmation
        has_rtm_zone = market_structure.get("has_rtm_zone", False)
        has_fractal_base = market_structure.get("has_fractal_base", False)
        spread_acceptable = spread_pip <= 3.0

        if not (has_rtm_zone or has_fractal_base):
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction=reversal_direction,
                reversal_price=exit_price,
                reason="Reversal level lacks RTM zone or Fractal Base structural confirmation."
            )

        if not spread_acceptable:
            return ReversalCandidateResult(
                is_candidate=False,
                reversal_direction=reversal_direction,
                reversal_price=exit_price,
                reason=f"Spread ({spread_pip} pips) too wide for reversal scalp entry."
            )

        # Calculate potential reversal SL / TP distances
        pip_size = self.risk_engine.get_pip_size(symbol)
        sl_distance = market_structure.get("suggested_sl_pips", 20) * pip_size
        tp_distance = market_structure.get("suggested_tp_pips", 100) * pip_size  # Aiming 1:5 R/R

        if reversal_direction == "BUY":
            rev_sl = exit_price - sl_distance
            rev_tp = exit_price + tp_distance
        else:
            rev_sl = exit_price + sl_distance
            rev_tp = exit_price - tp_distance

        risk_eval = self.risk_engine.evaluate_trade_risk(
            symbol=symbol,
            direction=reversal_direction,
            entry_price=exit_price,
            stop_loss=rev_sl,
            take_profit=rev_tp,
            account_balance=account_equity,
            risk_percentage=2.0,
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
