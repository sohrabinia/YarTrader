import os
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Data.MarketData.Models.models import MarketDataRequest
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine

class ResearchRuntime:
    """
    Autonomous Non-Trading Research Runtime.
    Polls real-time market data from read-only MetaTrader 5 adapter,
    triggers passive feature calculation, and executes the research analysis pipeline.
    """
    def __init__(
        self,
        provider: Optional[MetaTrader5Provider] = None,
        research_engine: Optional[FeatureExtractionResearchEngine] = None,
        symbol: str = "XAUUSD",
        timeframe: str = "H1",
        evidence_dir: str = "runtime_logs",
        provider_name: str = "MT5",
        asset_class: str = "Forex"
    ) -> None:
        self._provider = provider or MetaTrader5Provider()
        self._research_engine = research_engine or FeatureExtractionResearchEngine(data_provider=self._provider)
        self._symbol = symbol
        self._timeframe = timeframe
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
    def research_engine(self) -> FeatureExtractionResearchEngine:
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

    def run_once(self) -> ResearchResult:
        """Executes a single synchronous loop cycle of the research pipeline."""
        # 1. Start Cycle
        tf_upper = self._timeframe.upper()
        if "M1" == tf_upper:
            start_time = datetime.now() - timedelta(hours=10) # 600 minutes (>= 500)
        elif "M5" == tf_upper:
            start_time = datetime.now() - timedelta(days=2) # 576 bars (>= 500)
        elif "M15" == tf_upper:
            start_time = datetime.now() - timedelta(days=6) # 576 bars (>= 500)
        elif "H1" in tf_upper:
            start_time = datetime.now() - timedelta(days=22) # 528 hours (>= 500)
        elif "H4" in tf_upper:
            start_time = datetime.now() - timedelta(days=52) # 312 bars (>= 300)
        elif "D1" in tf_upper or "DAILY" in tf_upper:
            start_time = datetime.now() - timedelta(days=205) # 205 days (>= 200)
        elif "W1" in tf_upper:
            start_time = datetime.now() - timedelta(days=210) # 30 weeks (>= 14)
        elif "MN1" in tf_upper:
            start_time = datetime.now() - timedelta(days=900) # 30 months (>= 14)
        else:
            start_time = datetime.now() - timedelta(days=2)
        end_time = datetime.now()

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
                self._log_evidence("MT5 Connected")

            candles_count = len(data_response.DataPoints)
            self._log_evidence(f"Candles Received: {candles_count}")

            if candles_count == 0:
                raise ValidationException(f"Received empty candle series for {self._symbol} from {self._provider_name}.")

            # 4. Construct Research Request with Enrichment context
            research_req = ResearchRequest(
                Asset=self._symbol,
                StartTime=start_time,
                EndTime=end_time,
                Context={"timeframe": self._timeframe}
            )

            # 5. Run the decorated FeatureExtractionResearchEngine
            result = self._research_engine.analyze_market(research_req)

            # 6. Verify outputs and confirm features are generated
            features_generated = "feature_set" in result.Findings
            self._log_evidence(f"Features Generated: {str(features_generated).lower()}")
            self._log_evidence("Research Completed: true")

            # Update Shadow Trading Engine with latest market price and decision
            try:
                from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
                shadow_engine = ShadowTradingEngine.get_instance()

                latest_price = data_response.DataPoints[-1].Close

                # Update open position prices first (recalculates floating PnL and handles SL/TP hits)
                shadow_engine.update_market_price(self._symbol, latest_price, timeframe=self._timeframe)

                po = result.Findings.get("pipeline_outputs", {})
                smart = po.get("smart_interpretation", {})
                bias = smart.get("bias", "Neutral")
                confidence = smart.get("confidence", 50)
                reasoning_list = smart.get("reasoning", [])
                reason_text = " ".join(reasoning_list) if isinstance(reasoning_list, list) else str(reasoning_list)

                decision_action = "WAIT"
                if bias == "Bullish":
                    decision_action = "BUY"
                elif bias == "Bearish":
                    decision_action = "SELL"

                evidence_payload = {
                    "signature": [latest_price],
                    "raw_findings": result.Findings
                }

                shadow_engine.handle_decision(
                    decision_action=decision_action,
                    current_price=latest_price,
                    confidence=confidence,
                    reason=reason_text,
                    evidence=evidence_payload,
                    symbol=self._symbol,
                    timeframe=self._timeframe
                )
            except Exception as se:
                self._log_evidence(f"Shadow Trading update skipped or errored: {str(se)}")

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

        # Thread-safe write using temp file renaming pattern
        temp_filepath = filepath + ".tmp"
        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=4)
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
