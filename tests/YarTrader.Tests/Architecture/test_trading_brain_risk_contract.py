"""Trading Brain -> planning/risk contract regression tests."""

from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy


def _planner():
    return ExecutionIntelligencePlanner()


def test_production_risk_policy_is_canonical():
    assert ProductionRiskPolicy.TARGET_RISK_PCT == 0.5
    assert ProductionRiskPolicy.HARD_CEILING_RISK_PCT == 2.0
    assert ProductionRiskPolicy.MINIMUM_RR == 1.5
    assert ProductionRiskPolicy.MAX_DAILY_LOSS_PCT == 8.0


def test_planner_never_fabricates_sl_tp_when_brain_has_action_but_structure_has_no_levels():
    result = _planner().generate_execution_plan(
        symbol="XAUUSD",
        timeframe="H1",
        narrative={"trend": "BULLISH", "data_source": "RAW_MARKET_DATA"},
        liquidity={"latest_sweep": None, "resting_bsl": [], "resting_ssl": []},
        zones={"order_blocks": [], "fair_value_gaps": []},
        alignment={"alignment": "ALIGNED", "confidence": 80},
        similarity={},
        portfolio_risk={"approved": True},
        current_price=2650.0,
        newborn_brain_report={
            "brain_available": True,
            "active_hypotheses": [
                {"suggested_virtual_action": "BUY"}
            ],
        },
    )
    plan = result["plan"]
    assert plan["action"] == "WAIT"
    assert plan["entry"] == 0.0
    assert plan["stop_loss"] == 0.0
    assert plan["take_profit"] == 0.0
    assert plan["risk_reward"] == 0.0


def test_planner_rejects_structure_with_rr_below_minimum():
    result = _planner().generate_execution_plan(
        symbol="XAUUSD",
        timeframe="H1",
        narrative={"trend": "BULLISH", "data_source": "RAW_MARKET_DATA"},
        liquidity={"latest_sweep": None, "resting_bsl": [2650.5], "resting_ssl": []},
        zones={
            "order_blocks": [{"type": "BULLISH_OB", "bottom": 2649.5}],
            "fair_value_gaps": [],
        },
        alignment={"alignment": "ALIGNED", "confidence": 80},
        similarity={},
        portfolio_risk={"approved": True},
        current_price=2650.0,
        newborn_brain_report={
            "brain_available": True,
            "active_hypotheses": [{"suggested_virtual_action": "BUY"}],
        },
    )
    assert result["plan"]["action"] == "WAIT"
    assert result["plan"]["risk_reward"] == 0.0
