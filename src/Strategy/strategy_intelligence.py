from datetime import datetime
from typing import Dict, List, Optional
from src.Strategy.Interfaces.interfaces import IStrategyEngine, IStrategyEvaluator, IStrategyRegistry
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyDefinition


class StrategyLifecycleManager:
    """
    Manages the end-to-end lifecycle, activation states, and validation runs
    of financial strategy concept candidates.
    """

    def __init__(self, registry: IStrategyRegistry) -> None:
        self.registry = registry
        self._active_strategy_ids: List[str] = []

    def activate_strategy(self, strategy_id: str) -> None:
        """Transitions strategy status to Active."""
        definition = self.registry.get_strategy(strategy_id)
        if definition:
            if strategy_id not in self._active_strategy_ids:
                self._active_strategy_ids.append(strategy_id)

    def deactivate_strategy(self, strategy_id: str) -> None:
        """Deactivates and removes strategy from runtime pool."""
        if strategy_id in self._active_strategy_ids:
            self._active_strategy_ids.remove(strategy_id)

    def get_active_strategy_ids(self) -> List[str]:
        return self._active_strategy_ids


class StrategyEngine(IStrategyEngine):
    """
    Production-grade strategy execution engine coordinating evaluations and lifecycle states.
    Strictly calculates descriptive rankings; produces zero actual buy/sell transaction orders.
    """

    def __init__(self, evaluator: IStrategyEvaluator, lifecycle_manager: StrategyLifecycleManager) -> None:
        self.evaluator = evaluator
        self.lifecycle_manager = lifecycle_manager

    def process_candidate(self, candidate: StrategyCandidate) -> StrategyEvaluation:
        # Check active status
        active_ids = self.lifecycle_manager.get_active_strategy_ids()

        evaluation = self.evaluator.evaluate(candidate)

        # If strategy concept is active, rankings are confirmed, else marked pending
        if candidate.Id in active_ids:
            # Reconstruct evaluation status to represent runtime confirmation
            from dataclasses import replace
            candidate_updated = replace(candidate, EvaluationStatus="Approved")
            evaluation = replace(evaluation, EvaluationNotes=f"Active Strategy Processed: {evaluation.EvaluationNotes}")

        return evaluation
