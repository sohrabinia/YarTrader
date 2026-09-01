import uuid
import logging
from typing import Dict, Any, List, Optional

from src.Application.Research.optimization.parameter_space import ParameterSpace
from src.Application.Research.optimization.dataset_splitter import DatasetSplitter
from src.Application.Research.optimization.grid_search import GridSearchEngine
from src.Application.Research.optimization.objective import ObjectiveEvaluator
from src.Application.Research.optimization.cost_model import CostModel
from src.Application.Research.optimization.walk_forward import WalkForwardOptimizer
from src.Application.Research.optimization.overfitting import OverfittingDiagnostics
from src.Application.Research.optimization.baseline import BaselineEvaluator
from src.Application.Research.optimization.provenance import ExperimentProvenance
from src.Application.Research.optimization.report import ResearchReportGenerator

logger = logging.getLogger("ResearchOptimizationRunner")

class ResearchOptimizationRunner:
    """
    High-level Research Optimization Runner for YarTrader.
    Executes isolated parameter grid-searches, walk-forward optimization, overfitting diagnostics, and baseline comparisons.
    Enforces strict safety boundaries: NEVER invokes live MT5 orders, NEVER modifies production configuration, and NEVER auto-promotes candidates to production.
    """
    def __init__(self, commit_sha: str = "5b7e817d44f43131a8ce68193a36bcbf2fdbd0fc") -> None:
        self.commit_sha = commit_sha
        self.grid_engine = GridSearchEngine()
        self.wfo_engine = WalkForwardOptimizer()
        self.baseline_evaluator = BaselineEvaluator()

    def run_full_research_pipeline(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        parameter_space: ParameterSpace,
        initial_balance: float = 10000.0,
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20
    ) -> Dict[str, Any]:
        # 1. Dataset Splitting
        split_res = DatasetSplitter.split_chronological(candles, train_ratio, val_ratio, test_ratio)
        dataset_hash = split_res["hash"]
        train_set = split_res["train"]
        val_set = split_res["validation"]
        test_set = split_res["test"]

        # 2. Frozen Baseline Evaluation
        baseline_res = self.baseline_evaluator.evaluate_frozen_baseline(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            initial_balance=initial_balance,
            commit_sha=self.commit_sha
        )

        # 3. Train Optimization via Grid Search
        train_opt_results = self.grid_engine.run_optimization(
            symbol=symbol,
            timeframe=timeframe,
            candles=train_set,
            parameter_space=parameter_space,
            initial_balance=initial_balance
        )

        best_train_candidate = train_opt_results[0] if train_opt_results else {}

        # 4. Validation Evaluation
        val_backtest = self.grid_engine.backtest_engine.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            candles=val_set,
            initial_balance=initial_balance
        )
        val_metrics = ObjectiveEvaluator.calculate_metrics(val_backtest.get("closed_trades", []), initial_balance)

        # 5. Out-of-Sample Test Evaluation
        test_backtest = self.grid_engine.backtest_engine.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            candles=test_set,
            initial_balance=initial_balance
        )
        test_metrics = ObjectiveEvaluator.calculate_metrics(test_backtest.get("closed_trades", []), initial_balance)

        # 6. Overfitting Diagnostics
        overfitting_res = OverfittingDiagnostics.evaluate_candidate_robustness(
            candidate=best_train_candidate,
            val_metrics=val_metrics,
            test_metrics=test_metrics
        )

        # 7. Walk-Forward Optimization
        wfo_res = self.wfo_engine.run_walk_forward(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            parameter_space=parameter_space,
            initial_balance=initial_balance
        )

        # 8. Baseline Comparison
        comparison_res = BaselineEvaluator.compare_candidate_to_baseline(baseline_res, test_metrics)

        # 9. Provenance Recording
        exp_id = f"EXP-OPT-{symbol.upper()}-{timeframe.upper()}-{uuid.uuid4().hex[:8]}"
        split_def = {"train": train_ratio, "val": val_ratio, "test": test_ratio}

        provenance_rec = ExperimentProvenance.create_provenance_record(
            experiment_id=exp_id,
            commit_sha=self.commit_sha,
            symbol=symbol,
            timeframe=timeframe,
            dataset_hash=dataset_hash,
            split_definition=split_def,
            configuration=best_train_candidate.get("configuration", {}),
            metrics=test_metrics,
            objective_score=test_metrics.get("objective_score", 0.0),
            overfitting_status=overfitting_res["status"]
        )

        # 10. Generate Reports
        markdown_report = ResearchReportGenerator.generate_markdown_report(
            experiment_provenance=provenance_rec,
            baseline_comparison=comparison_res,
            walk_forward_summary=wfo_res,
            overfitting_summary=overfitting_res
        )

        return {
            "experiment_id": exp_id,
            "status": "COMPLETED",
            "provenance": provenance_rec,
            "baseline": baseline_res,
            "best_train_candidate": best_train_candidate,
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
            "overfitting": overfitting_res,
            "walk_forward": wfo_res,
            "baseline_comparison": comparison_res,
            "markdown_report": markdown_report,
            "promotion_status": "RESEARCH_ONLY_NO_AUTO_PROMOTION"
        }
