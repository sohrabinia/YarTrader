from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator


def test_orchestrator_exposes_only_base_hierarchy():
    orchestrator = StrategyOrchestrator()
    assert orchestrator.supported_strategies == ["BASE_HIERARCHY"]


def test_orchestrator_fails_closed_without_candles():
    result = StrategyOrchestrator().evaluate_all_strategies(
        symbol="XAUUSD", primary_timeframe="M1", candles=[]
    )
    assert result["candidates"] == []
    assert result["best_candidate"] is None
    assert result["active_candidates_count"] == 0
    assert "No candle data" in result["summary"]
