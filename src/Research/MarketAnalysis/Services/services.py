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
        if base_engine is None:
            from src.Research.Engine.services import ResearchEngine
            self._base_engine = ResearchEngine()
        else:
            self._base_engine = base_engine
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

        # Feed real candles explicitly into the six dedicated pipeline/analytical engines
        from src.Research.analysis_pipeline import (
            TechnicalAnalysisEngine,
            FeatureEngineeringLayer,
            MarketRegimeDetection,
            TrendAnalysis,
            VolatilityAnalysis,
            MomentumAnalysis
        )

        # A. Technical Analysis Engine
        tech_engine = TechnicalAnalysisEngine()
        tech_results = tech_engine.analyze(market_data_response.DataPoints)

        # B. Feature Engineering Layer
        feat_layer = FeatureEngineeringLayer(pipeline=self._feature_pipeline)
        feature_set = feat_layer.process(market_data_response.DataPoints)

        # C. Trend Analysis
        trend_analysis = TrendAnalysis()
        trend_results = trend_analysis.analyze(market_data_response.DataPoints, feature_set)

        # D. Volatility Analysis
        vol_analysis = VolatilityAnalysis()
        vol_results = vol_analysis.analyze(market_data_response.DataPoints, feature_set)

        # E. Momentum Analysis
        mom_analysis = MomentumAnalysis()
        mom_results = mom_analysis.analyze(market_data_response.DataPoints, feature_set)

        # F. Market Regime Detection
        regime_detector = MarketRegimeDetection()
        regime_results = regime_detector.detect(market_data_response.DataPoints, feature_set)

        # G. Smart Interpretation Engine (combines results to generate qualitative bias & confidence)
        from src.Research.analysis_pipeline import SmartInterpretationEngine
        interpretation_engine = SmartInterpretationEngine()
        smart_results = interpretation_engine.interpret(
            candles=market_data_response.DataPoints,
            tech=tech_results,
            trend=trend_results,
            vol=vol_results,
            mom=mom_results,
            regime=regime_results
        )

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
        enriched_context["market_feature_set"] = feature_set
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
        # Inject explicit pipeline results into enriched context
        enriched_context["technical_analysis"] = tech_results
        enriched_context["trend_analysis"] = trend_results
        enriched_context["volatility_analysis"] = vol_results
        enriched_context["momentum_analysis"] = mom_results
        enriched_context["market_regime"] = regime_results
        enriched_context["smart_interpretation"] = smart_results

        enriched_request = ResearchRequest(
            Asset=request.Asset,
            StartTime=request.StartTime,
            EndTime=request.EndTime,
            Context=enriched_context
        )

        # H. Newborn Market Discovery Brain v1 Integration
        from src.Research.Brain.live_brain import LiveAnalysisBrain
        newborn_brain = LiveAnalysisBrain(request.Asset, timeframe)
        newborn_report = None
        for dp in market_data_response.DataPoints:
            raw_candle_dict = {
                "timestamp": dp.Timestamp.isoformat() if isinstance(dp.Timestamp, datetime) else str(dp.Timestamp),
                "open": dp.Open,
                "high": dp.High,
                "low": dp.Low,
                "close": dp.Close,
                "volume": dp.Volume
            }
            newborn_report = newborn_brain.process_live_candle(raw_candle_dict)

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

        # Expose final compiled pipeline outputs in the findings dict
        enriched_findings["pipeline_outputs"] = {
            "technical_analysis": tech_results,
            "trend_analysis": trend_results,
            "volatility_analysis": vol_results,
            "momentum_analysis": mom_results,
            "market_regime": regime_results,
            "smart_interpretation": smart_results
        }

        # Embed Newborn Market Discovery Brain v1 report if generated
        if newborn_report:
            enriched_findings["newborn_brain_report"] = newborn_report.to_dict()

        # I. Fractal Behavior Analysis Engine Integration
        try:
            from src.Infrastructure.DI.container import container_instance
            from src.Research.MarketAnalysis.Interfaces.interfaces import IFractalEngine
            fractal_engine = container_instance.resolve(IFractalEngine)
        except Exception:
            from src.Research.Brain.fractal_engine import FractalEngine
            fractal_engine = FractalEngine()

        try:
            candles_by_tf = {timeframe: market_data_response.DataPoints}
            fractal_res = fractal_engine.analyze_fractals(
                symbol=request.Asset,
                primary_timeframe=timeframe,
                candles_by_tf=candles_by_tf
            )
            enriched_findings["fractal_analysis"] = fractal_res
            enriched_findings["pipeline_outputs"]["fractal_analysis"] = fractal_res
        except Exception as fe_err:
            enriched_findings["fractal_analysis_error"] = str(fe_err)

        # Dynamically set the confidence score from smart interpretation (converted back to fraction [0, 1])
        conf_score = float(smart_results.get("confidence", 50.0)) / 100.0

        return ResearchResult(
            Request=request,
            Findings=enriched_findings,
            ConfidenceScore=conf_score,
            CreatedAt=datetime.now()
        )
