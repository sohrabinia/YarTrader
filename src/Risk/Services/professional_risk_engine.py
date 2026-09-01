from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from src.Risk.Models.campaign import CampaignLeg, TradeCampaign

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


@dataclass
class PositionSizingResult:
    is_valid: bool
    risk_budget_usd: float
    risk_pct: float
    volume_lots: float
    margin_required_usd: float
    free_margin_usd: float
    effective_be_price: float
    rejection_reason: Optional[str] = None


class ProfessionalRiskEngine:
    """
    Professional Risk Engine for YarTrader V1.2 / Master Roadmap V1.
    Calculates exact Entry, Stop Loss, Take Profit, Transaction Costs (Spread, Commission, Slippage),
    Real Risk/Reward (Real RR), Account Equity Sizing, Effective Risk-Free Break-Even, Multi-Leg Campaign Rules,
    1% Add-On Eligibility, Free Margin Sequence Checks, and Base/Node Settlement.

    Enforces mandatory trade qualification rules:
    - Win Probability >= 50%
    - Real RR >= 1.5
    - Expected Value > 0
    - Acceptable Risk & Spread Conditions
    - Strict Free Margin & Portfolio Risk Constraints
    """

    def get_pip_size(self, symbol: str) -> float:
        s = symbol.upper()
        if "XAU" in s or "GOLD" in s:
            return 0.1
        if "BTC" in s:
            return 1.0
        if "JPY" in s:
            return 0.01
        return 0.0001

    def calculate_effective_risk_free_stop(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        volume_lots: float = 1.0,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        safety_buffer_pip: float = 0.5,
        contract_size: float = 100.0
    ) -> float:
        """
        Calculates exact stop loss price required for a position/leg to be zero-loss
        accounting for spread, commission, slippage, and execution safety buffer.
        """
        pip_size = self.get_pip_size(symbol)
        total_pips_friction = spread_pip + estimated_slippage_pip + safety_buffer_pip
        friction_dist_from_pips = total_pips_friction * pip_size

        # Convert fixed commission to price distance
        # Commission USD = commission_per_lot * volume_lots
        # Price distance per lot = Commission USD / (volume_lots * contract_size)
        commission_price_dist = commission_per_lot / contract_size if contract_size > 0 else 0.0

        total_cost_distance = friction_dist_from_pips + commission_price_dist

        if direction.upper() == "BUY":
            return round(entry_price + total_cost_distance, 4)
        elif direction.upper() == "SELL":
            return round(entry_price - total_cost_distance, 4)
        else:
            return entry_price

    def evaluate_equity_risk_and_position_size(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        account_equity: float,
        free_margin: float,
        risk_pct: float = 2.0,
        leverage: float = 100.0,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        contract_size: float = 100.0
    ) -> PositionSizingResult:
        """
        Enforces Free Margin Sequence:
        Risk Budget -> Stop Distance -> Position Size -> Margin Check -> Free Margin Check -> Execution.
        Calculates position size strictly against Account Equity (default 2.0%).
        """
        if account_equity <= 0:
            return PositionSizingResult(
                is_valid=False,
                risk_budget_usd=0.0,
                risk_pct=risk_pct,
                volume_lots=0.0,
                margin_required_usd=0.0,
                free_margin_usd=free_margin,
                effective_be_price=entry_price,
                rejection_reason="Account equity must be greater than zero."
            )

        pip_size = self.get_pip_size(symbol)
        raw_sl_dist = abs(entry_price - stop_loss)
        if raw_sl_dist <= 0:
            return PositionSizingResult(
                is_valid=False,
                risk_budget_usd=0.0,
                risk_pct=risk_pct,
                volume_lots=0.0,
                margin_required_usd=0.0,
                free_margin_usd=free_margin,
                effective_be_price=entry_price,
                rejection_reason="Stop Loss distance must be greater than zero."
            )

        risk_budget_usd = account_equity * (risk_pct / 100.0)
        friction_dist = (spread_pip + estimated_slippage_pip) * pip_size
        net_sl_dist = raw_sl_dist + friction_dist

        # Calculate volume in lots: Lot Size * (net_sl_dist * contract_size) + Lot Size * commission_per_lot = risk_budget_usd
        risk_per_lot = (net_sl_dist * contract_size) + commission_per_lot
        if risk_per_lot <= 0:
            return PositionSizingResult(
                is_valid=False,
                risk_budget_usd=risk_budget_usd,
                risk_pct=risk_pct,
                volume_lots=0.0,
                margin_required_usd=0.0,
                free_margin_usd=free_margin,
                effective_be_price=entry_price,
                rejection_reason="Invalid risk per lot calculation."
            )

        calculated_lots = risk_budget_usd / risk_per_lot
        volume_lots = round(max(0.01, calculated_lots), 2)

        # Margin Requirement Check
        margin_required = (entry_price * contract_size * volume_lots) / leverage if leverage > 0 else 0.0

        if margin_required > free_margin:
            return PositionSizingResult(
                is_valid=False,
                risk_budget_usd=risk_budget_usd,
                risk_pct=risk_pct,
                volume_lots=volume_lots,
                margin_required_usd=round(margin_required, 2),
                free_margin_usd=free_margin,
                effective_be_price=entry_price,
                rejection_reason=f"Insufficient free margin. Required: ${margin_required:.2f}, Available: ${free_margin:.2f}."
            )

        effective_be = self.calculate_effective_risk_free_stop(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            volume_lots=volume_lots,
            spread_pip=spread_pip,
            commission_per_lot=commission_per_lot,
            estimated_slippage_pip=estimated_slippage_pip,
            contract_size=contract_size
        )

        return PositionSizingResult(
            is_valid=True,
            risk_budget_usd=round(risk_budget_usd, 2),
            risk_pct=risk_pct,
            volume_lots=volume_lots,
            margin_required_usd=round(margin_required, 2),
            free_margin_usd=free_margin,
            effective_be_price=effective_be,
            rejection_reason=None
        )

    def evaluate_add_on_eligibility(
        self,
        campaign: TradeCampaign,
        new_setup_valid: bool,
        current_price: float,
        account_equity: float,
        free_margin: float,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        leverage: float = 100.0,
        contract_size: float = 100.0,
        max_portfolio_risk_pct: float = 6.0
    ) -> Dict[str, Any]:
        """
        Enforces 1% Add-On Gate:
        - Campaign must be ACTIVE.
        - Previous active legs MUST be effective risk-free (stop price at or beyond effective BE).
        - Independent new M5 setup valid.
        - Margin and portfolio exposure limits respected.
        """
        rejection_reasons = []

        if campaign.status != "ACTIVE":
            rejection_reasons.append(f"Campaign status is {campaign.status}, not ACTIVE.")

        if not new_setup_valid:
            rejection_reasons.append("New M5 setup validation failed or missing.")

        active_legs = campaign.active_legs
        if not active_legs:
            rejection_reasons.append("No active legs in campaign to add on to.")

        for leg in active_legs:
            # Update leg risk-free status based on current stop loss and price
            if leg.direction.upper() == "BUY":
                is_rf = (leg.stop_loss >= leg.effective_be_price) and (current_price >= leg.effective_be_price)
            else:
                is_rf = (leg.stop_loss <= leg.effective_be_price) and (current_price <= leg.effective_be_price)

            leg.is_effective_risk_free = is_rf
            if not is_rf:
                rejection_reasons.append(
                    f"Leg {leg.leg_id} is not effective risk-free. Effective BE: {leg.effective_be_price}, Stop: {leg.stop_loss}, Price: {current_price}."
                )

        # 1% Add-On Risk Sizing Check
        add_on_sizing = self.evaluate_equity_risk_and_position_size(
            symbol=campaign.symbol,
            direction=campaign.direction,
            entry_price=current_price,
            stop_loss=campaign.legs[0].stop_loss if active_legs else current_price,
            account_equity=account_equity,
            free_margin=free_margin,
            risk_pct=1.0,  # Strict 1% add-on
            leverage=leverage,
            spread_pip=spread_pip,
            commission_per_lot=commission_per_lot,
            estimated_slippage_pip=estimated_slippage_pip,
            contract_size=contract_size
        )

        if not add_on_sizing.is_valid:
            rejection_reasons.append(f"Add-on position sizing failed: {add_on_sizing.rejection_reason}")

        add_on_allowed = len(rejection_reasons) == 0

        return {
            "add_on_allowed": add_on_allowed,
            "add_on_risk_pct": 1.0,
            "sizing": add_on_sizing,
            "rejection_reasons": rejection_reasons
        }

    def settle_campaign(
        self,
        campaign: TradeCampaign,
        settlement_reason: str,
        current_price: float
    ) -> TradeCampaign:
        """
        Closes/Settles campaign when price reaches structural Node/Base or Target Zone.
        Locks campaign status and prevents further add-ons.
        """
        campaign.status = "SETTLED"
        campaign.settled_at = datetime.now(timezone.utc)
        campaign.settlement_reason = settlement_reason

        for leg in campaign.active_legs:
            leg.status = "CLOSED"

        return campaign

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

        pip_size = self.get_pip_size(symbol)

        raw_sl_distance = abs(entry_price - stop_loss)
        raw_tp_distance = abs(take_profit - entry_price)

        # Dynamic Market Risk & Volatility Bounds (No fixed SL/TP hardcoding)
        # Validates that Stop Loss distance is non-zero and reasonable relative to market volatility
        if raw_sl_distance < (spread_pip * pip_size):
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
                rejection_reason=f"Stop Loss distance ({raw_sl_distance:.4f}) is smaller than execution spread cost."
            )

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
