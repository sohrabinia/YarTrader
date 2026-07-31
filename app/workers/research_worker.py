import time
import threading
from datetime import datetime
from typing import Optional
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state

class ResearchWorker:
    """Manages the background research worker polling loop."""
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "H1", interval_sec: float = 60.0) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.interval_sec = interval_sec
        self.runtime = ResearchRuntime(symbol=symbol, timeframe=timeframe, evidence_dir="runtime_logs")
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_analysis_time: Optional[datetime] = None
        self.last_candle_time: Optional[datetime] = None
        self.status = "IDLE"
        self.error_count = 0
        central_runtime_state.update_state("research_status", "Stopped")

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
                try:
                    res = self.runtime.run_once()
                    if not self.is_running:
                        break
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
                    if not self.is_running:
                        break
                    self.error_count += 1
                    self.status = "RECOVERING"
                    central_runtime_state.update_state("research_status", "Recovering")
                    time.sleep(min(self.interval_sec, 5.0))

                sleep_elapsed = 0.0
                while sleep_elapsed < self.interval_sec and self.is_running:
                    time.sleep(0.1)
                    sleep_elapsed += 0.1
        finally:
            self.status = "STOPPED"
            central_runtime_state.update_state("research_status", "Stopped")
