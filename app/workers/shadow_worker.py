import time
import threading
from datetime import datetime
from typing import Optional
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine

class ShadowWorker:
    """Manages periodic updates for Virtual Accounts and Positions within the Shadow Trading Engine."""
    def __init__(self, interval_sec: float = 30.0) -> None:
        self.interval_sec = interval_sec
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_run_time: Optional[datetime] = None
        self.status = "IDLE"
        self.engine = ShadowTradingEngine.get_instance()

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ShadowWorker")
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        self.status = "STOPPED"
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        while self.is_running:
            try:
                self.engine.tick_update()
                self.last_run_time = datetime.now()
                self.status = "RUNNING"
            except Exception:
                self.status = "RECOVERING"

            sleep_elapsed = 0.0
            while sleep_elapsed < self.interval_sec and self.is_running:
                time.sleep(0.5)
                sleep_elapsed += 0.5
