import pytest
from datetime import datetime, timezone

from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
from src.Risk.Services.campaign_manager import CampaignLifecycleManager
from src.Risk.Models.campaign import TradeCampaign, CampaignLeg

class TestPhaseBRiskCampaign:

    @pytest.fixture
    def risk_engine(self):
        return ProfessionalRiskEngine()

    @pytest.fixture
    def manager(self, risk_engine):
        return CampaignLifecycleManager(risk_engine=risk_engine)

    def test_2_percent_initial_risk_equity_sizing(self, risk_engine):
        # Test 2% Equity Risk calculation
        res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            account_equity=10000.0,
            free_margin=5000.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            risk_pct=2.0,
            leverage=100.0,
            contract_size=100.0,
            spread_pip=1.0,
            commission_per_lot=7.0,
            estimated_slippage_pip=0.5
        )
        assert res.is_valid is True
        assert res.risk_budget_usd == 200.0  # 2% of $10,000
        assert res.volume_lots > 0
        assert res.margin_required_usd < 5000.0
        assert res.effective_be_price > 2000.0  # Must cover friction for BUY

    def test_effective_risk_free_stop_calculation(self, risk_engine):
        # For BUY: entry + spread + slippage + buffer + commission_dist
        be_buy = risk_engine.calculate_effective_risk_free_stop(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            volume_lots=1.0,
            contract_size=100.0,
            spread_pip=1.0,
            commission_per_lot=7.0,
            estimated_slippage_pip=0.5,
            safety_buffer_pip=0.5
        )
        # Total pips friction = 1.0 + 0.5 + 0.5 = 2.0 pips * 0.1 = 0.20 + comm dist (7/100 = 0.07) = +0.27
        assert be_buy >= 2000.20

        # For SELL: entry - spread - slippage - buffer - commission_dist
        be_sell = risk_engine.calculate_effective_risk_free_stop(
            symbol="XAUUSD",
            direction="SELL",
            entry_price=2000.0,
            volume_lots=1.0,
            contract_size=100.0,
            spread_pip=1.0,
            commission_per_lot=7.0,
            estimated_slippage_pip=0.5,
            safety_buffer_pip=0.5
        )
        assert be_sell <= 1999.80

    def test_add_on_blocked_before_risk_free(self, manager):
        # Create campaign (Leg 1)
        created = manager.create_campaign(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            account_equity=10000.0,
            free_margin=5000.0
        )
        assert created["success"] is True
        campaign = created["campaign"]

        # Attempt add-on when market price has NOT reached effective BE and stop is still at initial SL
        add_on = manager.attempt_add_on_leg(
            campaign_id=campaign.campaign_id,
            new_entry_price=2010.0,
            new_take_profit=2060.0,
            new_setup_valid=True,
            current_market_price=2001.0,  # Below effective BE
            account_equity=10000.0,
            free_margin=4500.0
        )
        assert add_on["success"] is False
        assert "not effective risk-free" in add_on["rejection_reason"]

    def test_add_on_allowed_after_risk_free(self, manager):
        # Create campaign (Leg 1)
        created = manager.create_campaign(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            account_equity=10000.0,
            free_margin=5000.0
        )
        campaign = created["campaign"]
        leg1 = campaign.legs[0]

        # Protect Leg 1 by moving stop loss to or above effective BE price
        leg1.stop_loss = leg1.effective_be_price + 0.10

        # Now market price has advanced well above effective BE
        add_on = manager.attempt_add_on_leg(
            campaign_id=campaign.campaign_id,
            new_entry_price=2015.0,
            new_take_profit=2060.0,
            new_setup_valid=True,
            current_market_price=2015.0,  # Above effective BE
            account_equity=10000.0,
            free_margin=4500.0
        )
        assert add_on["success"] is True
        assert len(campaign.legs) == 2
        assert campaign.legs[1].risk_pct == 1.0  # Strict 1% add-on

    def test_campaign_node_settlement(self, manager):
        created = manager.create_campaign(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            account_equity=10000.0,
            free_margin=5000.0
        )
        campaign = created["campaign"]

        # Price hits structural target node
        settled = manager.settle_at_node(
            campaign_id=campaign.campaign_id,
            current_market_price=2050.0,
            reason="TARGET_NODE_REACHED"
        )
        assert settled is not None
        assert settled.status == "SETTLED"
        assert settled.settlement_reason == "TARGET_NODE_REACHED"

        # Further add-on to settled campaign must be blocked
        add_on = manager.attempt_add_on_leg(
            campaign_id=campaign.campaign_id,
            new_entry_price=2055.0,
            new_take_profit=2080.0,
            new_setup_valid=True,
            current_market_price=2055.0,
            account_equity=10000.0,
            free_margin=4500.0
        )
        assert add_on["success"] is False
        assert "Campaign status is SETTLED" in add_on["rejection_reason"]

    def test_margin_insufficiency_rejection(self, risk_engine):
        # Attempt trade when required margin exceeds free margin
        res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1999.0,  # Very tight SL -> Huge lot size requirement
            account_equity=100000.0,
            free_margin=50.0,  # Tiny free margin
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            contract_size=100.0,
            risk_pct=2.0,
            leverage=10.0
        )
        assert res.is_valid is False
        assert "Insufficient free margin" in res.rejection_reason

    def test_eod_flatten_safety_invariant(self, manager):
        manager.create_campaign(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            account_equity=10000.0,
            free_margin=5000.0
        )
        manager.create_campaign(
            symbol="EURUSD",
            direction="SELL",
            entry_price=1.0800,
            stop_loss=1.0850,
            take_profit=1.0700,
            account_equity=10000.0,
            free_margin=5000.0
        )

        assert len(manager.active_campaigns) == 2

        # Trigger EOD Flatten
        flattened = manager.flatten_all_at_eod(reason="SESSION_EOD_CUTOFF")
        assert len(flattened) == 2
        for camp in manager.active_campaigns.values():
            assert camp.status == "FLATTENED"
            for leg in camp.legs:
                assert leg.status == "CLOSED"
