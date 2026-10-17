import pytest

from src.Execution.Services.strategy_risk_allocator import allocate_demo_slot_risk_pct


def test_demo_risk_is_per_trade_and_not_divided_by_concurrent_slots():
    # A three-slot cap limits concurrency; it must not divide the explicit 1%
    # per-trade budget into thirds and incorrectly reject valid minimum lots.
    result = allocate_demo_slot_risk_pct([], "BASE_HIERARCHY", max_slots=3, total_risk_pct=1.0)
    assert result["risk_pct"] == pytest.approx(1.0)
    assert result["strategy_count"] == 1
    assert result["max_concurrent_slots"] == 3
    assert result["reserved_slot_count"] == 2
    assert result["allocation_method"] == "PER_TRADE_TARGET_WITH_SEPARATE_AGGREGATE_AND_DAILY_CAPS"


def test_demo_risk_reserves_budget_for_existing_and_future_slots():
    result = allocate_demo_slot_risk_pct(
        ["BASE_HIERARCHY"], "BASE_ENGULF_REVERSAL", max_slots=3, total_risk_pct=1.0
    )
    assert result["risk_pct"] == pytest.approx(1.0)
    assert result["reserved_slot_count"] == 1


def test_demo_risk_rejects_more_occupied_slots_than_configured():
    with pytest.raises(ValueError, match="exceed the configured maximum"):
        allocate_demo_slot_risk_pct(
            ["BASE_HIERARCHY", "RTM"], "BASE_ENGULF_REVERSAL", max_slots=2, total_risk_pct=1.0
        )
