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
    """Use a cross-session OS file lock; unlike a Global mutex it needs no special ACL."""
    global _worker_lock_handle
    if os.name != "nt":
        return True
    import msvcrt
    lock_path = ROOT / "runtime_logs" / "base_behavior_runtime" / ".demo_worker.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
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
