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
    Indicator-independent market observation and learning engine.

    Research/Brain output is retained for learning and explanation only. The sole
    source of an actionable trading proposal is the canonical Base hierarchy plus
    costed re-entry reaction model; missing/invalid evidence fails closed to WAIT.
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

        # Canonical decision authority: Base hierarchy + costed re-entry reaction only.
        # Brain hypotheses remain available for learning but cannot originate signals.
        try:
            from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
            from src.Decision.Models.models import AutonomousTradingDecision

            base_report = StrategyOrchestrator().evaluate_all_strategies(
                symbol=request.Asset,
                primary_timeframe=timeframe,
                candles=candles_dicts,
                all_timeframe_candles={timeframe: candles_dicts},
            )
            base_candidate = base_report.get("best_candidate")
            base_plan = base_report.get("base_plan") or {}
            action = str((base_candidate or {}).get("direction", "WAIT")).upper()
            if action not in ("BUY", "SELL"):
                action = "WAIT"
                base_candidate = None

            entry = float((base_candidate or {}).get("entry", 0.0) or 0.0)
            stop_loss = float((base_candidate or {}).get("stop_loss", 0.0) or 0.0)
            take_profit = float((base_candidate or {}).get("take_profit", 0.0) or 0.0)
            risk_reward = float((base_candidate or {}).get("risk_reward", 0.0) or 0.0)
            confidence = float((base_candidate or {}).get("confidence", 0.0) or 0.0)
            candidate_reasoning = (base_candidate or {}).get("reasoning")
            if isinstance(candidate_reasoning, str):
                candidate_reasoning = [candidate_reasoning]
            if not candidate_reasoning:
                candidate_reasoning = [
                    str(base_report.get("summary") or base_plan.get("reason") or
                        "No validated Base hierarchy and costed-reaction proposal; waiting for sufficient evidence.")
                ]

            intel_res = {
                "source": "BASE_HIERARCHY",
                "decision_authority": "BASE_HIERARCHY",
                "model_status": base_report.get("model_status", "UNKNOWN"),
                "summary": base_report.get("summary"),
                "base_plan": base_plan,
                "hierarchy": base_report.get("hierarchy", {}),
                "reaction_analysis": base_report.get("reaction_analysis", {}),
                "candidate_available": bool(base_candidate),
            }
            auto_decision = AutonomousTradingDecision(
                decision_id=decision_id,
                cycle_id=cycle_id,
                action=action,
                symbol=request.Asset,
                timeframe=timeframe,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                volume=0.0,
                risk_reward=risk_reward,
                confidence=confidence if action in ("BUY", "SELL") else 0.0,
                reasoning=candidate_reasoning,
                evidence={
                    "decision_authority": "BASE_HIERARCHY",
                    "base_model_status": intel_res["model_status"],
                    "base_plan": base_plan,
                    "hierarchy": intel_res["hierarchy"],
                    "reaction_analysis": intel_res["reaction_analysis"],
                    "latest_price": candles_dicts[-1]["close"],
                },
                risk_status="PENDING" if action in ("BUY", "SELL") else "CHECKED",
                execution_status="PENDING" if action in ("BUY", "SELL") else "SKIPPED",
                configuration_version="base-hierarchy-1.0",
                timestamp=datetime.now().isoformat(),
            )
            auto_dec_dict = auto_decision.to_dict()
        except Exception as base_error:
            # Any Base-model failure blocks the signal; there is no legacy fallback.
            intel_res = {
                "source": "BASE_HIERARCHY",
                "decision_authority": "BASE_HIERARCHY",
                "model_status": "BASE_ANALYSIS_FAILED",
                "error_type": type(base_error).__name__,
                "candidate_available": False,
            }
            auto_dec_dict = {
                "decision_id": decision_id,
                "cycle_id": cycle_id,
                "action": "WAIT",
                "symbol": request.Asset,
                "timeframe": timeframe,
                "entry": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "volume": 0.0,
                "risk_reward": 0.0,
                "confidence": 0.0,
                "reasoning": ["Base-only analysis failed; no fallback strategy is permitted."],
                "evidence": {"decision_authority": "BASE_HIERARCHY", "base_model_status": "BASE_ANALYSIS_FAILED"},
                "risk_status": "CHECKED",
                "execution_status": "SKIPPED",
                "configuration_version": "base-hierarchy-1.0",
                "timestamp": datetime.now().isoformat(),
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

        decision_action = str(auto_dec_dict.get("action", "WAIT")).upper()
        decision_evidence = auto_dec_dict.get("evidence") if isinstance(auto_dec_dict.get("evidence"), dict) else {}
        base_candidate_available = bool(intel_res.get("candidate_available"))
        try:
            risk_parameters_available = all(
                float(auto_dec_dict.get(key) or 0.0) > 0.0
                for key in ("entry", "stop_loss", "take_profit")
            )
        except (TypeError, ValueError):
            risk_parameters_available = False

        # Learning/Brain hypotheses are descriptive only. They cannot upgrade WAIT,
        # supply a fallback direction, or raise execution confidence.
        if (decision_action in ("BUY", "SELL") and base_candidate_available
                and decision_evidence.get("decision_authority") == "BASE_HIERARCHY"
                and risk_parameters_available):
            smart_bias = decision_action
            smart_confidence = float(auto_dec_dict.get("confidence", 0.0) or 0.0)
            signal_status = "ACTIVE"
        else:
            smart_bias = "Neutral"
            smart_confidence = 0.0
            signal_status = "WAIT"
            decision_action = "WAIT"

        smart_interpretation = {
            "confidence": smart_confidence,
            "bias": smart_bias,
            "reasoning": auto_dec_dict.get("reasoning", []),
            "execution_action": decision_action,
            "signal_status": signal_status,
            "risk_parameters_available": bool(risk_parameters_available),
            "decision_authority": "BASE_HIERARCHY",
            "base_model_status": intel_res.get("model_status", "UNKNOWN"),
            "candidate_reason": None if signal_status == "ACTIVE" else (
                intel_res.get("summary") or
                (intel_res.get("reaction_analysis") or {}).get("reason") or
                "No validated Base-only entry proposal; learning hypotheses cannot authorize a trade."
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
