from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from src.Risk.Models.campaign import CampaignLeg, TradeCampaign
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine

class CampaignLifecycleManager:
    """
    Campaign Lifecycle Manager for YarTrader Master Roadmap Phase B.
    Orchestrates:
    1. Initial 2% Equity Leg entry creation.
    2. Effective Risk-Free tracking (including spread, commission, slippage).
    3. 1% Add-On eligibility checks and leg creation ONLY after previous legs become effective risk-free.
    4. Base / Node campaign settlement upon reaching structural target nodes.
    5. EOD emergency flattening ensuring OPEN_POSITIONS = 0.
    """

    def __init__(self, risk_engine: Optional[ProfessionalRiskEngine] = None):
        self.risk_engine = risk_engine or ProfessionalRiskEngine()
        self.active_campaigns: Dict[str, TradeCampaign] = {}

    def create_campaign(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        account_equity: float,
        free_margin: float,
        setup_name: str = "M5_STRUCTURAL_BREAKOUT",
        zone_name: str = "RTM_KEY_NODE",
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        contract_size: float = 100.0,
        leverage: float = 100.0
    ) -> Dict[str, Any]:
        """
        Creates an initial 2% Equity TradeCampaign with Leg 1.
        """
        sizing = self.risk_engine.evaluate_equity_risk_and_position_size(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            account_equity=account_equity,
            free_margin=free_margin,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            risk_pct=2.0,  # Mandatory 2% initial risk
            leverage=leverage,
            spread_pip=spread_pip,
            commission_per_lot=commission_per_lot,
            estimated_slippage_pip=estimated_slippage_pip,
            contract_size=contract_size
        )

        if not sizing.is_valid:
            return {
                "success": False,
                "campaign": None,
                "rejection_reason": sizing.rejection_reason
            }

        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
        leg_id = f"leg_{uuid.uuid4().hex[:8]}"

        initial_leg = CampaignLeg(
            leg_id=leg_id,
            campaign_id=campaign_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume_lots=sizing.volume_lots,
            risk_pct=2.0,
            risk_amount_usd=sizing.risk_budget_usd,
            margin_required_usd=sizing.margin_required_usd,
            effective_be_price=sizing.effective_be_price,
            is_effective_risk_free=False,
            status="ACTIVE",
            setup=setup_name,
            zone=zone_name
        )

        campaign = TradeCampaign(
            campaign_id=campaign_id,
            symbol=symbol,
            direction=direction,
            status="ACTIVE",
            legs=[initial_leg],
            total_current_risk_usd=sizing.risk_budget_usd,
            max_risk_pct=2.0
        )

        self.active_campaigns[campaign_id] = campaign

        return {
            "success": True,
            "campaign": campaign,
            "initial_leg": initial_leg,
            "rejection_reason": None
        }

    def attempt_add_on_leg(
        self,
        campaign_id: str,
        new_entry_price: float,
        new_take_profit: float,
        new_setup_valid: bool,
        current_market_price: float,
        account_equity: float,
        free_margin: float,
        spread_pip: float = 1.0,
        commission_per_lot: float = 7.0,
        estimated_slippage_pip: float = 0.5,
        contract_size: float = 100.0,
        leverage: float = 100.0
    ) -> Dict[str, Any]:
        """
        Attempts to add a 1% Equity Add-On leg to an active campaign.
        Strictly requires all previous legs to be Effective Risk-Free.
        """
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return {
                "success": False,
                "add_on_leg": None,
                "rejection_reason": f"Campaign {campaign_id} not found."
            }

        eligibility = self.risk_engine.evaluate_add_on_eligibility(
            campaign=campaign,
            new_setup_valid=new_setup_valid,
            current_price=current_market_price,
            account_equity=account_equity,
            free_margin=free_margin,
            spread_pip=spread_pip,
            commission_per_lot=commission_per_lot,
            estimated_slippage_pip=estimated_slippage_pip,
            leverage=leverage,
            contract_size=contract_size
        )

        if not eligibility["add_on_allowed"]:
            return {
                "success": False,
                "add_on_leg": None,
                "rejection_reason": "; ".join(eligibility["rejection_reasons"])
            }

        sizing = eligibility["sizing"]
        leg_id = f"leg_{uuid.uuid4().hex[:8]}"

        add_on_leg = CampaignLeg(
            leg_id=leg_id,
            campaign_id=campaign_id,
            symbol=campaign.symbol,
            direction=campaign.direction,
            entry_price=new_entry_price,
            stop_loss=campaign.legs[0].stop_loss,  # Share protected stop or new trailing stop
            take_profit=new_take_profit,
            volume_lots=sizing.volume_lots,
            risk_pct=1.0,  # 1% add-on
            risk_amount_usd=sizing.risk_budget_usd,
            margin_required_usd=sizing.margin_required_usd,
            effective_be_price=sizing.effective_be_price,
            is_effective_risk_free=False,
            status="ACTIVE",
            setup="M5_ADD_ON_SETUP"
        )

        campaign.legs.append(add_on_leg)

        return {
            "success": True,
            "add_on_leg": add_on_leg,
            "campaign": campaign,
            "rejection_reason": None
        }

    def settle_at_node(
        self,
        campaign_id: str,
        current_market_price: float,
        reason: str = "STRUCTURAL_NODE_REACHED"
    ) -> Optional[TradeCampaign]:
        """
        Settles campaign when price reaches structural Node / Base / Target.
        """
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return None

        settled = self.risk_engine.settle_campaign(campaign, reason, current_market_price)
        return settled

    def flatten_all_at_eod(self, reason: str = "EOD_FLATTEN") -> List[TradeCampaign]:
        """
        Flattens all active campaigns at Session EOD cutoff.
        """
        flattened = []
        for campaign_id, campaign in list(self.active_campaigns.items()):
            if campaign.status == "ACTIVE":
                campaign.status = "FLATTENED"
                campaign.settled_at = datetime.now(timezone.utc)
                campaign.settlement_reason = reason
                for leg in campaign.legs:
                    leg.status = "CLOSED"
                flattened.append(campaign)
        return flattened
