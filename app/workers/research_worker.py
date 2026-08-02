import time
import threading
from datetime import datetime
from typing import Optional, Dict
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine

class ResearchWorker:
    """Manages the background research worker polling loop."""
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "H1", interval_sec: float = 60.0) -> None:
        self.default_symbol = symbol
        self.timeframe = timeframe
        self.interval_sec = interval_sec

        # Cache of active ResearchRuntimes per symbol
        self.runtimes: Dict[str, ResearchRuntime] = {}

        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_analysis_time: Optional[datetime] = None
        self.last_candle_time: Optional[datetime] = None
        self.status = "IDLE"
        self.error_count = 0
        central_runtime_state.update_state("research_status", "Stopped")

    def _get_or_create_runtime(self, symbol: str) -> ResearchRuntime:
        symbol_upper = symbol.upper()
        if symbol_upper not in self.runtimes:
            self.runtimes[symbol_upper] = ResearchRuntime(
                symbol=symbol_upper,
                timeframe=self.timeframe,
                evidence_dir="runtime_logs"
            )
        return self.runtimes[symbol_upper]

    def _get_active_symbols(self) -> list:
        # 1. Fetch symbols from the PredictiveShadowEngine contexts
        try:
            engine = PredictiveShadowEngine.get_instance()
            contexts_symbols = [ctx.symbol.upper() for ctx in engine.contexts.values()]
        except Exception:
            contexts_symbols = []

        # 2. Add our default and system limits allowed assets
        default_symbols = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "ETHUSD"]
        if self.default_symbol.upper() not in default_symbols:
            default_symbols.append(self.default_symbol.upper())

        # Combine, preserve order, and filter duplicates
        seen = set()
        all_symbols = []
        for s in (contexts_symbols + default_symbols):
            if s not in seen:
                seen.add(s)
                all_symbols.append(s)

        # Cap list to active symbols ceiling limit governed by config/system_limits.yaml
        return all_symbols[:30]

    def start(self) -> None:
        """Starts the background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_state("research_status", "Running")
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ResearchWorker")
        self.thread.start()

    def stop(self) -> None:
        """Stops the background worker gracefully."""
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("research_status", "Stopped")
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        """Worker loop running on the background thread."""
        try:
            while self.is_running:
                active_symbols = self._get_active_symbols()

                for symbol in active_symbols:
                    if not self.is_running:
                        break

                    try:
                        runtime = self._get_or_create_runtime(symbol)
                        res = runtime.run_once()

                        self.last_analysis_time = datetime.now()
                        if res.Request.EndTime:
                            self.last_candle_time = res.Request.EndTime
                        self.status = "RUNNING"
                        self.error_count = 0

                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat()
                        })
                    except Exception as e:
                        self.error_count += 1
                        self.status = "RECOVERING"
                        central_runtime_state.update_state("research_status", "Recovering")
                        # Graceful quick delay before next asset if error happens
                        time.sleep(0.5)

                # Wait for the next interval
                sleep_elapsed = 0.0
                while sleep_elapsed < self.interval_sec and self.is_running:
                    time.sleep(0.1)
                    sleep_elapsed += 0.1
        finally:
            self.status = "STOPPED"
            central_runtime_state.update_state("research_status", "Stopped")
