import pytest

from src.Execution.Services.strategy_risk_allocator import allocate_strategy_risk_pct


def test_equal_share_divides_global_budget_across_all_strategy_slots():
    result = allocate_strategy_risk_pct(["BASE_HIERARCHY", "RTM", "PRICE_ACTION", "SCALP", "BASE_ENGULF_REVERSAL"], "RTM")
    assert result["strategy_count"] == 5
    assert result["risk_pct"] == pytest.approx(0.2)
    assert result["risk_pct"] * result["strategy_count"] == pytest.approx(1.0)


def test_duplicate_strategy_names_do_not_get_duplicate_budget_shares():
    result = allocate_strategy_risk_pct(["RTM", "rtm", "PRICE_ACTION"], "RTM")
    assert result["strategy_count"] == 2
    assert result["risk_pct"] == pytest.approx(0.5)


def test_unknown_selected_strategy_is_included_as_a_slot():
    result = allocate_strategy_risk_pct(["RTM", "PRICE_ACTION"], "SCALP")
    assert result["strategy_count"] == 3
    assert result["risk_pct"] == pytest.approx(1.0 / 3.0)


@pytest.mark.parametrize("risk", [0, -0.1, 1.01, float("nan"), float("inf")])
def test_invalid_total_risk_budget_is_rejected(risk):
    with pytest.raises(ValueError):
        allocate_strategy_risk_pct(["RTM"], "RTM", risk)
