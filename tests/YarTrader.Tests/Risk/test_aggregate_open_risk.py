import pytest

from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine


def test_aggregate_open_risk_allows_only_when_existing_and_candidate_risk_fit_cap():
    engine = ProfessionalRiskEngine()
    result = engine.evaluate_aggregate_open_risk(
        account_equity=10_000.0,
        open_risk_usd=[30.0, 25.0],
        candidate_risk_usd=40.0,
    )
    assert result["allowed"] is True
    assert result["existing_open_risk_usd"] == 55.0
    assert result["aggregate_open_risk_usd"] == 95.0
    assert result["max_open_risk_usd"] == 100.0


def test_aggregate_open_risk_blocks_candidate_that_exceeds_portfolio_cap():
    result = ProfessionalRiskEngine().evaluate_aggregate_open_risk(
        account_equity=10_000.0,
        open_risk_usd=[60.0],
        candidate_risk_usd=45.0,
    )
    assert result["allowed"] is False
    assert result["reason"] == "AGGREGATE_OPEN_RISK_LIMIT_EXCEEDED"
    assert result["aggregate_open_risk_usd"] == 105.0


def test_aggregate_risk_limit_cannot_be_configured_above_hard_ceiling():
    result = ProfessionalRiskEngine().evaluate_aggregate_open_risk(
        account_equity=10_000.0,
        open_risk_usd=[80.0],
        candidate_risk_usd=30.0,
        max_aggregate_risk_pct=50.0,
    )
    assert result["allowed"] is False
    assert result["max_open_risk_pct"] == 1.0


@pytest.mark.parametrize(
    ("equity", "open_risk", "candidate"),
    [
        (0.0, [], 1.0),
        (10_000.0, [float("nan")], 1.0),
        (10_000.0, [-1.0], 1.0),
        (10_000.0, [], float("inf")),
    ],
)
def test_aggregate_risk_fails_closed_for_invalid_inputs(equity, open_risk, candidate):
    result = ProfessionalRiskEngine().evaluate_aggregate_open_risk(
        account_equity=equity,
        open_risk_usd=open_risk,
        candidate_risk_usd=candidate,
    )
    assert result["allowed"] is False
