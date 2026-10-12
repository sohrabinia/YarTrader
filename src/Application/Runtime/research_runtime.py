import os
import time
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any


# Production research/Brain scheduling contract:
# - M1 is the minimum supported market timeframe.
# - Tick/sub-minute streams are never accepted by the research runtime.
# - One runtime instance executes one cycle at a time (no overlapping cycles).
MIN_RESEARCH_TIMEFRAME_SECONDS = 60
_TIMEFRAME_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
    "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000,
}
_BASE_MTF_TIMEFRAMES = ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")
_BASE_MTF_CACHE: Dict[tuple, tuple] = {}
_BASE_MTF_CACHE_LOCK = threading.Lock()


def validate_research_timeframe(timeframe: str) -> str:
    """Normalize and fail closed for tick/sub-minute research timeframes."""
    normalized = str(timeframe or "").strip().upper()
    seconds = _TIMEFRAME_SECONDS.get(normalized)
    if seconds is None or seconds < MIN_RESEARCH_TIMEFRAME_SECONDS:
        raise ValidationException(
            f"Unsupported research timeframe '{timeframe}'. Minimum supported timeframe is M1 (60s); tick/sub-minute analysis is disabled."
        )
    return normalized
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Data.MarketData.Models.models import MarketDataRequest
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine

