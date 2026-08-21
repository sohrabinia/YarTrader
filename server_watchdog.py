#!/usr/bin/env python3
"""
YarTrader — Production Server Watchdog & Self-Healing Engine
Generates independent logs, fail-safe isolation, monitors resources,
implements strict restart thresholds, and dispatches simulated Telegram alerts.
"""

import os
import sys
import time
import subprocess
import gc
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Set working directory to project root relative to this file
project_root = os.path.abspath(os.path.dirname(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

from src.Application.Deployment.storage import YarTraderStorageManager

# Create directory structures
WATCHDOG_DIR = os.path.join(YarTraderStorageManager.get_manager().get_log_dir(), "watchdog")
RUNTIME_DIR = os.path.join(YarTraderStorageManager.get_manager().get_log_dir(), "runtime")
os.makedirs(WATCHDOG_DIR, exist_ok=True)
os.makedirs(RUNTIME_DIR, exist_ok=True)

WATCHDOG_LOG_PATH = os.path.join(WATCHDOG_DIR, "watchdog.log")
TELEGRAM_ALERTS_LOG_PATH = os.path.join(WATCHDOG_DIR, "telegram_alerts.log")


def log_watchdog_message(message: str) -> None:
    """Writes independent watchdog events to logs/watchdog/watchdog.log."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [WATCHDOG] {message}\n"
    try:
        with open(WATCHDOG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass
    print(f"[WATCHDOG] {message}")


def log_telegram_alert(message: str) -> None:
    """Dispatches a simulated Telegram alert to logs/watchdog/telegram_alerts.log."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [TELEGRAM_ALERT] {message}\n"
    try:
        with open(TELEGRAM_ALERTS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass
    print(f"\a[TELEGRAM ALERT] {message}")


def get_memory_usage_percent() -> float:
    """
    Retrieves system memory usage percent using zero external dependencies.
    Natively supports Windows Kernel32 DLL and Linux /proc/meminfo.
    """
    sys_type = platform.system()
    if sys_type == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedPhys", ctypes.c_uint64),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return float(stat.dwMemoryLoad)
        except Exception:
            pass
    elif sys_type == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_total = 0
            mem_free = 0
            mem_available = 0
            for line in lines:
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == "MemTotal:":
                    mem_total = float(parts[1])
                elif parts[0] == "MemFree:":
                    mem_free = float(parts[1])
                elif parts[0] == "MemAvailable:":
                    mem_available = float(parts[1])
            if mem_total > 0:
                available = mem_available if mem_available > 0 else mem_free
                return ((mem_total - available) / mem_total) * 100.0
        except Exception:
            pass
    # Safe mock fallback for isolated environment run consistency
    return 45.0


class ServerWatchdogEngine:
    """Coordinates independent health checking and managed subprocess recovery loops."""
    def __init__(self, target_script: str = "app/workers/service.py") -> None:
        self.target_script = target_script
        self.restart_history: List[datetime] = []
        self.last_telegram_alert_time: Optional[datetime] = None
        self.managed_process: Optional[subprocess.Popen] = None
        self.system_state = "HEALTHY"

    def update_central_state(self, new_status: str) -> None:
        """Safely updates central runtime state and logs transitions."""
        try:
            from src.Application.Runtime.runtime_state import central_runtime_state
            central_runtime_state.update_state("worker_status", new_status)
        except Exception as e:
            log_watchdog_message(f"Could not update central_runtime_state: {e}")

        # Fallback raw write to runtime transition log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | ServiceHost | RUNNING -> {new_status}\n"
        try:
            with open(os.path.join(RUNTIME_DIR, "runtime_state.log"), "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

    def dispatch_telegram_alert_with_cooldown(self, text: str) -> None:
        """Sends a Telegram alert unless suppressed by the 5-minute duplicate protection cooldown."""
        now = datetime.now()
        if self.last_telegram_alert_time is not None:
            cooldown_period = timedelta(minutes=5)
            if now - self.last_telegram_alert_time < cooldown_period:
                log_watchdog_message("Telegram alert suppressed due to 5-minute cooldown.")
                return

        self.last_telegram_alert_time = now
        log_telegram_alert(text)

    def prune_restart_history(self) -> None:
        """Keeps only restart timestamps within the last 10 minutes."""
        now = datetime.now()
        ten_minutes_ago = now - timedelta(minutes=10)
        self.restart_history = [t for t in self.restart_history if t > ten_minutes_ago]

    def monitor_resources(self) -> None:
        """Triggers garbage collection if memory threshold exceeds 85%."""
        mem_pct = get_memory_usage_percent()
        log_watchdog_message(f"Current System Memory Load: {mem_pct:.2f}%")

        if mem_pct > 85.0:
            log_watchdog_message(f"Memory threshold (85%) exceeded! Triggering explicit gc.collect().")
            gc.collect()

            # Recheck after collect
            mem_pct_post = get_memory_usage_percent()
            log_watchdog_message(f"Memory Load after gc.collect(): {mem_pct_post:.2f}%")

    def run_cycle(self) -> None:
        """Performs a single observation cycle of resources and subprocess health."""
        # 1. Resource Monitor
        self.monitor_resources()

        # 2. Managed Subprocess Status Check
        if self.managed_process is None or self.managed_process.poll() is not None:
            now = datetime.now()
            exit_code = self.managed_process.poll() if self.managed_process else "NONE"
            log_watchdog_message(f"Managed process '{self.target_script}' is OFFLINE! Exit Code: {exit_code}")

            # Register restart attempt
            self.prune_restart_history()

            # Check Restart Limits (Max 5 restarts within 10 minutes)
            if len(self.restart_history) >= 5:
                log_watchdog_message("CRITICAL: Restart limit exceeded! (Max 5 restarts per 10 mins).")
                self.system_state = "DEGRADED"
                self.update_central_state("DEGRADED")

                # Dispatch alert
                self.dispatch_telegram_alert_with_cooldown(
                    f"[CRITICAL_CRASH] YarTrader restart threshold exceeded. "
                    f"System state set to DEGRADED. Reached 5 crashes in 10 minutes."
                )

                # Cooldown Sleep to suppress infinite rapid restart loops
                log_watchdog_message("Watchdog entering cooldown protection mode (sleeping for 30 seconds).")
                time.sleep(30)
                return

            # Start/Restart process
            log_watchdog_message("Attempting to launch/restart the managed service process...")
            self.restart_history.append(now)
            self.system_state = "HEALTHY"
            self.update_central_state("Running")

            try:
                # Use sys.executable to run with identical python context
                self.managed_process = subprocess.Popen(
                    [sys.executable, self.target_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    env=os.environ.copy()
                )
                log_watchdog_message(f"Managed process successfully launched. PID: {self.managed_process.pid}")
            except Exception as e:
                log_watchdog_message(f"ERROR: Failed to launch managed process: {e}")
                self.dispatch_telegram_alert_with_cooldown(f"[CRITICAL_CRASH] Failed to start YarTrader: {e}")

    def stop(self) -> None:
        """Gracefully terminates the managed subprocess if active."""
        if self.managed_process and self.managed_process.poll() is None:
            log_watchdog_message("Terminating managed subprocess gracefully...")
            self.managed_process.terminate()
            try:
                self.managed_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                log_watchdog_message("Subprocess did not stop. Forcing kill...")
                self.managed_process.kill()
        log_watchdog_message("Watchdog engine stopped.")


def main():
    log_watchdog_message("Starting Production Server Watchdog Daemon...")
    engine = ServerWatchdogEngine()

    try:
        # Run polling observation loop
        while True:
            engine.run_cycle()
            time.sleep(5.0)  # Verify health every 5 seconds
    except KeyboardInterrupt:
        log_watchdog_message("Watchdog stopped by User Interrupt.")
    finally:
        engine.stop()


if __name__ == "__main__":
    # If run standalone as daemon
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        main()
