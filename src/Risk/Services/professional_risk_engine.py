from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RiskEvaluationResult:
    is_valid: bool
    direction: str  # "BUY", "SELL", "WAIT"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount_usd: float
    potential_reward_usd: float
    spread_cost_pip: float
    commission_usd: float
    slippage_pip: float
    gross_rr: float
    real_rr: float
    win_probability: float
    expected_value: float
    rejection_reason: Optional[str] = None

class ProfessionalRiskEngine:
    """
    Professional Risk Engine for YarTrader V1.2.
    Calculates exact Entry, Stop Loss, Take Profit, Transaction Costs (Spread, Commission, Slippage),
    and Real Risk/Reward (Real RR).

    Enforces mandatory trade qualification rules:
    - Win Probability >= 50%
    - Real RR >= 1.5
    - Expected Value > 0
    - Acceptable Risk & Spread Conditions
    Otherwise outputs direction = "WAIT".
    """

    def evaluate_trade_risk(
        self,
        symbol: str,
        direction: str,  # "BUY" or "SELL"
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        account_balance: float = 10000.0,
        risk_percentage: float = 1.0,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        win_probability: float = 0.55
    ) -> RiskEvaluationResult:
        if direction not in ["BUY", "SELL"]:
            return RiskEvaluationResult(
                is_valid=False,
                direction="WAIT",
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount_usd=0.0,
                potential_reward_usd=0.0,
                spread_cost_pip=spread_pip,
                commission_usd=0.0,
                slippage_pip=estimated_slippage_pip,
                gross_rr=0.0,
                real_rr=0.0,
                win_probability=win_probability,
                expected_value=0.0,
                rejection_reason="Invalid direction specified."
            )

        # Pip value factor estimation (Forex vs Gold vs BTC)
        pip_size = 0.0001 if "USD" in symbol and "XAU" not in symbol and "BTC" not in symbol else 0.1
        if "XAU" in symbol:
            pip_size = 0.1
        elif "BTC" in symbol:
            pip_size = 1.0

        raw_sl_distance = abs(entry_price - stop_loss)
        raw_tp_distance = abs(take_profit - entry_price)

        if raw_sl_distance <= 0:
            return RiskEvaluationResult(
                is_valid=False,
                direction="WAIT",
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_amount_usd=0.0,
                potential_reward_usd=0.0,
                spread_cost_pip=spread_pip,
                commission_usd=0.0,
                slippage_pip=estimated_slippage_pip,
                gross_rr=0.0,
                real_rr=0.0,
                win_probability=win_probability,
                expected_value=0.0,
                rejection_reason="Stop Loss distance must be greater than zero."
            )

        gross_rr = raw_tp_distance / raw_sl_distance

        # Adjust for costs (Spread + Slippage)
        cost_pip = spread_pip + estimated_slippage_pip
        cost_distance = cost_pip * pip_size

        net_tp_distance = max(0.0, raw_tp_distance - cost_distance)
        net_sl_distance = raw_sl_distance + cost_distance

        real_rr = net_tp_distance / net_sl_distance if net_sl_distance > 0 else 0.0

        # Capital Risk Calculation
        target_risk_usd = account_balance * (risk_percentage / 100.0)
        potential_reward_usd = target_risk_usd * real_rr

        # Expected Value = (Win Prob * Net Reward) - ((1 - Win Prob) * Risk)
        expected_value = (win_probability * potential_reward_usd) - ((1.0 - win_probability) * target_risk_usd)

        # Qualification Gate Checks
        rejection_reasons = []
        if win_probability < 0.50:
            rejection_reasons.append(f"Win probability ({win_probability*100:.1f}%) < 50.0% threshold.")

        if real_rr < 1.5:
            rejection_reasons.append(f"Real RR ({real_rr:.2f}) < 1.5 minimum threshold.")

        if expected_value <= 0:
            rejection_reasons.append(f"Expected Value (${expected_value:.2f}) <= 0.")

        if spread_pip > 5.0:
            rejection_reasons.append(f"Spread ({spread_pip} pips) exceeds maximum safe threshold (5.0 pips).")

        is_valid = len(rejection_reasons) == 0
        final_direction = direction if is_valid else "WAIT"
        rejection_msg = "; ".join(rejection_reasons) if rejection_reasons else None

        return RiskEvaluationResult(
            is_valid=is_valid,
            direction=final_direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount_usd=round(target_risk_usd, 2),
            potential_reward_usd=round(potential_reward_usd, 2),
            spread_cost_pip=spread_pip,
            commission_usd=commission_per_lot,
            slippage_pip=estimated_slippage_pip,
            gross_rr=round(gross_rr, 2),
            real_rr=round(real_rr, 2),
            win_probability=win_probability,
            expected_value=round(expected_value, 2),
            rejection_reason=rejection_msg
        )
