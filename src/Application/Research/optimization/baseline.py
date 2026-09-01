from typing import Dict, Any, List
from src.Application.Research.optimization.objective import ObjectiveEvaluator
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

class BaselineEvaluator:
    """
    Control group baseline evaluator for YarTrader Research Optimization.
    Establishes and locks the frozen default configuration baseline for comparison against candidate configurations.
    """
    def __init__(self) -> None:
        self.backtest_engine = BacktestAndLearningEngine()

    def evaluate_frozen_baseline(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        initial_balance: float = 10000.0,
        commit_sha: str = "5b7e817d44f43131a8ce68193a36bcbf2fdbd0fc"
    ) -> Dict[str, Any]:
        res = self.backtest_engine.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            initial_balance=initial_balance
        )

        closed_trades = res.get("closed_trades", [])
        metrics = ObjectiveEvaluator.calculate_metrics(closed_trades, initial_balance=initial_balance)

        return {
            "baseline_commit_sha": commit_sha,
            "baseline_strategy_configuration": "DEFAULT_FROZEN_CORE",
            "baseline_trade_count": metrics["total_trades"],
            "baseline_net_pnl": metrics["net_pnl"],
            "baseline_win_rate_pct": metrics["win_rate_pct"],
            "baseline_profit_factor": metrics["profit_factor"],
            "baseline_expectancy": metrics["expectancy"],
            "baseline_max_drawdown_pct": metrics["max_drawdown_pct"],
            "baseline_objective_score": metrics["objective_score"]
        }

    @staticmethod
    def compare_candidate_to_baseline(baseline: Dict[str, Any], candidate_test_metrics: Dict[str, Any]) -> Dict[str, Any]:
        pnl_diff = candidate_test_metrics.get("net_pnl", 0.0) - baseline.get("baseline_net_pnl", 0.0)
        win_rate_diff = candidate_test_metrics.get("win_rate_pct", 0.0) - baseline.get("baseline_win_rate_pct", 0.0)
        score_diff = candidate_test_metrics.get("objective_score", 0.0) - baseline.get("baseline_objective_score", 0.0)

        if pnl_diff > 0 and score_diff > 0:
            comparison_verdict = "IMPROVED"
        elif pnl_diff < 0 or score_diff < 0:
            comparison_verdict = "WORSE"
        else:
            comparison_verdict = "NO_MATERIAL_CHANGE"

        return {
            "comparison_verdict": comparison_verdict,
            "pnl_diff": round(pnl_diff, 2),
            "win_rate_diff_pct": round(win_rate_diff, 2),
            "score_diff": round(score_diff, 2),
            "baseline": baseline,
            "candidate": candidate_test_metrics
        }
