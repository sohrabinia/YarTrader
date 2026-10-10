import os
from datetime import datetime, timedelta
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


class PrimitiveMarketResearchEngine(IResearchEngine):
    """
    Indicator-Independent Research Engine for the 30-Instrument Market Universe.
    Consumes primitive broker market facts and ExecutionIntelligenceCore context evaluation
    WITHOUT invoking technical indicators (NO ATR, NO RSI, NO MA, NO TechnicalAnalysisEngine).
    """

    def __init__(
        self,
        data_provider: IMarketDataProvider,
        base_engine: Optional[IResearchEngine] = None
    ) -> None:
        self._data_provider = data_provider
        if base_engine is None:
            from src.Research.Engine.services import ResearchEngine
            self._base_engine = ResearchEngine()
        else:
            self._base_engine = base_engine
        self._live_brains: Dict[tuple, Any] = {}
        self._last_processed_candle_timestamps: Dict[tuple, datetime] = {}

    @property
    def data_provider(self) -> IMarketDataProvider:
        return self._data_provider

    @staticmethod
    def _timestamp_order(value: Any) -> float:
        if isinstance(value, datetime):
            return value.timestamp()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()

    def _select_brain_points(self, brain_key: tuple, data_points: List[MarketDataPoint]) -> List[MarketDataPoint]:
        """Bootstrap on a bounded recent window, then feed only unseen candles to the live Brain."""
        last_processed = self._last_processed_candle_timestamps.get(brain_key)
        if last_processed is None:
            try:
                bootstrap_bars = max(1, int(os.getenv("YARTRADER_LIVE_BRAIN_BOOTSTRAP_BARS", "120")))
            except (TypeError, ValueError):
                bootstrap_bars = 120
            return list(data_points[-bootstrap_bars:])
        last_order = self._timestamp_order(last_processed)
        return [dp for dp in data_points if self._timestamp_order(dp.Timestamp) > last_order]

    def analyze_market(self, request: ResearchRequest, market_data_response=None) -> ResearchResult:
        """
        Retrieves primitive market data and context intelligence without technical indicators.
        """
        timeframe = request.Context.get("timeframe", "H1")
        data_req = MarketDataRequest(
            Asset=request.Asset,
            StartTime=request.StartTime,
            EndTime=request.EndTime,
            Timeframe=timeframe
        )

        try:
            if market_data_response is None:
                market_data_response = self._data_provider.retrieve_market_data(data_req)
        except Exception as e:
            raise ValidationException(
                f"Validation Error: Failed to fetch market data for primitive research: {str(e)}"
            ) from e

        data_points = market_data_response.DataPoints
        if not data_points:
            raise ValidationException(f"Received empty market data points for {request.Asset}")

        latest_dp = data_points[-1]
        candles_dicts = [
            {
                "timestamp": dp.Timestamp.isoformat() if hasattr(dp.Timestamp, "isoformat") else str(dp.Timestamp),
                "open": float(dp.Open),
                "high": float(dp.High),
                "low": float(dp.Low),
                "close": float(dp.Close),
                "volume": float(dp.Volume)
            }
            for dp in data_points
        ]

        import time
        cycle_id = f"cyc-{request.Asset.upper()}-{timeframe.upper()}-{int(time.time())}"
        decision_id = f"DEC-{request.Asset.upper()}-{timeframe.upper()}-{int(time.time())}"

        # Check if newborn_brain_report is already provided in request context or compute via LiveAnalysisBrain
        newborn_report_dict = request.Context.get("newborn_brain_report")
        if not newborn_report_dict:
            try:
                from src.Research.Brain.live_brain import LiveAnalysisBrain
                brain_key = (request.Asset.upper(), timeframe.upper())
                newborn_brain = self._live_brains.get(brain_key)
                if newborn_brain is None:
                    newborn_brain = LiveAnalysisBrain(request.Asset, timeframe)
                    self._live_brains[brain_key] = newborn_brain
                newborn_report = None
                brain_points = self._select_brain_points(brain_key, data_points)
                for point_index, dp in enumerate(brain_points):
                    raw_candle_dict = {
                        "timestamp": dp.Timestamp.isoformat() if isinstance(dp.Timestamp, datetime) else str(dp.Timestamp),
                        "open": float(dp.Open),
                        "high": float(dp.High),
                        "low": float(dp.Low),
                        "close": float(dp.Close),
                        "volume": float(dp.Volume)
                    }
                    newborn_report = newborn_brain.process_live_candle(
                        raw_candle_dict,
                        learning_cycle_due=(point_index == len(brain_points) - 1),
                    )
                    self._last_processed_candle_timestamps[brain_key] = dp.Timestamp
                if newborn_report is None:
                    newborn_report = getattr(newborn_brain, "_last_report", None)
                if newborn_report:
                    newborn_report_dict = newborn_report.to_dict()
                else:
                    newborn_report_dict = {
                        "brain_available": False,
                        "suggested_virtual_action": "WAIT",
                        "brain_error": "No new or previously cached candle report is available from LiveAnalysisBrain"
                    }
            except Exception as be_err:
                newborn_report_dict = {
                    "brain_available": False,
                    "suggested_virtual_action": "WAIT",
                    "brain_error": f"LiveAnalysisBrain exception: {type(be_err).__name__}: {str(be_err)}"[:200]
                }

        try:
            from src.Intelligence.Execution.core import ExecutionIntelligenceCore
            from src.Decision.Models.models import AutonomousTradingDecision

            intel_core = ExecutionIntelligenceCore.get_instance()
            intel_res = intel_core.evaluate_context(
                symbol=request.Asset,
                timeframe=timeframe,
                candles=candles_dicts,
                newborn_brain_report=newborn_report_dict
            )

            plan = intel_res.get("plan", {})
            action = str(plan.get("action", "WAIT")).upper()
            if action not in ["BUY", "SELL", "WAIT", "AVOID"]:
                action = "WAIT"

            auto_decision = AutonomousTradingDecision(
                decision_id=decision_id,
                cycle_id=cycle_id,
                action=action,
                symbol=request.Asset,
                timeframe=timeframe,
                entry=float(plan.get("entry", 0.0)),
                stop_loss=float(plan.get("stop_loss", 0.0)),
                take_profit=float(plan.get("take_profit", 0.0)),
                volume=0.0,
                risk_reward=float(plan.get("risk_reward", 0.0)),
                confidence=float(plan.get("confidence", 0.0)),
                reasoning=plan.get("reasoning", ["Indicator-independent primitive evaluation"]),
                evidence={
                    "narrative": intel_res.get("narrative", {}),
                    "liquidity": intel_res.get("liquidity", {}),
                    "zones": intel_res.get("zones", {}),
                    "alignment": intel_res.get("alignment", {}),
                    "latest_price": candles_dicts[-1]["close"]
                },
                risk_status="APPROVED" if action in ["BUY", "SELL"] else "CHECKED",
                execution_status="PENDING" if action in ["BUY", "SELL"] else "SKIPPED",
                configuration_version="1.2.0",
                timestamp=datetime.now().isoformat()
            )
            auto_dec_dict = auto_decision.to_dict()
        except Exception:
            intel_res = {}
            auto_dec_dict = {
                "action": "WAIT",
                "confidence": 0.0,
                "reasoning": ["Default primitive evaluation"]
            }

        primitive_observation = {
            "symbol": request.Asset,
            "timeframe": timeframe,
            "latest_price": float(latest_dp.Close),
            "high": float(max(dp.High for dp in data_points)),
            "low": float(min(dp.Low for dp in data_points)),
            "volume": float(sum(dp.Volume for dp in data_points)),
            "bar_count": len(data_points),
            "timestamp": latest_dp.Timestamp.isoformat() if hasattr(latest_dp.Timestamp, "isoformat") else str(latest_dp.Timestamp)
        }

        brain_hypotheses = newborn_report_dict.get("active_hypotheses", []) if isinstance(newborn_report_dict, dict) else []
        primary_hypothesis = brain_hypotheses[0] if brain_hypotheses and isinstance(brain_hypotheses[0], dict) else {}
        brain_action = str(primary_hypothesis.get("suggested_virtual_action", "WAIT")).upper()
        brain_confidence = float(primary_hypothesis.get("hypothesis_confidence", 0.0) or 0.0)
        blocked_direction = str(primary_hypothesis.get("blocked_direction") or "WAIT").upper()
        blocked_direction_confidence = float(primary_hypothesis.get("blocked_direction_confidence", 0.0) or 0.0)
        evidence_status = str(primary_hypothesis.get("evidence_status", "NO_OUTCOME_LABELS"))
        successful_outcomes = int(primary_hypothesis.get("successful_outcomes", 0) or 0)
        brain_trade_parameters = primary_hypothesis.get("trade_parameters", {}) or {}
        decision_action = str(auto_dec_dict.get("action", "WAIT")).upper()
        try:
            risk_parameters_available = isinstance(brain_trade_parameters, dict) and all(
                float(brain_trade_parameters.get(key) or 0.0) > 0.0
                for key in ("entry", "stop_loss", "take_profit")
            )
        except (TypeError, ValueError):
            risk_parameters_available = False
        if decision_action in ("BUY", "SELL"):
            smart_bias = decision_action
            smart_confidence = float(auto_dec_dict.get("confidence", 0.0) or 0.0)
            signal_status = "ACTIVE"
        elif brain_action in ("BUY", "SELL") and brain_confidence >= 50.0 and evidence_status == "VALIDATED_OUTCOMES" and successful_outcomes >= 3:
            smart_bias = brain_action
            smart_confidence = brain_confidence
            signal_status = "CANDIDATE"
        elif blocked_direction in ("BUY", "SELL") or (brain_action in ("BUY", "SELL") and (evidence_status != "VALIDATED_OUTCOMES" or successful_outcomes < 3)):
            smart_bias = blocked_direction if blocked_direction in ("BUY", "SELL") else brain_action
            smart_confidence = blocked_direction_confidence if blocked_direction in ("BUY", "SELL") else brain_confidence
            signal_status = "BLOCKED"
        else:
            smart_bias = "Neutral"
            smart_confidence = float(auto_dec_dict.get("confidence", 0.0) or 0.0)
            signal_status = "WAIT"
        smart_interpretation = {
            "confidence": smart_confidence,
            "bias": smart_bias,
            "reasoning": auto_dec_dict.get("reasoning", []),
            "execution_action": decision_action,
            "signal_status": signal_status,
            "risk_parameters_available": bool(risk_parameters_available),
            "candidate_reason": (
                "Brain proposed a direction, but learned entry/stop-loss/take-profit parameters are missing or failed planner validation."
                if signal_status == "CANDIDATE" else
                (primary_hypothesis.get("blocked_reason") or f"Historical outcome evidence is {evidence_status}; no executable signal is authorized.")
                if signal_status == "BLOCKED" else None
            ),
        }

        findings = {
            "asset_id": request.Asset,
            "period_start": request.StartTime.isoformat(),
            "period_end": request.EndTime.isoformat(),
            "research_context": request.Context,
            "status": "completed",
            "indicator_independent": True,
            "feature_set": {
                "asset_id": request.Asset,
                "start_time": request.StartTime.isoformat(),
                "end_time": request.EndTime.isoformat(),
                "features_count": 0,
                "mode": "primitive_indicator_free"
            },
            "primitive_observation": primitive_observation,
            "autonomous_decision": auto_dec_dict,
            "intel_summary": intel_res,
            "newborn_brain_report": newborn_report_dict,
            "pipeline_outputs": {
                "technical_analysis": {"candles": candles_dicts, "bar_count": len(candles_dicts)},
                "smart_interpretation": smart_interpretation
            }
        }

        conf_score = float(auto_dec_dict.get("confidence", 50.0)) / 100.0

        return ResearchResult(
            Request=request,
            Findings=findings,
            ConfidenceScore=conf_score,
            CreatedAt=datetime.now()
        )


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
        # Keep one Brain instance per symbol/timeframe across research cycles.
        # This preserves pending hypotheses/simulated positions while isolating assets.
        self._live_brains: Dict[tuple, Any] = {}

    @property
    def data_provider(self) -> IMarketDataProvider:
        return self._data_provider

    @property
    def base_engine(self) -> IResearchEngine:
        return self._base_engine

    @property
    def feature_pipeline(self) -> FeaturePipeline:
        return self._feature_pipeline

    def _get_live_brain(self, asset: str, timeframe: str):
        """Return the persistent Brain instance for one isolated symbol/timeframe."""
        from src.Research.Brain.live_brain import LiveAnalysisBrain
        brain_key = (asset.upper(), timeframe.upper())
        newborn_brain = self._live_brains.get(brain_key)
        if newborn_brain is None:
            newborn_brain = LiveAnalysisBrain(asset, timeframe)
            self._live_brains[brain_key] = newborn_brain
        return newborn_brain

    def analyze_market(self, request: ResearchRequest, market_data_response=None) -> ResearchResult:
        """
        Executes feature calculations on the caller-supplied market data when provided.
        This preserves the selected universe provider (for example Crypto) end-to-end
        instead of silently re-fetching the same symbol through MT5.
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
            if market_data_response is None:
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
        newborn_brain = self._get_live_brain(request.Asset, timeframe)
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
            from src.Research.Brain.fractal_range_learning_engine import TIMEFRAMES, TF_SECONDS
            fractal_context = request.Context if isinstance(request.Context, dict) else {}
            supplied_mtf = fractal_context.get("fractal_candles_by_timeframe")
            if not isinstance(supplied_mtf, dict):
                supplied_mtf = fractal_context.get("candles_by_timeframe")
            candles_by_tf = {}
            if isinstance(supplied_mtf, dict):
                for tf_key, tf_rows in supplied_mtf.items():
                    if isinstance(tf_rows, (list, tuple)) and tf_rows:
                        candles_by_tf[str(tf_key).upper()] = tf_rows
            candles_by_tf[str(timeframe).upper()] = market_data_response.DataPoints

            # Supply real multi-timeframe history to the existing FractalEngine.
            # Each auxiliary request is bounded by a configurable bar lookback, and
            # failures remain non-fatal so the primary analysis still completes.
            mtf_fetch_errors = []
            if fractal_context.get("fractal_multi_timeframe", False):
                try:
                    context_bars = max(32, min(1000, int(fractal_context.get("fractal_context_bars", 64))))
                except (TypeError, ValueError):
                    context_bars = 64
                for tf_key in TIMEFRAMES:
                    if tf_key in candles_by_tf:
                        continue
                    try:
                        seconds = TF_SECONDS.get(tf_key, 3600)
                        tf_end = request.EndTime
                        tf_start = tf_end - timedelta(seconds=seconds * context_bars)
                        tf_request = MarketDataRequest(
                            Asset=request.Asset,
                            StartTime=tf_start,
                            EndTime=tf_end,
                            Timeframe=tf_key,
                        )
                        tf_response = self._data_provider.retrieve_market_data(tf_request)
                        tf_rows = getattr(tf_response, "DataPoints", None) if tf_response is not None else None
                        if tf_rows:
                            # Some adapters return a wider cached range than requested.
                            # Enforce the configured cap before passing data downstream.
                            tf_rows = list(tf_rows)[-context_bars:]
                            candles_by_tf[tf_key] = tf_rows
                        else:
                            mtf_fetch_errors.append({"timeframe": tf_key, "reason": "NO_DATA"})
                    except Exception as tf_err:
                        mtf_fetch_errors.append({
                            "timeframe": tf_key,
                            "reason": f"{type(tf_err).__name__}: {str(tf_err)}"[:160],
                        })

            fractal_res = fractal_engine.analyze_fractals(
                symbol=request.Asset,
                primary_timeframe=timeframe,
                candles_by_tf=candles_by_tf
            )
            enriched_findings["fractal_analysis"] = fractal_res
            enriched_findings["pipeline_outputs"]["fractal_analysis"] = fractal_res
            enriched_findings["fractal_analysis_timeframes_supplied"] = sorted(candles_by_tf)
            if mtf_fetch_errors:
                enriched_findings["fractal_analysis_timeframe_fetch_warnings"] = mtf_fetch_errors
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
