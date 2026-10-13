"""Long-running DEMO-only worker for YarTrader's Base hierarchy/reaction model."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Global namespace is required because Task Scheduler can launch workers in
# different Windows sessions. Keep the handle alive for the worker lifetime.
_worker_lock_handle = None


def acquire_single_worker_lock() -> bool:
    global _worker_lock_handle
    if os.name != "nt":
        return True
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, True, r"Global\YarTrader_BaseBehaviorDemoWorker")
    if not handle:
        raise OSError(
            f"Could not create DEMO worker singleton mutex (WinError {ctypes.get_last_error()})."
        )
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _worker_lock_handle = handle
    return True


if __name__ == "__main__":
    acquired = acquire_single_worker_lock()
    instance_log = ROOT / "runtime_logs" / "base_behavior_runtime" / "worker_instances.log"
    instance_log.parent.mkdir(parents=True, exist_ok=True)
    with instance_log.open("a", encoding="utf-8") as stream:
        stream.write(
            f"{__import__('datetime').datetime.now().astimezone().isoformat()} "
            f"pid={os.getpid()} ppid={os.getppid()} lock={acquired}\n"
        )
    if not acquired:
        print(
            "Another Base DEMO worker already holds the singleton lock; exiting without trading.",
            flush=True,
        )
        raise SystemExit(0)
    from src.Execution.Services.autonomous_demo_trader import run_autonomous_demo_trading_loop

    run_autonomous_demo_trading_loop()
