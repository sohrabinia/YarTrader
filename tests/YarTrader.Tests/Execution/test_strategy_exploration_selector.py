import json
from pathlib import Path

from src.Learning.Services.strategy_exploration_selector import choose_demo_strategy


def test_selector_round_robins_equal_sample_candidates(tmp_path):
    a = choose_demo_strategy(["RTM", "PRICE_ACTION", "SCALP"], "EURUSD", tmp_path)
    b = choose_demo_strategy(["RTM", "PRICE_ACTION", "SCALP"], "EURUSD", tmp_path)
    c = choose_demo_strategy(["RTM", "PRICE_ACTION", "SCALP"], "EURUSD", tmp_path)
    assert [a["selected_strategy"], b["selected_strategy"], c["selected_strategy"]] == ["RTM", "PRICE_ACTION", "SCALP"]
    assert all(not item["validated_for_live"] and not item["activation_allowed"] for item in (a, b, c))


def test_selector_prioritizes_lowest_observed_sample_count(tmp_path):
    root = tmp_path / "XAUUSD"
    root.mkdir()
    (root / "autonomous_strategy_discovery.json").write_text(json.dumps({"cohorts": [
        {"cohort": "XAUUSD|BASE_HIERARCHY", "closed_position_count": 30, "net_expectancy_per_position": -3, "profit_factor": 0.8, "status": "INSUFFICIENT_SAMPLE_RESEARCH_ONLY"},
        {"cohort": "XAUUSD|RTM", "closed_position_count": 4, "net_expectancy_per_position": 1, "profit_factor": 1.1, "status": "INSUFFICIENT_SAMPLE_RESEARCH_ONLY"}
    ]}), encoding="utf-8")
    result = choose_demo_strategy(["BASE_HIERARCHY", "RTM", "PRICE_ACTION"], "XAUUSD", tmp_path)
    assert result["selected_strategy"] == "PRICE_ACTION"
    assert result["observed_closed_positions"] == 0


def test_selector_prioritizes_promising_but_unvalidated_demo_hypothesis(tmp_path):
    root = tmp_path / "XAUUSD"
    root.mkdir()
    (root / "autonomous_strategy_discovery.json").write_text(json.dumps({"cohorts": [
        {"cohort": "XAUUSD|RTM", "closed_position_count": 30, "net_expectancy_per_position": 3.2, "profit_factor": 1.3, "status": "PROMISING_HYPOTHESIS_REQUIRES_WALK_FORWARD"}
    ]}), encoding="utf-8")
    result = choose_demo_strategy(["BASE_HIERARCHY", "RTM"], "XAUUSD", tmp_path)
    assert result["selected_strategy"] == "RTM"
    assert result["reason"] == "PROMISING_DEMO_HYPOTHESIS_REQUIRES_WALK_FORWARD"
    assert result["validated_for_live"] is False
