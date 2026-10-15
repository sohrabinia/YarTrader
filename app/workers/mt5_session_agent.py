"""Interactive-session entrypoint for the MT5 Session-2 bridge."""
import os
import subprocess
import sys

from src.Infrastructure.mt5_session_bridge import run_agent

_SESSION_MUTEX_HANDLE = None

def _acquire_session_singleton() -> bool:
    """Cross-session lock: MT5 bridge/supervisor must be singleton across Windows sessions."""
    global _SESSION_MUTEX_HANDLE
    if os.name != "nt":
        return True
    import msvcrt
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    lock_path = os.path.join(project_root, "runtime_logs", "base_behavior_runtime", ".mt5_session_agent.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    handle = open(lock_path, "a+b")
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
    _SESSION_MUTEX_HANDLE = handle
    return True


if __name__ == "__main__":
    if not _acquire_session_singleton():
        print("Another MT5 session agent already owns the singleton mutex; exiting.", flush=True)
        raise SystemExit(0)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    supervisor = os.path.join(project_root, "app", "workers", "mt5_backtest_supervisor.py")
    supervisor_process = None
    try:
        supervisor_process = subprocess.Popen(
            [sys.executable, supervisor],
            cwd=project_root,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        run_agent()
    finally:
        if supervisor_process is not None:
            try:
                supervisor_process.terminate()
                supervisor_process.wait(timeout=10)
            except Exception:
                try:
                    supervisor_process.kill()
                except Exception:
                    pass
