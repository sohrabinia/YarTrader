import os
import sys
import time
import signal
import threading
import uvicorn
from datetime import datetime
from typing import Any, Dict, Optional

# Set working directory to project root relative to this file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.chdir(project_root)
sys.path.insert(0, project_root)

# Signal to web_dashboard to bypass duplicate background worker loops
os.environ["TRADEYAR_SERVICE_RUN"] = "True"

# Ensure logs/service directory exists
try:
    os.makedirs(os.path.join("logs", "service"), exist_ok=True)
except Exception:
    pass

def log_service_message(message: str) -> None:
    """Logs dedicated service messages directly to logs/service/service.log and main application.log."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [SERVICE] {message}\n"
    try:
        with open(os.path.join("logs", "service", "service.log"), "a", encoding="utf-8") as f:
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

class TradeYarAIServiceHost:
    """Orchestrator for the TradeYar-AI Windows Service runtime and background workers."""
    def __init__(self, config: Optional[ProductionConfig] = None) -> None:
        self.config = config or ProductionConfig()
        self.is_running = False
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

        log_service_message("Service Started")
        central_runtime_state.update_state("worker_status", "Running")

        # 1. Start background workers based on configuration
        try:
            if self.config.workers_research:
                log_service_message("Workers Started — Research Worker")
                self.research_worker.start()

            if self.config.workers_intelligence:
                log_service_message("Workers Started — Intelligence Worker")
                self.intelligence_worker.start()

            log_service_message("Workers Started — Shadow Trading Worker")
            self.shadow_worker.start()
        except Exception as e:
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
            self.uvicorn_thread = threading.Thread(
                target=self.uvicorn_server.run,
                daemon=True,
                name="FastAPIServer"
            )
            self.uvicorn_thread.start()
            log_service_message(f"FastAPI Started at http://{self.config.api_host}:{self.config.api_port}")
        except Exception as e:
            log_service_message(f"Exception during FastAPI startup: {str(e)}")

    def stop(self) -> None:
        """Stops all background processes and API server gracefully."""
        if not self.is_running:
            return
        self.is_running = False

        log_service_message("Shutdown Requested")
        central_runtime_state.update_state("worker_status", "Stopped")

        # 1. Stop workers
        try:
            self.research_worker.stop()
            self.intelligence_worker.stop()
            self.shadow_worker.stop()
        except Exception as e:
            log_service_message(f"Exception during worker shutdown: {str(e)}")

        # 2. Stop Uvicorn FastAPI server
        try:
            if self.uvicorn_server:
                self.uvicorn_server.should_exit = True
                if self.uvicorn_thread:
                    self.uvicorn_thread.join(timeout=5.0)
        except Exception as e:
            log_service_message(f"Exception during FastAPI shutdown: {str(e)}")

        log_service_message("Service Stopped")


if WINDOWS_SERVICE_SUPPORTED:
    class TradeYarAIWindowsService(win32serviceutil.ServiceFramework):
        """Native Windows Service Lifecycle handler for TradeYar-AI."""
        _svc_name_ = "TradeYar-AI"
        _svc_display_name_ = "TradeYar AI Production Runtime Service"
        _svc_description_ = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.host = TradeYarAIServiceHost()

        def SvcStop(self):
            # Report stop pending to SCM
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.host.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            try:
                # Log started state natively to Windows Event Viewer and files
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(self)
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )

                log_service_message("Service starting up via Windows Service Control Manager (SCM)")
                # Start service host
                self.host.start()

                # Wait for SCM stop notification
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            except Exception as e:
                crash_msg = f"Windows Service Crash/Failure: {str(e)}"
                log_service_message(crash_msg)
                try:
                    import traceback
                    log_service_message(traceback.format_exc())
                    servicemanager.LogErrorMsg(f"{self._svc_name_} - {crash_msg}")
                except Exception:
                    pass
                raise
else:
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
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "remove", "start", "stop", "debug"]:
        if WINDOWS_SERVICE_SUPPORTED:
            win32serviceutil.HandleCommandLine(TradeYarAIWindowsService)
        else:
            log_service_message("Windows Service packages are not installed on this system. Running standalone instead...")
            run_standalone()
    else:
        # Check if run by the Windows Service Control Manager (SCM)
        if WINDOWS_SERVICE_SUPPORTED:
            # Handle native SCM run dispatching
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(TradeYarAIWindowsService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            run_standalone()
