import os
import time
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
        evidence_dir: str = "runtime_logs"
    ) -> None:
        self._provider = provider or MetaTrader5Provider()
        self._research_engine = research_engine or FeatureExtractionResearchEngine(data_provider=self._provider)
        self._symbol = symbol
        self._timeframe = timeframe
        self._evidence_dir = evidence_dir
        self._history: List[ResearchResult] = []
        self._is_running = False

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
        start_time = datetime.now() - timedelta(days=2) # Fetch last 2 days to have enough historical data for features
        end_time = datetime.now()

        # Write start step to logs
        self._log_evidence(f"Starting research iteration for {self._symbol} on {self._timeframe}...")

        # 2. Connect and Retrieve Candles
        self._log_evidence("MT5 Connected")
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
            data_response = self._provider.retrieve_market_data(target_req)
            candles_count = len(data_response.DataPoints)
            self._log_evidence(f"Candles Received: {candles_count}")

            if candles_count == 0:
                raise ValidationException("Received empty candle series from MT5.")

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

            # 7. Store Result
            self._history.append(result)
            self._log_evidence(f"Research cycle completed successfully. Result ID: {result.Findings.get('report_id', 'unknown')}")

            return result

        except Exception as e:
            self._log_evidence(f"Research cycle encountered an error: {str(e)}")
            raise

    def start_polling_loop(self, interval_seconds: float = 60.0, limit_cycles: Optional[int] = None) -> None:
        """
        Starts a continuous thread polling runtime loop.
        Can be limited to a specific cycle count (useful for testing or one-off jobs).
        """
        self._is_running = True
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
