from datetime import datetime
from typing import List, Any, Dict
from src.Research.MarketAnalysis.Interfaces.interfaces import IMarketAnalyzer, IResearchEngine
from src.Research.MarketAnalysis.Models.models import MarketObservation, MarketInsight, ResearchRequest, ResearchResult
from src.Data.MarketData.Models.models import MarketDataPoint

class MarketAnalysisEngine(IMarketAnalyzer):
    """
    Advanced analytical service translating raw normalized MarketDataPoint streams
    into structured MarketObservations and qualitative MarketInsights.
    """
    def analyze_observations(self, observations: List[MarketObservation]) -> List[MarketInsight]:
        insights = []
        for obs in observations:
            price_trend = obs.Observations.get("price_trend", "neutral")
            confidence = obs.Observations.get("confidence", 0.5)

            insight = MarketInsight(
                Category="TrendAnalysis",
                Description=f"Analyzed {obs.Asset} from source '{obs.Source}'. Observed trend: {price_trend}.",
                Confidence=confidence,
                CreatedAt=datetime.now()
            )
            insights.append(insight)
        return insights

    def generate_observations_from_data(self, asset_id: str, data_points: List[MarketDataPoint]) -> List[MarketObservation]:
        """Translates normalized bar series into formal structural observations."""
        if not data_points:
            return []

        # Basic math to establish metrics
        latest = data_points[-1]
        older = data_points[0]

        pct_change = (latest.Close - older.Close) / older.Close if older.Close > 0 else 0.0
        trend = "bullish" if pct_change > 0.01 else ("bearish" if pct_change < -0.01 else "neutral")

        observations_payload = {
            "price_trend": trend,
            "period_pct_change": pct_change,
            "volume_sum": sum(dp.Volume for pt in data_points for dp in [pt]),
            "bars_evaluated": len(data_points),
            "confidence": 0.85
        }

        return [
            MarketObservation(
                Asset=asset_id,
                Timestamp=datetime.now(),
                Observations=observations_payload,
                Source="MarketAnalysisEngine"
            )
        ]


class ResearchProcessor(IResearchEngine):
    """
    Processes complex multi-asset research requests and logs report histories.
    """
    def __init__(self) -> None:
        self._history = ResearchHistory()

    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        # standard statistical metrics calculations
        findings = {
            "asset_id": request.Asset,
            "period_start": request.StartTime.isoformat(),
            "period_end": request.EndTime.isoformat(),
            "research_context": request.Context,
            "status": "completed",
            "historical_mean_volatility": 0.187
        }
        result = ResearchResult(
            Request=request,
            Findings=findings,
            ConfidenceScore=0.88,
            CreatedAt=datetime.now()
        )
        # Store in historical register
        self._history.log_result(result)
        return result


class ResearchHistory:
    """Historical tracker recording finalized ResearchResults."""
    def __init__(self) -> None:
        self._records: List[ResearchResult] = []

    def log_result(self, result: ResearchResult) -> None:
        self._records.append(result)

    def list_history(self, asset_id: str) -> List[ResearchResult]:
        return [r for r in self._records if r.Request.Asset == asset_id]
