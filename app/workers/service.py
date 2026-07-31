import os
import sys
import time
import signal
import threading
import uvicorn
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import ProductionConfig
from app.workers.research_worker import ResearchWorker
from app.workers.intelligence_worker import IntelligenceWorker
from app.workers.shadow_worker import ShadowWorker

from src.Application.Services.web_dashboard import app as fastapi_app

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

        print("Starting TradeYar AI Production Service...")

        if self.config.workers_research:
            print("Starting Research Worker...")
            self.research_worker.start()

        if self.config.workers_intelligence:
            print("Starting Intelligence Worker...")
            self.intelligence_worker.start()

        print("Starting Shadow Trading Worker...")
        self.shadow_worker.start()

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
        print(f"FastAPI Server active at http://{self.config.api_host}:{self.config.api_port}")

    def stop(self) -> None:
        """Stops all background processes and API server gracefully."""
        if not self.is_running:
            return
        self.is_running = False

        print("Shutting down TradeYar AI Production Service...")

        self.research_worker.stop()
        self.intelligence_worker.stop()
        self.shadow_worker.stop()

        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True
            if self.uvicorn_thread:
                self.uvicorn_thread.join(timeout=5.0)

        print("Shutdown complete.")


if WINDOWS_SERVICE_SUPPORTED:
    class TradeYarAIWindowsService(win32serviceutil.ServiceFramework):
        """Windows Service implementation for TradeYar AI."""
        _svc_name_ = "TradeYar-AI"
        _svc_display_name_ = "TradeYar AI Production Runtime Service"
        _svc_description_ = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.host = TradeYarAIServiceHost()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.host.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.host.start()
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
else:
    class TradeYarAIWindowsService:
        pass


def run_standalone():
    """Standalone CLI process entrypoint with SIGINT/SIGTERM signal handling."""
    host = TradeYarAIServiceHost()

    def handle_signal(signum, frame):
        print(f"Received signal {signum}. Shutting down...")
        host.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    host.start()

    while host.is_running:
        time.sleep(1.0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "remove", "start", "stop"]:
        if WINDOWS_SERVICE_SUPPORTED:
            win32serviceutil.HandleCommandLine(TradeYarAIWindowsService)
        else:
            print("Windows Service packages are not installed on this system. Running standalone instead...")
            run_standalone()
    else:
        run_standalone()
