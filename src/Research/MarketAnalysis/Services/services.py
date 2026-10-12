import os
from datetime import datetime, timedelta
from typing import List, Any, Dict, Optional
from src.Research.MarketAnalysis.Interfaces.interfaces import IMarketAnalyzer, IResearchEngine
from src.Research.MarketAnalysis.Models.models import MarketObservation, MarketInsight, ResearchRequest, ResearchResult
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
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

        # The parallel discovery Brain and its virtual-trade hypotheses are retired
        # from active analysis. Only the canonical Base hierarchy may describe a setup.
        newborn_report_dict = {
            "symbol": request.Asset,
            "brain_available": False,
            "status": "DISABLED_NON_BASE",
            "decision_authority": "BASE_HIERARCHY_ONLY",
            "execution_enabled": False,
        }

        # Canonical decision authority: Base hierarchy + costed re-entry reaction only.
        # Parallel Brain hypotheses are not consumed by active Base-only analysis.
        try:
            from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
            from src.Decision.Models.models import AutonomousTradingDecision

            raw_mtf = (request.Context or {}).get("base_candles_by_timeframe", {})
            all_tf_candles = {
                str(tf).upper(): [bar for bar in bars if isinstance(bar, dict)]
                for tf, bars in raw_mtf.items()
                if isinstance(bars, list)
            } if isinstance(raw_mtf, dict) else {}
            if not all_tf_candles.get(timeframe):
                all_tf_candles[timeframe] = candles_dicts
            base_report = StrategyOrchestrator().evaluate_all_strategies(
                symbol=request.Asset,
                primary_timeframe=timeframe,
                candles=candles_dicts,
                all_timeframe_candles=all_tf_candles,
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
            "observation_summary": primitive_observation,
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


class FeatureExtractionResearchEngine(PrimitiveMarketResearchEngine):
    """Backward-compatible alias for the indicator-free, Base-only research engine.

    The legacy name remains temporarily importable for callers being migrated, but
    it does not instantiate FeaturePipeline or run technical/trend/momentum/
    volatility/regime indicators. Actionable decisions still come only from the
    hierarchical Base + costed reaction model; all other hypotheses are telemetry.
    """

    def __init__(
        self,
        data_provider: IMarketDataProvider,
        base_engine: Optional[IResearchEngine] = None,
        feature_pipeline=None,
    ) -> None:
        # Accept the former argument for source compatibility, but deliberately
        # do not construct, store, or execute a feature/indicator pipeline.
        del feature_pipeline
        super().__init__(data_provider=data_provider, base_engine=base_engine)

    @property
    def feature_pipeline(self):
        """Legacy compatibility property; no feature/indicator pipeline is active."""
        return None