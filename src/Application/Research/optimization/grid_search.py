import uuid
import logging
from typing import Dict, Any, List, Optional
from src.Application.Research.optimization.parameter_space import ParameterSpace
from src.Application.Research.optimization.dataset_splitter import DatasetSplitter
from src.Application.Research.optimization.objective import ObjectiveEvaluator
from src.Application.Research.optimization.cost_model import CostModel
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

logger = logging.getLogger("GridSearchOptimizer")

class GridSearchEngine:
    """
    Deterministic grid search optimization engine for YarTrader Research.
    Evaluates parameter configurations against Train data without mutating global Trading Core state.
    Includes failure isolation so a single configuration error does not terminate the optimization run.
    """
    def __init__(self, cost_model: Optional[CostModel] = None) -> None:
        self.cost_model = cost_model or CostModel()
        self.backtest_engine = BacktestAndLearningEngine()

    def run_optimization(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        parameter_space: ParameterSpace,
        initial_balance: float = 10000.0
    ) -> List[Dict[str, Any]]:
        combinations = parameter_space.generate_cartesian_product()
        dataset_hash = DatasetSplitter.calculate_dataset_hash(candles)
        results = []

        for idx, config in enumerate(combinations, 1):
            exp_id = f"exp-{symbol.upper()}-{timeframe.upper()}-{idx:03d}-{hashlib_config(config)}"
            try:
                # Run deterministic backtest
                res = self.backtest_engine.run_backtest(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles,
                    initial_balance=initial_balance
                )

                closed_trades = res.get("closed_trades", [])
                metrics = ObjectiveEvaluator.calculate_metrics(closed_trades, initial_balance=initial_balance)

                results.append({
                    "experiment_id": exp_id,
                    "configuration": config,
                    "dataset_hash": dataset_hash,
                    "trade_count": metrics["total_trades"],
                    "net_pnl": metrics["net_pnl"],
                    "win_rate_pct": metrics["win_rate_pct"],
                    "profit_factor": metrics["profit_factor"],
                    "expectancy": metrics["expectancy"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "avg_r": metrics["avg_r"],
                    "objective_score": metrics["objective_score"],
                    "status": "SUCCESS",
                    "error": None
                })
            except Exception as e:
                logger.error(f"Experiment {exp_id} failed: {str(e)}")
                results.append({
                    "experiment_id": exp_id,
                    "configuration": config,
                    "dataset_hash": dataset_hash,
                    "trade_count": 0,
                    "net_pnl": 0.0,
                    "win_rate_pct": 0.0,
                    "objective_score": -999.0,
                    "status": "FAILED",
                    "error": str(e)
                })

        # Rank results by objective score descending
        results.sort(key=lambda x: x["objective_score"], reverse=True)
        return results

def hashlib_config(config: Dict[str, Any]) -> str:
    import hashlib
    import json
    raw = json.dumps(config, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:6]
