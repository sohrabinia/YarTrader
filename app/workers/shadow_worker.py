import time
import threading
from datetime import datetime
from typing import Optional
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
from src.Application.Runtime.runtime_state import central_runtime_state

class ShadowWorker:
    """Manages periodic updates for Virtual Accounts and Positions within the Shadow Trading Engine."""
    def __init__(self, interval_sec: float = 30.0) -> None:
        self.interval_sec = interval_sec
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_run_time: Optional[datetime] = None
        self.status = "IDLE"
        self.engine = ShadowTradingEngine.get_instance()
        central_runtime_state.update_state("shadow_status", "Stopped")

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_state("shadow_status", "Running")
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ShadowWorker")
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("shadow_status", "Stopped")
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        while self.is_running:
            try:
                self.engine.tick_update()
                self.last_run_time = datetime.now()
                self.status = "RUNNING"
                central_runtime_state.update_state("shadow_status", "Running")
            except Exception:
                self.status = "RECOVERING"
                central_runtime_state.update_state("shadow_status", "Recovering")

            sleep_elapsed = 0.0
            while sleep_elapsed < self.interval_sec and self.is_running:
                time.sleep(0.5)
                sleep_elapsed += 0.5
