import pytest
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, TradeCampaign, CampaignLeg
from src.Risk.Services.reversal_handoff import ReversalHandoffManager

class TestPhaseBRiskAndReversal:
    def test_effective_cost_adjusted_break_even(self):
        engine = ProfessionalRiskEngine()
        # BUY XAUUSD entry 2000.0, spread=1 pip ($0.10), commission=$7/lot ($0.07), slippage=0.5 pip ($0.05), buffer=0.5 pip ($0.05)
        # Total cost distance = (1 + 0.5 + 0.5)*0.1 + 7/100 = 0.20 + 0.07 = 0.27
        be_buy = engine.calculate_effective_risk_free_stop(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            volume_lots=1.0,
            spread_pip=1.0,
            commission_per_lot=7.0,
            estimated_slippage_pip=0.5,
            safety_buffer_pip=0.5,
            contract_size=100.0
        )
        assert be_buy == 2000.27

        # SELL XAUUSD entry 2000.0
        be_sell = engine.calculate_effective_risk_free_stop(
            symbol="XAUUSD",
            direction="SELL",
            entry_price=2000.0,
            volume_lots=1.0,
            spread_pip=1.0,
            commission_per_lot=7.0,
            estimated_slippage_pip=0.5,
            safety_buffer_pip=0.5,
            contract_size=100.0
        )
        assert be_sell == 1999.73

    def test_add_on_gated_by_risk_free_status(self):
        engine = ProfessionalRiskEngine()
        leg1 = CampaignLeg(
            leg_id="leg-1",
            campaign_id="camp-1",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            volume_lots=1.0,
            risk_pct=2.0,
            risk_amount_usd=200.0,
            margin_required_usd=2000.0,
            effective_be_price=2000.27,
            is_effective_risk_free=False
        )
        campaign = TradeCampaign(
            campaign_id="camp-1",
            symbol="XAUUSD",
            direction="BUY",
            legs=[leg1],
            status="ACTIVE"
        )

        # Price at 2005.0, but stop loss is still 1990.0 (< BE 2000.27) -> Add-on REJECTED
        result1 = engine.evaluate_add_on_eligibility(
            campaign=campaign,
            new_setup_valid=True,
            current_price=2005.0,
            account_equity=10000.0,
            free_margin=8000.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            leverage=100.0,
            contract_size=100.0
        )
        assert not result1["add_on_allowed"]
        assert any("not effective risk-free" in r for r in result1["rejection_reasons"])

        # Now move stop_loss to 2000.30 (>= 2000.27) -> Add-on ALLOWED with 1% risk
        leg1.stop_loss = 2000.30
        result2 = engine.evaluate_add_on_eligibility(
            campaign=campaign,
            new_setup_valid=True,
            current_price=2005.0,
            account_equity=10000.0,
            free_margin=8000.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            leverage=100.0,
            contract_size=100.0
        )
        assert result2["add_on_allowed"]
        assert result2["add_on_risk_pct"] == 1.0

    def test_reversal_handoff_candidate_evaluation(self):
        manager = ReversalHandoffManager()
        closed_pos = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "exit_price": 2020.0,
            "exit_reason": "STRUCTURAL_TARGET_REACHED",
            "trading_style": "FAST_SCALP"
        }
        structure = {
            "has_rtm_zone": True,
            "has_fractal_base": True,
            "suggested_sl_pips": 20,
            "suggested_tp_pips": 120,
            "win_probability": 0.60
        }

        res = manager.evaluate_reversal_candidate(
            closed_position=closed_pos,
            market_structure=structure,
            account_equity=10000.0,
            free_margin=8000.0,
            spread_pip=1.0
        )
        assert res.is_candidate
        assert res.reversal_direction == "SELL"
        assert res.reversal_price == 2020.0
