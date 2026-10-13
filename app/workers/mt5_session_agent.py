"""Interactive-session entrypoint for the MT5 Session-2 bridge."""
import os
import subprocess
import sys

from src.Infrastructure.mt5_session_bridge import run_agent

_SESSION_MUTEX_HANDLE = None

def _acquire_session_singleton() -> bool:
    global _SESSION_MUTEX_HANDLE
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, True, r"Local\YarTraderMT5SessionAgent")
    if not handle:
        raise OSError(f"Could not create MT5 session agent mutex (WinError {ctypes.get_last_error()}).")
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
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
