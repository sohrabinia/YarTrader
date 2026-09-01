from typing import Dict, Any, List
from src.Application.Research.optimization.grid_search import GridSearchEngine
from src.Application.Research.optimization.objective import ObjectiveEvaluator

class WalkForwardOptimizer:
    """
    Chronological Walk-Forward Optimization (WFO) engine.
    Constructs rolling Train/Validation windows, advances chronologically, and aggregates unseen OOS metrics.
    Guarantees zero future look-ahead leakage.
    """
    def __init__(self, window_size_bars: int = 200, step_size_bars: int = 50) -> None:
        self.window_size_bars = window_size_bars
        self.step_size_bars = step_size_bars
        self.grid_engine = GridSearchEngine()

    def run_walk_forward(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        parameter_space: Any,
        initial_balance: float = 10000.0
    ) -> Dict[str, Any]:
        total_bars = len(candles)
        if total_bars < self.window_size_bars + self.step_size_bars:
            return {
                "status": "INSUFFICIENT_DATA",
                "windows_evaluated": 0,
                "aggregate_metrics": {},
                "window_results": []
            }

        window_results = []
        current_start = 0

        window_index = 1
        while current_start + self.window_size_bars + self.step_size_bars <= total_bars:
            train_start = current_start
            train_end = current_start + self.window_size_bars
            oos_start = train_end
            oos_end = min(total_bars, oos_start + self.step_size_bars)

            train_candles = candles[train_start:train_end]
            oos_candles = candles[oos_start:oos_end]

            # 1. Optimize on Train window
            opt_results = self.grid_engine.run_optimization(
                symbol=symbol,
                timeframe=timeframe,
                candles=train_candles,
                parameter_space=parameter_space,
                initial_balance=initial_balance
            )

            best_candidate = opt_results[0] if opt_results else {}

            # 2. Evaluate selected best candidate on unseen OOS window
            oos_backtest = self.grid_engine.backtest_engine.run_backtest(
                symbol=symbol,
                timeframe=timeframe,
                candles=oos_candles,
                initial_balance=initial_balance
            )

            oos_closed = oos_backtest.get("closed_trades", [])
            oos_metrics = ObjectiveEvaluator.calculate_metrics(oos_closed, initial_balance=initial_balance)

            window_results.append({
                "window_index": window_index,
                "train_bars": len(train_candles),
                "oos_bars": len(oos_candles),
                "best_train_config": best_candidate.get("configuration", {}),
                "train_objective_score": best_candidate.get("objective_score", 0.0),
                "oos_trade_count": oos_metrics["total_trades"],
                "oos_net_pnl": oos_metrics["net_pnl"],
                "oos_win_rate_pct": oos_metrics["win_rate_pct"],
                "oos_profit_factor": oos_metrics["profit_factor"],
                "oos_max_drawdown_pct": oos_metrics["max_drawdown_pct"],
                "oos_objective_score": oos_metrics["objective_score"]
            })

            current_start += self.step_size_bars
            window_index += 1

        # Aggregate Walk-Forward performance across all windows
        total_oos_trades = sum(w["oos_trade_count"] for w in window_results)
        total_oos_pnl = sum(w["oos_net_pnl"] for w in window_results)
        profitable_windows = sum(1 for w in window_results if w["oos_net_pnl"] > 0)
        profitability_ratio = (profitable_windows / len(window_results)) * 100.0 if window_results else 0.0

        return {
            "status": "SUCCESS",
            "windows_evaluated": len(window_results),
            "profitable_windows": profitable_windows,
            "profitability_ratio_pct": round(profitability_ratio, 2),
            "total_oos_trades": total_oos_trades,
            "aggregate_oos_net_pnl": round(total_oos_pnl, 2),
            "window_results": window_results
        }
