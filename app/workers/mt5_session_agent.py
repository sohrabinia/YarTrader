"""Interactive-session entrypoint for the MT5 Session-2 bridge."""
import os
import subprocess
import sys

from src.Infrastructure.mt5_session_bridge import run_agent


if __name__ == "__main__":
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
