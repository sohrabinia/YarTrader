from typing import Dict, Optional
from src.Strategy.Interfaces.interfaces import IStrategyRegistry
from src.Strategy.Models.models import StrategyDefinition

class StrategyRegistry(IStrategyRegistry):
    """In-memory registry implementation to keep track of approved StrategyDefinitions."""
    def __init__(self) -> None:
        self._store: Dict[str, StrategyDefinition] = {}

    def register_strategy(self, definition: StrategyDefinition) -> None:
        self._store[definition.Id] = definition

    def get_strategy(self, strategy_id: str) -> Optional[StrategyDefinition]:
        return self._store.get(strategy_id)
