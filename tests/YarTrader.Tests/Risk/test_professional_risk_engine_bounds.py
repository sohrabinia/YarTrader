import pytest
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine

def test_risk_pct_2_percent_valid():
    """Verifies that 2.0% risk is valid under ProfessionalRiskEngine."""
    engine = ProfessionalRiskEngine()
    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        stop_loss=1995.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=2.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    )
    assert res.is_valid is True
    assert res.risk_budget_usd == 200.0  # 2.0% of $10,000.00 = $200.00

def test_risk_pct_2_01_rejected():
    """Verifies that requests exceeding 2.0% risk ceiling (e.g. 2.01%) are rejected."""
    engine = ProfessionalRiskEngine()
    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        stop_loss=1995.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=2.01,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    )
    assert res.is_valid is False
    assert "exceeds maximum allowable ceiling" in res.rejection_reason

def test_risk_pct_5_percent_rejected():
    """Verifies that 5.0% risk request is rejected immediately."""
    engine = ProfessionalRiskEngine()
    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        stop_loss=1995.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=5.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    )
    assert res.is_valid is False

def test_risk_pct_0_and_negative_rejected():
    """Verifies that 0% and negative risk requests are rejected."""
    engine = ProfessionalRiskEngine()
    res_zero = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        stop_loss=1995.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    )
    assert res_zero.is_valid is False

    res_neg = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2000.0,
        stop_loss=1995.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=-1.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    )
    assert res_neg.is_valid is False


def test_nan_and_inf_risk_pct_rejected():
    """Verifies that NaN, +Inf, -Inf, and non-numeric risk_pct are fail-closed in both public evaluation paths."""
    engine = ProfessionalRiskEngine()
    invalid_risks = [float("nan"), float("inf"), float("-inf"), "invalid_risk", None, True]

    for inv_risk in invalid_risks:
        res1 = engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1995.0,
            account_equity=10000.0,
            free_margin=10000.0,
            risk_pct=inv_risk
        )
        assert res1.is_valid is False, f"Expected evaluate_equity_risk_and_position_size to fail for risk_pct={inv_risk}"

        res2 = engine.evaluate_trade_risk(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1995.0,
            take_profit=2010.0,
            account_balance=10000.0,
            risk_percentage=inv_risk
        )
        assert res2.is_valid is False, f"Expected evaluate_trade_risk to fail for risk_percentage={inv_risk}"
