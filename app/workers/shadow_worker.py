import time
import traceback
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
        self.status = "STARTING"
        self.engine = ShadowTradingEngine.get_instance()
        self.consecutive_failures = 0
        central_runtime_state.update_state("shadow_status", "Starting")

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.status = "STARTING"
        central_runtime_state.update_state("shadow_status", "Starting")
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ShadowWorker")
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("shadow_status", "Stopped")
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        self.status = "RUNNING"
        central_runtime_state.update_state("shadow_status", "Running")

        while self.is_running:
            try:
                # Call tick_update heartbeat safely
                self.engine.tick_update()
                self.last_run_time = datetime.now()
                self.consecutive_failures = 0

                # If there are no open positions, report IDLE state to avoid confusing users, otherwise RUNNING
                open_positions = len(self.engine.account.get_open_positions())
                if open_positions == 0:
                    self.status = "IDLE"
                    central_runtime_state.update_state("shadow_status", "IDLE")
                else:
                    self.status = "RUNNING"
                    central_runtime_state.update_state("shadow_status", "Running")

            except Exception as e:
                self.consecutive_failures += 1
                tb = traceback.format_exc()
                timestamp = datetime.now().isoformat()

                # Format complete diagnostic logs as requested
                error_msg = f"[SHADOW_WORKER_ERROR]\ntime: {timestamp}\nerror: {str(e)}\ntraceback:\n{tb}\n"
                print(error_msg)

                # Write to dedicated service log file
                try:
                    with open("logs/service/service.log", "a", encoding="utf-8") as f:
                        f.write(error_msg)
                except Exception:
                    pass

                if self.consecutive_failures >= 3:
                    self.status = "FAILED"
                    central_runtime_state.update_state("shadow_status", "Failed")
                else:
                    self.status = "RECOVERING"
                    central_runtime_state.update_state("shadow_status", "Recovering")

                # Sleep and recover
                time.sleep(5.0)

            # Responsive sleep loop
            sleep_elapsed = 0.0
            while sleep_elapsed < self.interval_sec and self.is_running:
                time.sleep(0.5)
                sleep_elapsed += 0.5

        self.status = "STOPPED"
        central_runtime_state.update_state("shadow_status", "Stopped")
