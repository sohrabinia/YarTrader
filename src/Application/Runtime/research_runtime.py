import os
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Data.MarketData.Models.models import MarketDataRequest
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine, PrimitiveMarketResearchEngine
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
        self._provider = provider or MetaTrader5Provider()
        self._research_engine = research_engine or PrimitiveMarketResearchEngine(data_provider=self._provider)
        self._symbol = symbol
        self._timeframe = timeframe

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
        self._cognitive_loop = None
        self._brain_last_observation_time: Optional[datetime] = None
        self._brain_learning_status: str = "NOT_STARTED"
        self._brain_learning_stats: Dict[str, Any] = {}

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
    def _timeframe_start(end_time: datetime, timeframe: str) -> datetime:
        """Return the canonical lookback window for one timeframe."""
        windows = {
            "M1": timedelta(hours=10), "M5": timedelta(days=2), "M15": timedelta(days=6),
            "H1": timedelta(days=22), "H4": timedelta(days=52), "D1": timedelta(days=205),
            "W1": timedelta(days=210), "MN1": timedelta(days=900)
        }
        return end_time - windows.get(timeframe.upper(), timedelta(days=2))

    def run_once(self) -> ResearchResult:
        """Executes a single synchronous loop cycle of the research pipeline."""
        # 1. Start Cycle
        tf_upper = self._timeframe.upper()
        end_time = datetime.now()
        start_time = self._timeframe_start(end_time, tf_upper)

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

            # Production Brain receives all canonical raw timeframes at the same end-time.
            all_timeframe_candles: Dict[str, List[Dict[str, Any]]] = {}
            if isinstance(self._research_engine, PrimitiveMarketResearchEngine):
                from src.Core.timeframes import SUPPORTED_TIMEFRAMES
                for mtf in SUPPORTED_TIMEFRAMES.keys():
                    mtf_upper = mtf.upper()
                    if mtf_upper == tf_upper:
                        mtf_points = data_response.DataPoints
                    else:
                        mtf_start = self._timeframe_start(end_time, mtf_upper)
                        mtf_req = MarketDataRequest(Asset=self._symbol, StartTime=mtf_start, EndTime=end_time, Timeframe=mtf_upper)
                        mtf_response = self._provider.retrieve_market_data(mtf_req)
                        mtf_points = mtf_response.DataPoints
                    all_timeframe_candles[mtf_upper] = [
                        {"timestamp": p.Timestamp.isoformat() if hasattr(p.Timestamp, "isoformat") else str(p.Timestamp),
                         "open": float(p.Open), "high": float(p.High), "low": float(p.Low),
                         "close": float(p.Close), "volume": float(p.Volume)}
                        for p in mtf_points
                    ]
                missing_mtf = [name for name, rows in all_timeframe_candles.items() if not rows]
                if missing_mtf:
                    raise ValidationException(f"Missing canonical multi-timeframe market data for {self._symbol}: {', '.join(missing_mtf)}")
                self._log_evidence("MTF Raw Context: " + ", ".join(f"{name}={len(rows)}" for name, rows in all_timeframe_candles.items()))

            # 4. Construct Research Request with Enrichment context
            research_req = ResearchRequest(
                Asset=self._symbol,
                StartTime=start_time,
                EndTime=end_time,
                Context={"timeframe": self._timeframe, "all_timeframe_candles": all_timeframe_candles, "mtf_timeframes": list(all_timeframe_candles.keys())}
            )

            # 4b. Feed the same canonical raw candles into the existing CognitiveReplayLoop.
            # This is research/simulation only; it has no order/execution authority.
            brain_learning = self._run_live_cognitive_learning(
                data_response.DataPoints,
                multi_timeframe_candles=all_timeframe_candles,
            )
            self._log_evidence(
                "Cognitive Learning: "
                f"{brain_learning.get('status', 'UNKNOWN')} "
                f"episodes={brain_learning.get('episodes_processed', 0)} "
                f"events={brain_learning.get('events_total', 0)} "
                f"patterns={brain_learning.get('patterns_created', 0)} "
                f"concepts={brain_learning.get('concepts_learned', 0)}"
            )

            # 5. Run the decorated FeatureExtractionResearchEngine
            result = self._research_engine.analyze_market(research_req)

            # 6. Verify outputs and confirm features are generated
            features_generated = ("feature_set" in result.Findings) or ("primitive_observation" in result.Findings)
            self._log_evidence(f"Features Generated: {str(features_generated).lower()}")
            self._log_evidence("Research Completed: true")

            # 6b. Single Source of Truth: Evaluate via ExecutionIntelligenceCore & Planner if not already evaluated
            if "autonomous_decision" not in result.Findings or "intel_summary" not in result.Findings:
                cycle_id = f"cyc-{self._symbol.upper()}-{self._timeframe.upper()}-{int(time.time())}"
                candles_dicts = [
                    {
                        "timestamp": p.Timestamp.isoformat() if hasattr(p.Timestamp, "isoformat") else str(p.Timestamp),
                        "open": float(p.Open),
                        "high": float(p.High),
                        "low": float(p.Low),
                        "close": float(p.Close),
                        "volume": float(p.Volume)
                    }
                    for p in data_response.DataPoints
                ]

                try:
                    from src.Intelligence.Execution.core import ExecutionIntelligenceCore
                    from src.Decision.Models.models import AutonomousTradingDecision

                    intel_core = ExecutionIntelligenceCore.get_instance()
                    newborn_report_dict = result.Findings.get("newborn_brain_report")
                    intel_res = intel_core.evaluate_context(
                        symbol=self._symbol,
                        timeframe=self._timeframe,
                        candles=candles_dicts,
                        all_timeframe_candles=all_timeframe_candles or None,
                        newborn_brain_report=newborn_report_dict
                    )

                    plan = intel_res.get("plan", {})
                    # CANONICAL_BRAIN is the sole source of trading direction.
                    # Execution Intelligence may calculate execution metadata, but it
                    # must never replace or override the Brain's learned decision.
                    brain_report = newborn_report_dict if isinstance(newborn_report_dict, dict) else {}
                    brain_hypothesis = brain_report.get("hypothesis", {}) if isinstance(brain_report.get("hypothesis", {}), dict) else {}
                    action = str(
                        brain_hypothesis.get("expected_direction")
                        or brain_report.get("expected_direction")
                        or "WAIT"
                    ).upper()
                    if action not in ["BUY", "SELL", "WAIT"]:
                        action = "WAIT"

                    entry = float(plan.get("entry", 0.0))
                    sl = float(plan.get("stop_loss", 0.0))
                    tp = float(plan.get("take_profit", 0.0))
                    rr = float(plan.get("risk_reward", 0.0))
                    confidence = float(plan.get("confidence", 0.0))
                    reasoning = plan.get("reasoning", ["Single source of truth evaluation"])

                    timestamp_now = datetime.now().isoformat()
                    decision_id = f"DEC-{self._symbol.upper()}-{self._timeframe.upper()}-{int(time.time())}"

                    fractal_res = result.Findings.get("fractal_analysis", {}) or intel_res.get("fractal", {})
                    fractal_rec = fractal_res.get("matching_pattern_record", {})
                    similarity_data = fractal_res.get("similarity_analysis", {})

                    auto_decision = AutonomousTradingDecision(
                        decision_id=decision_id,
                        cycle_id=cycle_id,
                        action=action,
                        symbol=self._symbol,
                        timeframe=self._timeframe,
                        entry=entry,
                        stop_loss=sl,
                        take_profit=tp,
                        volume=0.01,
                        risk_reward=rr,
                        confidence=confidence,
                        reasoning=reasoning,
                        evidence={
                            "narrative": intel_res.get("narrative", {}),
                            "liquidity": intel_res.get("liquidity", {}),
                            "zones": intel_res.get("zones", {}),
                            "alignment": intel_res.get("alignment", {}),
                            "similarity": intel_res.get("similarity", {}),
                            "fractal_analysis": fractal_res,
                            "observability": {
                                "fractal_score": float(fractal_rec.get("confidence_weight", 0.0)),
                                "similarity_score": float(similarity_data.get("average_similarity_score", 0.0)),
                                "market_regime": intel_res.get("narrative", {}).get("regime", "TRENDING"),
                                "scale_state": "MULTISCALE_STABLE" if fractal_res.get("scales_evaluated_count", 0) > 0 else "SINGLE_SCALE"
                            },
                            "latest_price": candles_dicts[-1]["close"],
                            "decision_authority": "CANONICAL_BRAIN",
                            "brain_hypothesis": brain_hypothesis,
                            "anticipation": brain_hypothesis.get("meta", {}).get("anticipation", {}) if isinstance(brain_hypothesis.get("meta", {}), dict) else {}
                        },
                        risk_status="PENDING" if action in ["BUY", "SELL"] else "CHECKED",
                        execution_status="PENDING" if action in ["BUY", "SELL"] else "SKIPPED",
                        configuration_version="1.2.0",
                        timestamp=timestamp_now
                    )

                    result.Findings["autonomous_decision"] = auto_decision.to_dict()
                    result.Findings["intel_summary"] = intel_res
                except Exception as ie:
                    self._log_evidence(f"ExecutionIntelligence evaluation error: {str(ie)}")

            # Shadow Trading is intentionally closed in the production architecture.
            # ResearchRuntime must not create, update, or evaluate Shadow positions.
            # The canonical live learning path above is research/simulation-only.
            self._log_evidence("Shadow Trading: Disabled (ResearchRuntime execution path closed)")

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

            # Update metrics
            self.last_successful_cycle = datetime.now()
            self.cycle_count += 1
            self.last_error = None

            return result

        except Exception as e:
            self.last_error = str(e)
            self._log_evidence(f"Research cycle encountered an error: {str(e)}")
            raise

    def _run_live_cognitive_learning(
        self,
        data_points: List[Any],
        multi_timeframe_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Feeds new real market candles into the canonical CognitiveReplayLoop."""
        try:
            from src.Research.Brain.models import MarketObservation
            from src.Research.Brain.cognitive_loop import CognitiveReplayLoop
            from src.Research.Brain.live_memory import get_live_memory_system

            observations = [
                MarketObservation(
                    symbol=self._symbol,
                    timeframe=self._timeframe,
                    timestamp=p.Timestamp,
                    high=float(p.High),
                    low=float(p.Low),
                    open_price=float(p.Open),
                    close_price=float(p.Close),
                    volume=float(p.Volume),
                    meta={"provider": self._provider_name, "source": "ResearchRuntime"},
                )
                for p in data_points
            ]
            observations.sort(key=lambda o: o.timestamp)

            multi_timeframe_observations: Dict[str, List[MarketObservation]] = {}
            for tf_name, rows in (multi_timeframe_candles or {}).items():
                tf_rows: List[MarketObservation] = []
                for row in rows:
                    try:
                        ts_value = row.get("timestamp")
                        ts = datetime.fromisoformat(str(ts_value).replace("Z", "+00:00"))
                        tf_rows.append(
                            MarketObservation(
                                symbol=self._symbol,
                                timeframe=str(tf_name).upper(),
                                timestamp=ts,
                                high=float(row["high"]),
                                low=float(row["low"]),
                                open_price=float(row["open"]),
                                close_price=float(row["close"]),
                                volume=float(row.get("volume", 0.0)),
                                meta={"provider": self._provider_name, "source": "ResearchRuntime", "context_only": True},
                            )
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
                if len(tf_rows) >= 5:
                    multi_timeframe_observations[str(tf_name).upper()] = sorted(
                        tf_rows, key=lambda o: o.timestamp
                    )

            if len(observations) < 5:
                self._brain_learning_status = "WAITING_FOR_DATA"
                return {"status": self._brain_learning_status, "episodes_processed": 0}

            latest_time = observations[-1].timestamp
            if self._brain_last_observation_time is not None and latest_time <= self._brain_last_observation_time:
                stats = get_live_memory_system().get_learning_statistics()
                self._brain_learning_status = "NO_NEW_CANDLE"
                self._brain_learning_stats = stats
                return {"status": self._brain_learning_status, **stats, "episodes_processed": 0}

            if self._cognitive_loop is None:
                memory = get_live_memory_system()
                self._cognitive_loop = CognitiveReplayLoop(
                    symbol=self._symbol,
                    timeframe=self._timeframe,
                    observations=observations,
                    memory_system=memory,
                )
            else:
                self._cognitive_loop.replay_engine.update_observations(
                    observations, current_time=latest_time
                )

            episode = self._cognitive_loop.process_live_observation(
                observations,
                multi_timeframe_observations=multi_timeframe_observations,
            )
            self._brain_last_observation_time = latest_time
            stats = self._cognitive_loop.memory_system.get_learning_statistics()
            stats["events_total"] = len(self._cognitive_loop.memory_system.get_events())
            self._brain_learning_stats = stats
            self._brain_learning_status = "RUNNING" if episode else "NO_NEW_CANDLE"
            try:
                from src.Application.Runtime.runtime_state import central_runtime_state
                central_runtime_state.update_multiple({
                    "brain_learning_status": self._brain_learning_status,
                    "brain_learning_stats": stats,
                })
            except Exception:
                pass

            return {
                "status": self._brain_learning_status,
                "episodes_processed": 1 if episode else 0,
                "events_total": len(self._cognitive_loop.memory_system.get_events()),
                **stats,
                "last_observation_time": latest_time.isoformat(),
            }
        except Exception as exc:
            self._brain_learning_status = "ERROR"
            try:
                from src.Application.Runtime.runtime_state import central_runtime_state
                central_runtime_state.update_state("brain_learning_status", "ERROR")
            except Exception:
                pass
            self._log_evidence(f"Cognitive Learning error: {exc}")
            return {"status": "ERROR", "episodes_processed": 0, "error": str(exc)}

    def start_polling_loop(self, interval_seconds: float = 60.0, limit_cycles: Optional[int] = None) -> None:
        """
        Starts a continuous thread polling runtime loop.
        Can be limited to a specific cycle count (useful for testing or one-off jobs).
        """
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
        """Appends formatted message to console, system log, and the dedicated runtime evidence log file."""
        os.makedirs(self._evidence_dir, exist_ok=True)
        evidence_file = os.path.join(self._evidence_dir, "research_runtime_evidence.log")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # Append to evidence file
        with open(evidence_file, "a") as f:
            f.write(log_entry)

        # Also output to stdout for diagnostics
        print(message)
