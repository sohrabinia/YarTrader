from typing import List, Dict
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchRepository
from src.Research.MarketAnalysis.Models.models import ResearchResult


class InMemoryResearchRepository(IResearchRepository):
    """
    High-performance in-memory persistent storage for ResearchResult outputs.
    Fully compliant with IResearchRepository interface.
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[ResearchResult]] = {}

    def store_research_result(self, result: ResearchResult) -> None:
        asset = result.Request.Asset
        if asset not in self._store:
            self._store[asset] = []
        self._store[asset].append(result)

    def get_research_results(self, asset: str) -> List[ResearchResult]:
        return self._store.get(asset, [])
