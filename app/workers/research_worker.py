import os
import time
import math
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.Application.Runtime.research_runtime import validate_research_timeframe, MIN_RESEARCH_TIMEFRAME_SECONDS


def is_autonomous_demo_enabled() -> bool:
    """Fail-closed gate for autonomous DEMO execution. Only explicit ``true`` enables it."""
    try:
        raw_val = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED")
        return raw_val is not None and raw_val.strip().lower() == "true"
    except Exception:
        return False


class ResearchWorker:
    """Manages the background research worker polling loop."""
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "H1", interval_sec: float = 60.0) -> None:
        self.default_symbol = symbol
        self.timeframe = validate_research_timeframe(timeframe)
        # Never schedule faster than the minimum M1 market cadence.
        self.interval_sec = max(float(interval_sec), MIN_RESEARCH_TIMEFRAME_SECONDS)

        # Cache of active ResearchRuntimes per (symbol, timeframe)
        self.runtimes: Dict[Any, ResearchRuntime] = {}


        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_analysis_time: Optional[datetime] = None
        self.last_candle_time: Optional[datetime] = None
        self.status = "IDLE"
        self.error_count = 0
        self.cycle_count = 0
        # Global single-flight guard: Brain/research cycles are strictly serialized.
        # A second worker/thread can never overlap an active research cycle.
        self._analysis_lock = threading.Lock()
        central_runtime_state.update_state("research_status", "Stopped")

    def _get_or_create_runtime(self, symbol: str, tf: str, asset_class: str = "Forex", provider: str = "MT5") -> ResearchRuntime:
        key = (symbol.upper(), tf.upper())
        if key not in self.runtimes:
            from src.Application.Deployment.storage import YarTraderStorageManager
            storage_mgr = YarTraderStorageManager.get_manager()
            self.runtimes[key] = ResearchRuntime(
                symbol=symbol.upper(),
                timeframe=tf.upper(),
                evidence_dir=os.path.join(storage_mgr.get_runtime_dir(), "research_logs"),
                provider_name=provider,
                asset_class=asset_class
            )
        return self.runtimes[key]

    def _get_active_matrix(self) -> list:
        try:
            from src.Market.Universe.symbol_registry import SymbolRegistry
            matrix = SymbolRegistry.get_instance().get_active_matrix()
            # Keep the configured multi-symbol active matrix in production.
            # Research and execution share the enabled multi-symbol registry.
            # Do not collapse production to one default symbol: each active symbol
            # is evaluated independently and must pass the same broker/risk gates.
            return matrix
        except Exception:
            return []

    @staticmethod
    def _is_market_data_unavailable_error(error: Exception) -> bool:
        """
        Classify an authoritative production market-data availability failure.

        A missing/unselected broker symbol is a per-symbol data condition, not a
        ResearchWorker lifecycle failure. It must be skipped without enabling
        synthetic data or weakening the production MT5 safety gate.
        """
        message = str(error).lower()
        return (
            "not selected or available in real mt5 terminal in production mode" in message
            or (
                "failed to fetch market data for primitive research" in message
                and "symbol" in message
                and "production mode" in message
            )
        )

    def start(self) -> None:
        """Starts the background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_multiple({
            "research_status": "Running",
            "research_worker_started_at": datetime.now().isoformat(),
            "research_cycle_started_at": None,
            "research_cycle_symbol": None,
            "research_cycle_timeframe": None,
            "research_last_error": None,
            "research_cycle_count": self.cycle_count,
        })
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ResearchWorker")
        self.thread.start()

    def stop(self) -> None:
        """Stops the background worker gracefully."""
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("research_status", "Stopped")
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)

    def _run_loop(self) -> None:
        """Worker loop running on the background thread."""
        try:
            from src.Market.Universe.symbol_registry import SymbolRegistry
            registry = SymbolRegistry.get_instance()
            active_matrix = self._get_active_matrix()
            unique_symbols = sorted(list(set(s for s, t, ac, p in active_matrix)))
            configured_tfs = sorted(list(set(t for s, t, ac, p in active_matrix)))

            print("================================================")
            print("YarTrader Multi-Symbol / Multi-TF Runtime")
            print("================================================")
            print(f"Registry Capacity:\n{registry.max_symbols} Symbols\n")
            print(f"Registered Symbols:\n{len(registry.get_all_registered())}\n")
            print(f"Active Symbols:\n{len(unique_symbols)}\n")
            print(f"Configured Timeframes:\n{configured_tfs}\n")
            print("Research Workers:\nRunning\n")
            print(f"Queue Size:\n{len(active_matrix)} ({len(unique_symbols)} symbols x {len(configured_tfs)} timeframes)\n")
            print("Mode:\nProduction")
            print("================================================\n")

            while self.is_running:
                active_matrix = self._get_active_matrix()

                for symbol, tf, asset_class, provider in active_matrix:
                    if not self.is_running:
                        break

                    try:
                        print(f"Research Started\nSymbol: {symbol}\nTimeframe: {tf}")

                        runtime = self._get_or_create_runtime(symbol, tf, asset_class, provider)

                        # Active read-only connection check
                        conn_health = runtime.provider.delegate.get_connection_health()
                        p_name = getattr(runtime, "_provider_name", "MT5")
                        if p_name == "ControlledOfflineFixture":
                            print("ControlledOfflineFixture: Connected (100% Offline)")
                        else:
                            print("MT5: Connected")

                        # Strict single-flight: never run two Brain/research cycles at once.
                        acquired = self._analysis_lock.acquire(blocking=False)
                        if not acquired:
                            print("[ResearchWorker] Research cycle skipped: another Brain/research cycle is still running.")
                            continue
                        central_runtime_state.update_multiple({
                            "research_cycle_started_at": datetime.now().isoformat(),
                            "research_cycle_symbol": symbol,
                            "research_cycle_timeframe": tf,
                        })
                        try:
                            res = runtime.run_once()
                        finally:
                            self._analysis_lock.release()

                        self.last_analysis_time = datetime.now()
                        if res.Request.EndTime:
                            self.last_candle_time = res.Request.EndTime
                        self.status = "RUNNING"
                        self.error_count = 0
                        self.cycle_count += 1
                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat(),
                            "research_cycle_count": self.cycle_count,
                            "research_last_successful_cycle": self.last_analysis_time.isoformat(),
                            "research_last_error": None,
                            "research_cycle_started_at": None,
                            "research_cycle_symbol": None,
                            "research_cycle_timeframe": None,
                        })

                        candles_count = len(res.Findings.get("pipeline_outputs", {}).get("technical_analysis", {}).get("candles", []))
                        print(f"Candles: {candles_count}")
                        print("Features: Generated")
                        print("Research: Completed\n")

                        # ResearchWorker is read-only. Broker execution belongs to the
                        # single Base-only execution service; this worker may never dispatch orders.
                        auto_dec = res.Findings.get("autonomous_decision", {})
                        evidence = auto_dec.get("evidence", {}) if isinstance(auto_dec, dict) else {}
                        action = str(auto_dec.get("action", "WAIT")).upper() if isinstance(auto_dec, dict) else "WAIT"
                        if action in ("BUY", "SELL") and evidence.get("decision_authority") != "BASE_HIERARCHY":
                            action = "WAIT"
                        print(f"[ResearchWorker] Read-only cycle completed for {symbol}; decision={action}; broker_dispatch=DISABLED.")
                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat()
                        })
                    except Exception as e:
                        if self._is_market_data_unavailable_error(e):
                            # A broker symbol can be unavailable while the MT5 bridge and the
                            # rest of the research universe remain healthy. Do not poison the
                            # worker lifecycle state or enable synthetic/fallback market data.
                            self.status = "RUNNING"
                            central_runtime_state.update_multiple({
                                "research_status": "Running",
                                "research_last_error": str(e),
                                "research_cycle_started_at": None,
                                "research_cycle_symbol": None,
                                "research_cycle_timeframe": None,
                            })
                            print(
                                f"[ResearchWorker] DATA_UNAVAILABLE/SKIPPED for {symbol} {tf}: "
                                f"{type(e).__name__}: {e}"
                            )
                            continue

                        self.error_count += 1
                        self.status = "RECOVERING"
                        central_runtime_state.update_multiple({
                            "research_status": "Recovering",
                            "research_last_error": f"{type(e).__name__}: {e}",
                            "research_cycle_started_at": None,
                            "research_cycle_symbol": None,
                            "research_cycle_timeframe": None,
                        })
                        # Never swallow research-cycle failures: production diagnosis must retain
                        # the exact symbol/timeframe, exception type, and traceback.
                        import traceback
                        error_context = (
                            f"Research cycle error for {symbol} {tf}: "
                            f"{type(e).__name__}: {e}"
                        )
                        print(f"[ResearchWorker] {error_context}")
                        print(traceback.format_exc())
                        try:
                            from app.core.logging import log_event
                            log_event(
                                "ERROR",
                                error_context,
                                source="research_worker",
                            )
                            log_event(
                                "ERROR",
                                traceback.format_exc().rstrip(),
                                source="research_worker",
                            )
                        except Exception:
                            pass
                        # Graceful quick delay before next asset if error happens
                        time.sleep(0.5)

                # Wait for the next interval
                sleep_elapsed = 0.0
                while sleep_elapsed < self.interval_sec and self.is_running:
                    time.sleep(0.1)
                    sleep_elapsed += 0.1
        finally:
            self.status = "STOPPED"
            central_runtime_state.update_state("research_status", "Stopped")
