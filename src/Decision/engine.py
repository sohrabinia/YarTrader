from datetime import datetime
import uuid
from typing import Dict, List
from src.Core.entities import DecisionReport, RiskParameters
from src.Core.interfaces import IDecisionService, IRepository, IRiskEvaluator
from src.Strategy.base import BaseAssetScoringStrategy

class AutonomousDecisionEngine(IDecisionService):
    """
    Autonomous decision engine responsible for performing financial intelligence recommendations.
    Combines passive asset scoring with risk evaluation to produce optimal risk-adjusted allocation models.
    """
    def __init__(
        self,
        repository: IRepository,
        strategy: BaseAssetScoringStrategy,
        risk_evaluator: IRiskEvaluator
    ) -> None:
        self._repository = repository
        self._strategy = strategy
        self._risk_evaluator = risk_evaluator

    def analyze_market_and_recommend(self, risk_params: RiskParameters) -> DecisionReport:
        """
        Analyzes the market assets, ranks them via strategy scores, and constructs a safe,
        optimized target portfolio allocation report.
        """
        assets = self._repository.list_assets()
        asset_market_data = {}

        # Load historical prices for each asset (using last 10 points)
        now = datetime.now()
        for asset in assets:
            # Gather prices
            data_points = self._repository.get_historical_market_data(
                asset.symbol,
                datetime(2000, 1, 1),
                now
            )
            asset_market_data[asset.symbol] = data_points

        # Calculate scores
        scores = self._strategy.score_assets(asset_market_data)

        # Filter active assets and sort by score
        active_scores = {
            sym: score for sym, score in scores.items()
            if self._repository.get_asset(sym) and self._repository.get_asset(sym).is_active
        }

        # Form a target allocation using normalized score rankings
        total_score = sum(active_scores.values())
        proposed_weights = {}

        if total_score > 0:
            for sym, score in active_scores.items():
                proposed_weights[sym] = score / total_score
        else:
            # Uniform weights
            num_assets = len(active_scores)
            if num_assets > 0:
                proposed_weights = {sym: 1.0 / num_assets for sym in active_scores}

        # Apply Risk Limit Verification & Adjust if needed
        is_safe = self._risk_evaluator.check_allocation_safety(proposed_weights, risk_params)

        if not is_safe:
            # Iterative capping and redistribution to respect single-asset limits
            max_limit = risk_params.max_single_asset_exposure
            adjusted = proposed_weights.copy()

            for _ in range(len(adjusted)):
                exceeded_symbols = [sym for sym, w in adjusted.items() if w > max_limit]
                if not exceeded_symbols:
                    break

                excess = 0.0
                for sym in exceeded_symbols:
                    excess += adjusted[sym] - max_limit
                    adjusted[sym] = max_limit

                non_exceeded_symbols = [sym for sym, w in adjusted.items() if w < max_limit]
                if non_exceeded_symbols:
                    distribution_sum = sum(adjusted[sym] for sym in non_exceeded_symbols)
                    if distribution_sum > 0:
                        for sym in non_exceeded_symbols:
                            adjusted[sym] += excess * (adjusted[sym] / distribution_sum)
                    else:
                        share = excess / len(non_exceeded_symbols)
                        for sym in non_exceeded_symbols:
                            adjusted[sym] += share
                else:
                    break
            proposed_weights = adjusted

        # Confirm safety after adjustment
        final_vol = self._risk_evaluator.calculate_portfolio_volatility(proposed_weights)
        is_safe_after = self._risk_evaluator.check_allocation_safety(proposed_weights, risk_params)
        risk_evaluation_status = (
            f"PASSED (Expected Volatility: {final_vol:.4f})"
            if is_safe_after else f"WARNING: Failed limits check (Expected Volatility: {final_vol:.4f})"
        )

        decision_id = str(uuid.uuid4())
        reasoning = (
            f"Optimized portfolio recommendation generated via '{self._strategy.name}' strategy. "
            f"Total evaluated assets: {len(active_scores)}."
        )

        return DecisionReport(
            decision_id=decision_id,
            target_weights=proposed_weights,
            reasoning=reasoning,
            risk_evaluation=risk_evaluation_status,
            timestamp=datetime.now()
        )
