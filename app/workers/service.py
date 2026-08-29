import os
import sys
import site

# 1. Forensic virtual environment site-packages bootstrap
# Set working directory to project root relative to this file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.chdir(project_root)

# Prepend project root to sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Locate and dynamically add the virtual environment's site-packages to sys.path
# This ensures pythonservice.exe (running as LocalSystem) can find uvicorn, fastapi, etc.
venv_site_packages = os.path.join(project_root, ".venv", "Lib", "site-packages")
if os.path.isdir(venv_site_packages):
    site.addsitedir(venv_site_packages)

import time
import socket
import signal
import threading
import uvicorn
from datetime import datetime
from typing import Any, Dict, Optional

# Signal to web_dashboard to bypass duplicate background worker loops
os.environ["TRADEYAR_SERVICE_RUN"] = "True"
os.environ["YARTRADER_SERVICE_RUN"] = "True"

from src.Application.Deployment.storage import YarTraderStorageManager

def _get_service_log_file() -> str:
    storage_mgr = YarTraderStorageManager.get_manager()
    service_log_dir = os.path.join(storage_mgr.get_logs_dir(), "service")
    os.makedirs(service_log_dir, exist_ok=True)
    return os.path.join(service_log_dir, "service.log")

def log_service_message(message: str) -> None:
    """Logs dedicated service messages directly to TradeYarStorageRoot/Logs/service/service.log and main application.log."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [SERVICE] {message}\n"
    try:
        log_file = _get_service_log_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass
    print(message)

    # Mirroring to application.log
    try:
        from app.core.logging import log_event
        level = "INFO"
        if "crash" in message.lower() or "exception" in message.lower() or "error" in message.lower() or "fail" in message.lower():
            level = "ERROR"
        log_event(level, f"Service Host: {message}", source="service_host")
    except Exception:
        pass

from app.core.config import ProductionConfig
from app.workers.research_worker import ResearchWorker
from app.workers.intelligence_worker import IntelligenceWorker
from app.workers.shadow_worker import ShadowWorker
from src.Application.Runtime.runtime_state import central_runtime_state

# Import existing FastAPI app
from src.Application.Services.web_dashboard import app as fastapi_app

# Dual Mode: Check if we are running as a Windows Service
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WINDOWS_SERVICE_SUPPORTED = True
except ImportError:
    WINDOWS_SERVICE_SUPPORTED = False

class YarTraderServiceHost:
    """Orchestrator for the YarTrader Windows Service runtime and background workers."""
    def __init__(self, config: Optional[ProductionConfig] = None) -> None:
        self.config = config or ProductionConfig()
        self.is_running = False
        self.fastapi_ready = False
        self.last_error: Optional[str] = None
        self.uvicorn_server: Optional[uvicorn.Server] = None
        self.uvicorn_thread: Optional[threading.Thread] = None

        # Instantiate workers
        self.research_worker = ResearchWorker(
            symbol=self.config.mt5_symbol,
            timeframe=self.config.mt5_timeframe
        )
        self.intelligence_worker = IntelligenceWorker()
        self.shadow_worker = ShadowWorker()

    def start(self) -> None:
        """Starts all background processes, API, and worker threads."""
        if self.is_running:
            return
        self.is_running = True
        self.fastapi_ready = False

        log_service_message("Service Started")
        central_runtime_state.update_state("worker_status", "Running")

        # 1. Start background workers based on configuration
        try:
            if self.config.workers_research:
                log_service_message("Workers Started — Research Worker")
                self.research_worker.start()

            # Continuous IntelligenceWorker is deprecated and removed from orchestration.
            # Active startup dependency has been completely removed to avoid server CPU pressure.
            log_service_message("Workers Started — Intelligence Worker (DEPRECATED/SKIPPED)")

            log_service_message("Workers Started — Shadow Trading Worker")
            self.shadow_worker.start()
        except Exception as e:
            self.last_error = f"Worker startup exception: {str(e)}"
            log_service_message(f"Exception during worker startup: {str(e)}")

        # 2. Start Uvicorn FastAPI Server on background thread
        try:
            uvicorn_config = uvicorn.Config(
                app=fastapi_app,
                host=self.config.api_host,
                port=self.config.api_port,
                log_level=self.config.logging_level.lower(),
                loop="asyncio"
            )
            self.uvicorn_server = uvicorn.Server(uvicorn_config)

            def _run_uvicorn():
                try:
                    self.uvicorn_server.run()
                except BaseException as crash_err:
                    self.fastapi_ready = False
                    self.last_error = f"Uvicorn server crashed: {str(crash_err)}"
                    log_service_message(f"Uvicorn Thread Exception: {str(crash_err)}")

            self.uvicorn_thread = threading.Thread(
                target=_run_uvicorn,
                daemon=True,
                name="FastAPIServer"
            )
            self.uvicorn_thread.start()

            # Confirm socket binding readiness
            self._verify_uvicorn_readiness()
        except Exception as e:
            self.fastapi_ready = False
            self.last_error = f"FastAPI startup exception: {str(e)}"
            log_service_message(f"Exception during FastAPI startup: {str(e)}")

    def _verify_uvicorn_readiness(self, timeout_sec: float = 5.0) -> bool:
        """Polls server state or socket availability before declaring FastAPI started."""
        start_time = time.time()
        host = self.config.api_host
        port = self.config.api_port

        while time.time() - start_time < timeout_sec:
            if self.uvicorn_server and getattr(self.uvicorn_server, "started", False):
                self.fastapi_ready = True
                log_service_message(f"FastAPI Started and Listening at http://{host}:{port}")
                return True

            # Fallback socket connectivity probe
            try:
                with socket.create_connection((host, port), timeout=0.2):
                    self.fastapi_ready = True
                    log_service_message(f"FastAPI Started and Verified Listening at http://{host}:{port}")
                    return True
            except (OSError, ConnectionRefusedError):
                pass

            time.sleep(0.1)

        # Timeout reached
        if self.uvicorn_server and getattr(self.uvicorn_server, "started", False):
            self.fastapi_ready = True
            log_service_message(f"FastAPI Started at http://{host}:{port}")
            return True

        self.fastapi_ready = False
        log_service_message(f"FastAPI socket listener probe failed on http://{host}:{port}")
        return False

    def stop(self) -> None:
        """Stops all background processes and API server gracefully."""
        if not self.is_running:
            return
        self.is_running = False
        self.fastapi_ready = False

        log_service_message("Shutdown Requested")
        central_runtime_state.update_state("worker_status", "Stopped")

        # 1. Stop workers
        try:
            self.research_worker.stop()
            self.shadow_worker.stop()
        except Exception as e:
            log_service_message(f"Exception during worker shutdown: {str(e)}")

        # 2. Stop Uvicorn FastAPI server
        try:
            if self.uvicorn_server:
                self.uvicorn_server.should_exit = True
                if self.uvicorn_thread and self.uvicorn_thread.is_alive():
                    self.uvicorn_thread.join(timeout=5.0)
        except Exception as e:
            log_service_message(f"Exception during FastAPI shutdown: {str(e)}")

        log_service_message("Service Stopped")


# Backward compatibility alias
TradeYarAIServiceHost = YarTraderServiceHost


if WINDOWS_SERVICE_SUPPORTED:
    class YarTraderWindowsService(win32serviceutil.ServiceFramework):
        """Native Windows Service Lifecycle handler for YarTrader."""
        _svc_name_ = "YarTrader"
        _svc_display_name_ = "YarTrader Production Runtime Service"
        _svc_description_ = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."
        _exe_path_ = sys.executable

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.host = YarTraderServiceHost()

        def SvcStop(self):
            log_service_message("SERVICE_STOP_REQUESTED")
            # Report stop pending to SCM
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.host.stop()
            log_service_message("SERVICE_HOST_STOPPED")
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            try:
                log_service_message("SERVICE_START_REQUESTED")
                # Start service host
                self.host.start()
                log_service_message("SERVICE_HOST_STARTED")

                # Report RUNNING status to SCM
                self.ReportServiceStatus(win32service.SERVICE_RUNNING)
                log_service_message("SERVICE_RUNNING")

                # Wait for SCM stop notification
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
                log_service_message("SERVICE_STOPPED")
            except Exception as e:
                log_service_message("SERVICE_START_FAILURE")
                crash_msg = f"Windows Service Crash/Failure: {str(e)}"
                log_service_message(crash_msg)
                try:
                    import traceback
                    log_service_message(traceback.format_exc())
                    if WINDOWS_SERVICE_SUPPORTED:
                        servicemanager.LogErrorMsg(f"{self._svc_name_} - {crash_msg}")
                except Exception:
                    pass
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)
                raise

    # Backward compatibility alias
    TradeYarAIWindowsService = YarTraderWindowsService
else:
    class YarTraderWindowsService:
        pass
    class TradeYarAIWindowsService:
        pass


def run_standalone():
    """Standalone CLI process entrypoint with SIGINT/SIGTERM signal handling."""
    host = TradeYarAIServiceHost()

    def handle_signal(signum, frame):
        log_service_message(f"Received signal {signum}. Shutting down...")
        host.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        log_service_message("Starting standalone console runner...")
        host.start()

        while host.is_running:
            time.sleep(1.0)
    except Exception as e:
        crash_msg = f"Standalone Service Crash/Failure: {str(e)}"
        log_service_message(crash_msg)
        try:
            import traceback
            log_service_message(traceback.format_exc())
        except Exception:
            pass
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "remove", "start", "stop", "debug", "update"]:
        if WINDOWS_SERVICE_SUPPORTED:
            win32serviceutil.HandleCommandLine(TradeYarAIWindowsService)
        else:
            log_service_message("Windows Service packages are not installed on this system. Running standalone instead...")
            run_standalone()
    else:
        # Check if run by the Windows Service Control Manager (SCM)
        if WINDOWS_SERVICE_SUPPORTED:
            try:
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(TradeYarAIWindowsService)
                servicemanager.StartServiceCtrlDispatcher()
            except Exception as e:
                # If we cannot connect to SCM (e.g. running interactively), fallback to standalone console
                winerr = getattr(e, "winerror", None)
                if winerr == 1063:  # ERROR_FAILED_SERVICE_CONTROLLER_CONNECT
                    run_standalone()
                else:
                    log_service_message(f"SCM dispatcher failed: {str(e)}. Falling back to standalone...")
                    run_standalone()
        else:
            run_standalone()
