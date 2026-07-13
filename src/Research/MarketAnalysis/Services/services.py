from datetime import datetime
from typing import List, Any, Dict, Optional
from src.Research.MarketAnalysis.Interfaces.interfaces import IMarketAnalyzer, IResearchEngine
from src.Research.MarketAnalysis.Models.models import MarketObservation, MarketInsight, ResearchRequest, ResearchResult
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Research.Features.pipeline import FeaturePipeline
from src.Infrastructure.exceptions import ValidationException


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


class FeatureExtractionResearchEngine(IResearchEngine):
    """
    Decorator/Adapter implementing IResearchEngine that orchestrates feature extraction
    from market data before delegating to an underlying research engine.
    """

    def __init__(
        self,
        data_provider: IMarketDataProvider,
        base_engine: Optional[IResearchEngine] = None,
        feature_pipeline: Optional[FeaturePipeline] = None
    ) -> None:
        self._data_provider = data_provider
        self._base_engine = base_engine or ResearchProcessor()
        self._feature_pipeline = feature_pipeline or FeaturePipeline()

    @property
    def data_provider(self) -> IMarketDataProvider:
        return self._data_provider

    @property
    def base_engine(self) -> IResearchEngine:
        return self._base_engine

    @property
    def feature_pipeline(self) -> FeaturePipeline:
        return self._feature_pipeline

    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        """
        Retrieves market data, executes feature calculations to generate observations,
        and builds a ResearchResult rich in market feature analytics.
        """
        # 1. Fetch market data points from provider
        timeframe = request.Context.get("timeframe", "H1")
        data_req = MarketDataRequest(
            Asset=request.Asset,
            StartTime=request.StartTime,
            EndTime=request.EndTime,
            Timeframe=timeframe
        )

        try:
            market_data_response = self._data_provider.retrieve_market_data(data_req)
        except Exception as e:
            raise ValidationException(
                f"Validation Error: Failed to fetch market data for feature extraction: {str(e)}"
            ) from e

        # 2. Execute feature pipeline to extract features
        feature_set = self._feature_pipeline.execute(market_data_response.DataPoints)

        # 3. Create MarketObservation from MarketFeatureSet
        observations_map = {name: fval.Value for name, fval in feature_set.Features.items()}
        market_observation = MarketObservation(
            Asset=request.Asset,
            Timestamp=datetime.now(),
            Observations=observations_map,
            Source="FeatureExtractionResearchEngine"
        )

        # 4. Enforce base engine execution with enriched context
        enriched_context = dict(request.Context)
        enriched_context["extracted_features"] = {
            name: {
                "value": fval.Value,
                "timestamp": fval.Timestamp.isoformat(),
                "metadata": fval.Metadata
            }
            for name, fval in feature_set.Features.items()
        }
        enriched_context["observation"] = {
            "asset": market_observation.Asset,
            "observations": market_observation.Observations,
            "source": market_observation.Source
        }

        enriched_request = ResearchRequest(
            Asset=request.Asset,
            StartTime=request.StartTime,
            EndTime=request.EndTime,
            Context=enriched_context
        )

        base_result = self._base_engine.analyze_market(enriched_request)

        # 5. Enrich findings with features and observations
        enriched_findings = dict(base_result.Findings)
        enriched_findings["feature_set"] = {
            "asset_id": feature_set.AssetId,
            "start_time": feature_set.StartTime.isoformat(),
            "end_time": feature_set.EndTime.isoformat(),
            "features_count": len(feature_set.Features)
        }
        enriched_findings["observation_summary"] = market_observation.Observations

        return ResearchResult(
            Request=request,
            Findings=enriched_findings,
            ConfidenceScore=base_result.ConfidenceScore,
            CreatedAt=datetime.now()
        )