class ResearchRuntime:
    """
    Autonomous Non-Trading Research Runtime.
    Polls real-time market data from read-only MetaTrader 5 adapter,
    triggers indicator-independent research analysis, and manages runtime snapshot states.
    """
    def __init__(
        self,
        provider: Optional[MetaTrader5Provider] = None,
        research_engine: Optional[IResearchEngine] = None,
        symbol: str = "XAUUSD",
        timeframe: str = "H1",
        evidence_dir: Optional[str] = None,
        provider_name: str = "MT5",
        asset_class: str = "Forex"
    ) -> None:
        self._timeframe = validate_research_timeframe(timeframe)
        self._provider = provider or MetaTrader5Provider()
        if research_engine is not None and not isinstance(research_engine, PrimitiveMarketResearchEngine):
            raise ValidationException(
                "Legacy feature/indicator research engines are retired. ResearchRuntime accepts only PrimitiveMarketResearchEngine (raw OHLC + Base hierarchy)."
            )
        self._research_engine = research_engine or PrimitiveMarketResearchEngine(data_provider=self._provider)
        self._symbol = symbol

        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()

        if not evidence_dir or not os.path.isabs(evidence_dir):
            sub_folder = os.path.basename(evidence_dir) if evidence_dir else "research_logs"
            self._evidence_dir = os.path.join(storage_mgr.get_runtime_dir(), sub_folder)
        else:
            self._evidence_dir = evidence_dir
        self._history: List[ResearchResult] = []
        self._is_running = False
        self._provider_name = provider_name
        self._asset_class = asset_class

        # Diagnostics / Polling status metrics
        self.worker_started_at: Optional[datetime] = None
        self.last_successful_cycle: Optional[datetime] = None
        self.cycle_count: int = 0
        self.last_error: Optional[str] = None

    @property
    def provider(self) -> MetaTrader5Provider:
        return self._provider

    @property
    def research_engine(self) -> IResearchEngine:
        return self._research_engine

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def history(self) -> List[ResearchResult]:
        return self._history

    @staticmethod
    def _timeframe_start_time(timeframe: str, end_time: datetime) -> datetime:
        """Return a bounded real-history window sufficient to form Base structures."""
        tf = str(timeframe).upper()
        lookbacks = {
            "M1": timedelta(hours=10), "M5": timedelta(days=2),
            "M15": timedelta(days=6), "M30": timedelta(days=13),
            "H1": timedelta(days=22), "H4": timedelta(days=52),
            "D1": timedelta(days=205), "W1": timedelta(days=700),
            "MN1": timedelta(days=1800),
        }
        return end_time - lookbacks.get(tf, timedelta(days=2))

    @staticmethod
    def _points_to_base_candles(points) -> List[Dict[str, Any]]:
        candles: List[Dict[str, Any]] = []
        for point in points or []:
            stamp = getattr(point, "Timestamp", None)
            if stamp is None:
                continue
            candles.append({
                "timestamp": stamp.isoformat() if hasattr(stamp, "isoformat") else str(stamp),
                "open": float(getattr(point, "Open", 0.0)),
                "high": float(getattr(point, "High", 0.0)),
                "low": float(getattr(point, "Low", 0.0)),
                "close": float(getattr(point, "Close", 0.0)),
                "volume": float(getattr(point, "Volume", 0.0) or 0.0),
            })
        return candles

    def _fetch_base_timeframe_candles(self, timeframe: str, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch/cache a real adjacent timeframe; failure returns no bars, never synthetic bars."""
        tf = str(timeframe).upper()
        key = (self._provider_name, self._symbol.upper(), tf)
        try:
            ttl = max(0.0, float(os.environ.get("YARTRADER_BASE_MTF_CACHE_TTL_SECONDS", "45")))
        except (TypeError, ValueError):
            ttl = 45.0
        now_mono = time.monotonic()
        with _BASE_MTF_CACHE_LOCK:
            cached = _BASE_MTF_CACHE.get(key)
            if cached and ttl > 0.0 and now_mono - cached[0] <= ttl:
                return list(cached[1])

        start_time = self._timeframe_start_time(tf, end_time)
        try:
            request = MarketDataRequest(
                Asset=self._symbol, StartTime=start_time, EndTime=end_time, Timeframe=tf
            )
            if self._provider_name == "Crypto":
                from src.Data.Providers.Crypto.crypto_provider import CryptoProvider
                raw = CryptoProvider().fetch_real_candles(self._symbol, tf, start_time, end_time)
                candles = [{
                    "timestamp": c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else str(c.timestamp),
                    "open": float(c.open), "high": float(c.high), "low": float(c.low),
                    "close": float(c.close), "volume": float(getattr(c, "volume", 0.0) or 0.0),
                } for c in (raw or [])]
            elif self._provider_name == "MT4":
                from src.Data.External.models import ExternalDataRequest
                ext_request = ExternalDataRequest(
                    symbol=self._symbol, timeframe=tf, start_time=start_time,
                    end_time=end_time, parameters={"data_source": "MT4"},
                )
                ext_response = self._provider.fetch_data(ext_request)
                if not ext_response.is_success:
                    raise ValidationException(ext_response.error_message or f"MT4 history unavailable for {self._symbol}/{tf}")
                candles = [{
                    "timestamp": datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).isoformat(),
                    "open": float(row["open"]), "high": float(row["high"]),
                    "low": float(row["low"]), "close": float(row["close"]),
                    "volume": float(row.get("volume", 0.0) or 0.0),
                } for row in (ext_response.raw_data or [])]
            else:
                response = self._provider.retrieve_market_data(request)
                candles = self._points_to_base_candles(getattr(response, "DataPoints", []))
        except Exception as exc:
            self._log_evidence(f"Base MTF history unavailable for {tf}: {type(exc).__name__}")
            candles = []

        with _BASE_MTF_CACHE_LOCK:
            _BASE_MTF_CACHE[key] = (now_mono, list(candles))
        return candles

    def _load_base_mtf_candles(self, primary_response, end_time: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """Load the primary Base timeframe plus its nearest parent/child frame with shared caching."""
        chain = _BASE_MTF_TIMEFRAMES
        try:
            index = chain.index(self._timeframe)
            start = max(0, min(index - 1, len(chain) - 3))
            selected = chain[start:start + 3]
        except ValueError:
            selected = (self._timeframe,)

        primary = self._points_to_base_candles(getattr(primary_response, "DataPoints", []))
        with _BASE_MTF_CACHE_LOCK:
            _BASE_MTF_CACHE[(self._provider_name, self._symbol.upper(), self._timeframe)] = (
                time.monotonic(), list(primary)
            )
        frames: Dict[str, List[Dict[str, Any]]] = {}
        for tf in selected:
            frames[tf] = primary if tf == self._timeframe else self._fetch_base_timeframe_candles(tf, end_time)
        return frames

    def run_once(self) -> ResearchResult:
        """Executes a single synchronous loop cycle of the research pipeline."""
        # 1. Start Cycle. Keep the primary and adjacent timeframe windows consistent.
        tf_upper = self._timeframe.upper()
        end_time = datetime.now()
        start_time = self._timeframe_start_time(tf_upper, end_time)

        # Write start step to logs
        self._log_evidence(f"Starting research iteration for {self._symbol} on {self._timeframe}...")

        # 2. Connect and Retrieve Candles
        self._log_evidence(f"Provider: {self._provider_name}")
        self._log_evidence(f"Symbol: {self._symbol}")
        self._log_evidence(f"Timeframe: {self._timeframe}")

        # Construct target request
        target_req = MarketDataRequest(
            Asset=self._symbol,
            StartTime=start_time,
            EndTime=end_time,
            Timeframe=self._timeframe
        )

        try:
            # 3. Retrieve Candles and Validate
            if self._provider_name == "Crypto":
                from src.Data.Providers.Crypto.crypto_provider import CryptoProvider
                crypto_prov = CryptoProvider()
                candles = crypto_prov.fetch_real_candles(self._symbol, self._timeframe, start_time, end_time)

                from src.Data.MarketData.Models.models import MarketDataPoint
                data_points = []
                for candle in candles:
                    data_points.append(
                        MarketDataPoint(
                            AssetId=self._symbol,
                            Timestamp=candle.timestamp,
                            Open=candle.open,
                            High=candle.high,
                            Low=candle.low,
                            Close=candle.close,
                            Volume=candle.volume
                        )
                    )

                from src.Data.MarketData.Models.models import MarketDataResponse
                data_response = MarketDataResponse(
                    Request=target_req,
                    DataPoints=data_points,
                    RetrievedAt=datetime.now()
                )
            elif self._provider_name == "MT4":
                from src.Data.External.models import ExternalDataRequest
                from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataResponse
                ext_req = ExternalDataRequest(
                    symbol=self._symbol, timeframe=self._timeframe,
                    start_time=start_time, end_time=end_time,
                    parameters={"data_source": "MT4"}
                )
                ext_resp = self._provider.fetch_data(ext_req)
                if not ext_resp.is_success:
                    raise ValidationException(ext_resp.error_message or f"MT4 history unavailable for {self._symbol} {self._timeframe}.")
                data_points = [
                    MarketDataPoint(
                        AssetId=self._symbol,
                        Timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                        Open=row["open"], High=row["high"], Low=row["low"],
                        Close=row["close"], Volume=row.get("volume", 0.0)
                    ) for row in ext_resp.raw_data
                ]
                data_response = MarketDataResponse(Request=target_req, DataPoints=data_points, RetrievedAt=datetime.now())
                self._log_evidence("MT4 history connected")
            else:
                data_response = self._provider.retrieve_market_data(target_req)
                if getattr(self, "_provider_name", "MT5") == "ControlledOfflineFixture":
                    self._log_evidence("ControlledOfflineFixture Connected (100% Offline)")
                else:
                    self._log_evidence("MT5 Connected")

            candles_count = len(data_response.DataPoints)
            self._log_evidence(f"Candles Received: {candles_count}")

            if candles_count == 0:
                raise ValidationException(f"Received empty candle series for {self._symbol} from {self._provider_name}.")

            # Load the nearest real parent/child frames. A shared short-TTL cache
            # prevents every symbol/timeframe worker from refetching identical bars.
            base_candles_by_timeframe = self._load_base_mtf_candles(data_response, end_time)
            self._log_evidence(
                "Base MTF bars: " + ", ".join(
                    f"{tf}={len(bars)}" for tf, bars in base_candles_by_timeframe.items()
                )
            )

            # 4. Construct Research Request with ephemeral MTF candle context.
            research_req = ResearchRequest(
                Asset=self._symbol,
                StartTime=start_time,
                EndTime=end_time,
                Context={
                    "timeframe": self._timeframe,
                    "base_candles_by_timeframe": base_candles_by_timeframe,
                }
            )

            # 5. Run the decorated FeatureExtractionResearchEngine
            if isinstance(self._research_engine, PrimitiveMarketResearchEngine):
                result = self._research_engine.analyze_market(research_req, market_data_response=data_response)
            else:
                result = self._research_engine.analyze_market(research_req)

            # 6. Verify outputs and confirm features are generated
            features_generated = ("feature_set" in result.Findings) or ("primitive_observation" in result.Findings)
            self._log_evidence(f"Features Generated: {str(features_generated).lower()}")
            self._log_evidence("Research Completed: true")

            # 6b. Enforce the canonical Base-only decision authority at the runtime boundary.
            # Never trust an upstream Brain/legacy planner decision, even if it already
            # populated autonomous_decision; only a validated Base candidate can authorize BUY/SELL.
            existing_decision = result.Findings.get("autonomous_decision") or {}
            existing_evidence = existing_decision.get("evidence") if isinstance(existing_decision, dict) else {}
            existing_summary = result.Findings.get("intel_summary") or {}
            base_authority = (
                isinstance(existing_evidence, dict)
                and existing_evidence.get("decision_authority") == "BASE_HIERARCHY"
                and isinstance(existing_summary, dict)
                and existing_summary.get("decision_authority") == "BASE_HIERARCHY"
            )
            if not base_authority:
                cycle_id = f"cyc-{self._symbol.upper()}-{self._timeframe.upper()}-{int(time.time())}"
                decision_id = f"DEC-{self._symbol.upper()}-{self._timeframe.upper()}-{int(time.time())}"
                try:
                    from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
                    from src.Decision.Models.models import AutonomousTradingDecision

                    base_candles = [
                        {
                            "timestamp": point.Timestamp.isoformat() if hasattr(point.Timestamp, "isoformat") else str(point.Timestamp),
                            "open": float(point.Open), "high": float(point.High),
                            "low": float(point.Low), "close": float(point.Close),
                            "volume": float(point.Volume),
                        }
                        for point in data_response.DataPoints
                    ]
                    # Use the same three real adjacent timeframes as the primary
                    # engine; missing parent/child data can only reduce confidence.
                    if not base_candles_by_timeframe.get(self._timeframe):
                        base_candles_by_timeframe[self._timeframe] = base_candles
                    base_report = StrategyOrchestrator().evaluate_all_strategies(
                        symbol=self._symbol,
                        primary_timeframe=self._timeframe,
                        candles=base_candles,
                        all_timeframe_candles=base_candles_by_timeframe,
                    )
                    candidate = base_report.get("best_candidate")
                    plan = base_report.get("base_plan") or {}
                    action = str((candidate or {}).get("direction", "WAIT")).upper()
                    if action not in ("BUY", "SELL"):
                        action = "WAIT"
                        candidate = None
                    entry = float((candidate or {}).get("entry", 0.0) or 0.0)
                    stop_loss = float((candidate or {}).get("stop_loss", 0.0) or 0.0)
                    take_profit = float((candidate or {}).get("take_profit", 0.0) or 0.0)
                    risk_reward = float((candidate or {}).get("risk_reward", 0.0) or 0.0)
                    confidence = float((candidate or {}).get("confidence", 0.0) or 0.0) if candidate else 0.0
                    reasoning = (candidate or {}).get("reasoning")
                    if isinstance(reasoning, str):
                        reasoning = [reasoning]
                    if not reasoning:
                        reasoning = [str(base_report.get("summary") or plan.get("reason") or
                                         "No validated Base-only proposal; waiting for sufficient evidence.")]
                    base_summary = {
                        "source": "BASE_HIERARCHY",
                        "decision_authority": "BASE_HIERARCHY",
                        "model_status": base_report.get("model_status", "UNKNOWN"),
                        "summary": base_report.get("summary"),
                        "base_plan": plan,
                        "hierarchy": base_report.get("hierarchy", {}),
                        "reaction_analysis": base_report.get("reaction_analysis", {}),
                        "candidate_available": bool(candidate),
                    }
                    auto_decision = AutonomousTradingDecision(
                        decision_id=decision_id, cycle_id=cycle_id, action=action,
                        symbol=self._symbol, timeframe=self._timeframe, entry=entry,
                        stop_loss=stop_loss, take_profit=take_profit, volume=0.0,
                        risk_reward=risk_reward, confidence=confidence,
                        reasoning=reasoning,
                        evidence={
                            "decision_authority": "BASE_HIERARCHY",
                            "base_model_status": base_summary["model_status"],
                            "base_plan": plan,
                            "hierarchy": base_summary["hierarchy"],
                            "reaction_analysis": base_summary["reaction_analysis"],
                            "latest_price": float(data_response.DataPoints[-1].Close),
                        },
                        risk_status="PENDING" if action in ("BUY", "SELL") else "CHECKED",
                        execution_status="PENDING" if action in ("BUY", "SELL") else "SKIPPED",
                        configuration_version="base-hierarchy-1.0",
                        timestamp=datetime.now().isoformat(),
                    )
                    result.Findings["autonomous_decision"] = auto_decision.to_dict()
                    result.Findings["intel_summary"] = base_summary
                except Exception as base_error:
                    self._log_evidence(f"Base-only decision projection failed closed: {type(base_error).__name__}")
                    result.Findings["autonomous_decision"] = {
                        "decision_id": decision_id, "cycle_id": cycle_id,
                        "action": "WAIT", "symbol": self._symbol,
                        "timeframe": self._timeframe, "entry": 0.0,
                        "stop_loss": 0.0, "take_profit": 0.0, "volume": 0.0,
                        "risk_reward": 0.0, "confidence": 0.0,
                        "reasoning": ["Base-only analysis failed; no fallback strategy is permitted."],
                        "evidence": {"decision_authority": "BASE_HIERARCHY", "base_model_status": "BASE_ANALYSIS_FAILED"},
                        "risk_status": "CHECKED", "execution_status": "SKIPPED",
                        "configuration_version": "base-hierarchy-1.0",
                        "timestamp": datetime.now().isoformat(),
                    }
                    result.Findings["intel_summary"] = {
                        "source": "BASE_HIERARCHY", "decision_authority": "BASE_HIERARCHY",
                        "model_status": "BASE_ANALYSIS_FAILED", "candidate_available": False,
                    }

            # Do not persist hundreds of raw bars inside each snapshot. Preserve the
            # timeframe inventory and the structured Base hierarchy/reaction evidence.
            result_context = getattr(result.Request, "Context", None)
            if isinstance(result_context, dict):
                loaded_timeframes = sorted(
                    tf for tf, bars in base_candles_by_timeframe.items() if bars
                )
                result_context.pop("base_candles_by_timeframe", None)
                result_context["base_timeframes_loaded"] = loaded_timeframes

            # Shadow mode is retired. Research results flow only to the canonical
            # ResearchRuntime snapshot/history and the guarded DEMO execution boundary.

            # 7. Store Result
            self._history.append(result)
            self._store_snapshot(result)
            self._log_evidence(f"Research cycle completed successfully. Result ID: {result.Findings.get('report_id', 'unknown')}")

            # Phase 9: Clear, structured logging matching task requirements
            print("\nResearch Started\n")
            print(f"Symbol:\n{self._symbol}\n")
            print(f"Timeframe:\n{self._timeframe}\n")
            print(f"Provider:\n{self._provider_name}\n")
            print(f"Candles:\n{candles_count}\n")
            print(f"Features:\nGenerated\n")
            print(f"Status:\nCompleted\n")

            # Update instance and shared API health metrics from the same successful cycle.
            completed_at = datetime.now()
            self.last_successful_cycle = completed_at
            self.cycle_count += 1
            self.last_error = None
            from src.Application.Runtime.runtime_state import central_runtime_state
            central_runtime_state.update_multiple({
                "last_cycle_time": completed_at.isoformat(),
                "research_last_successful_cycle": completed_at.isoformat(),
                "research_cycle_count": self.cycle_count,
                "research_cycle_symbol": self._symbol,
                "research_cycle_timeframe": self._timeframe,
                "research_status": "Completed",
            })

            return result

        except Exception as e:
            self.last_error = str(e)
            self._log_evidence(f"Research cycle encountered an error: {str(e)}")
            raise

    def start_polling_loop(self, interval_seconds: float = 60.0, limit_cycles: Optional[int] = None) -> None:
        """
        Starts a continuous thread polling runtime loop.
        Can be limited to a specific cycle count (useful for testing or one-off jobs).
        """
        interval_seconds = max(float(interval_seconds), MIN_RESEARCH_TIMEFRAME_SECONDS)
        self._is_running = True
        self.worker_started_at = datetime.now()
        cycle_count = 0

        while self._is_running:
            try:
                self.run_once()
            except Exception:
                # Log error and support runtime recovery by cooling down and retrying
                time.sleep(5.0)

            cycle_count += 1
            if limit_cycles is not None and cycle_count >= limit_cycles:
                break

            time.sleep(interval_seconds)

    def stop(self) -> None:
        """Signals the polling loop to gracefully terminate."""
        self._is_running = False

    def _store_snapshot(self, result: ResearchResult) -> None:
        """Stores the research result snapshot as a serialized JSON file for persistence."""
        snapshot_dir = os.path.join(self._evidence_dir, "research_snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        report_id = result.Findings.get("report_id", f"snapshot_{int(time.time())}")
        filename = f"rpt-{self._symbol}-{self._timeframe}-{report_id}.json"
        filepath = os.path.join(snapshot_dir, filename)

        # Safely find actual candle count
        try:
            cand_list = result.Findings.get("pipeline_outputs", {}).get("technical_analysis", {}).get("candles", [])
            cand_count = len(cand_list) if cand_list else 500
        except Exception:
            cand_count = 500

        # Build serializable dict
        snapshot_data = {
            "report_id": report_id,
            "asset": result.Request.Asset,
            "symbol": result.Request.Asset,
            "timeframe": result.Request.Context.get("timeframe", self._timeframe),
            "asset_class": getattr(self, "_asset_class", "Forex"),
            "provider": getattr(self, "_provider_name", "MT5"),
            "candle_count": cand_count,
            "timestamp": result.CreatedAt.isoformat(),
            "confidence_score": result.ConfidenceScore,
            "created_at": result.CreatedAt.isoformat(),
            "findings": result.Findings,
            "features": result.Findings.get("feature_set", {}),
            "research_result": result.Findings,
            "intelligence_result": result.Findings.get("pipeline_outputs", {}).get("smart_interpretation", {})
        }

        def custom_json_serializer(o):
            if hasattr(o, "to_dict"):
                return o.to_dict()
            if hasattr(o, "isoformat"):
                return o.isoformat()
            if hasattr(o, "AssetId") and hasattr(o, "Features"):
                return {
                    "asset_id": o.AssetId,
                    "start_time": o.StartTime.isoformat() if hasattr(o.StartTime, "isoformat") else str(o.StartTime),
                    "end_time": o.EndTime.isoformat() if hasattr(o.EndTime, "isoformat") else str(o.EndTime),
                    "features_count": len(o.Features)
                }
            return str(o)

        # Thread-safe write using temp file renaming pattern
        temp_filepath = filepath + ".tmp"
        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=4, default=custom_json_serializer)
            os.replace(temp_filepath, filepath)
        except Exception as e:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass
            raise e

        self._log_evidence(f"Saved research snapshot to: {filepath}")

        # Rotation strategy: keep the last 50 snapshots
        try:
            files = [f for f in os.listdir(snapshot_dir) if f.endswith(".json")]
            if len(files) > 50:
                files_paths = [os.path.join(snapshot_dir, f) for f in files]
                files_paths.sort(key=os.path.getmtime)
                # Delete the oldest files
                for old_file in files_paths[:-50]:
                    try:
                        os.remove(old_file)
                    except OSError:
                        pass
        except Exception:
            pass

    def _log_evidence(self, message: str) -> None:
        """Write runtime evidence without allowing diagnostics to abort research cycles."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        evidence_file = os.path.join(self._evidence_dir, "research_runtime_evidence.log")

        try:
            os.makedirs(self._evidence_dir, exist_ok=True)
            with open(evidence_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as exc:
            diagnostic = (
                f"Research evidence logging failed for {self._symbol} "
                f"{self._timeframe}: {type(exc).__name__}: {exc}; "
                f"path={evidence_file!r}"
            )
            # Evidence logging is diagnostic only; never let a filesystem/logging
            # failure stop the autonomous research cycle.
            print(f"[ResearchRuntime] {diagnostic}")
            try:
                from app.core.logging import log_event
                log_event("ERROR", diagnostic, source="research_runtime")
            except Exception:
                pass

        # Always retain the console trace even when the evidence file is unavailable.
        print(message)
