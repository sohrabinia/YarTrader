import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Data.External.interfaces import IDataProvider
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.Market.models import MarketInstrument, CandleRecord, MarketDataMetadata, MarketDataRequest, MarketDataResponse
from src.Infrastructure.exceptions import ValidationException

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


@dataclass(frozen=True)
class MT5ConnectionHealth:
    connected: bool
    terminal_path: str
    server: str
    login: int
    ping: float
    last_error: Optional[str] = None
    last_successful_fetch: Optional[str] = None


class MT5DataMapper:
    """Maps raw MT5 rates structures into standardized CandleRecord models."""
    def map_rates_to_candles(self, raw_rates: List[Dict[str, Any]]) -> List[CandleRecord]:
        candles = []
        for rate in raw_rates:
            # 1. Parse Timestamp
            try:
                ts_raw = rate.get("time") or rate.get("timestamp")
                if isinstance(ts_raw, (int, float)):
                    ts = datetime.fromtimestamp(ts_raw)
                elif isinstance(ts_raw, str):
                    ts = datetime.fromisoformat(ts_raw)
                elif isinstance(ts_raw, datetime):
                    ts = ts_raw
                else:
                    continue  # skip silently if timestamp missing
            except (ValueError, KeyError, TypeError):
                continue  # skip silently if timestamp is invalid format

            # 2. Parse Metrics (OHLCV)
            try:
                candles.append(
                    CandleRecord(
                        timestamp=ts,
                        open=float(rate["open"]),
                        high=float(rate["high"]),
                        low=float(rate["low"]),
                        close=float(rate["close"]),
                        volume=float(rate.get("tick_volume") or rate.get("volume", 0.0))
                    )
                )
            except Exception as e:
                # Raise ValidationException on bad metrics!
                raise ValidationException(f"MT5 Mapping Error: Failed to map rate entry. Details: {e}")
        return candles


class MT5DataProvider(IDataProvider):
    """
    Read-only adapter for MetaTrader 5 (MT5).
    Strictly forbids trading commands, orders, positions, and account modifications.

    ========================== SAFETY ENFORCEMENT ==========================
    FORBIDDEN:
    ❌ order_send (No execution of market or pending orders)
    ❌ positions modification (No closing, scaling, or modifying trades)
    ❌ trade requests (No execution or management of any trading activity)
    ❌ account modifications (No settings, password, or leverage changes)

    ALLOWED (Read-only metadata & historical data):
    ✅ initialize (Initialize MT5 terminal connection)
    ✅ terminal_info (Query MT5 terminal execution details)
    ✅ account_info (Read account configuration and balance details)
    ✅ symbols_get (List available instruments)
    ✅ symbol_info (Query single instrument specifications)
    ✅ copy_rates_range / copy_rates_from_pos (Fetch read-only candle records)
    ========================================================================
    """
    def __init__(
        self,
        provider_id: str = "mt5-provider",
        server: str = "Demo-Server",
        supported_symbols: Optional[List[str]] = None
    ) -> None:
        supported_symbols = supported_symbols or ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"]
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.MT5,
            supported_symbols=supported_symbols
        )
        self._server = server
        self._connected = True  # acts as an override/control flag for tests
        self._ping = 15.4
        self._mapper = MT5DataMapper()
        self._initialized = False

        # Diagnostics fields
        self._terminal_path = "C:\\Program Files\\MetaTrader 5"
        self._login = 12345678
        self._last_error = None
        self._last_successful_fetch = None

        # Attempt initialization if MT5 is available
        if MT5_AVAILABLE and mt5 is not None:
            try:
                if mt5.initialize():
                    self._initialized = True
                    self._update_diagnostics()
                else:
                    err_code, err_msg = mt5.last_error()
                    self._last_error = f"MT5 initialization failed: {err_msg} (code {err_code})"
            except Exception as e:
                self._initialized = False
                self._last_error = f"Exception during MT5 initialization: {str(e)}"

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def _update_diagnostics(self) -> None:
        """Fetch real values dynamically from terminal_info and account_info."""
        if not MT5_AVAILABLE or mt5 is None or not self._initialized:
            return
        try:
            term_info = mt5.terminal_info()
            if term_info is not None:
                self._terminal_path = getattr(term_info, "path", self._terminal_path)

            acc_info = mt5.account_info()
            if acc_info is not None:
                self._login = getattr(acc_info, "login", self._login)
                self._server = getattr(acc_info, "server", self._server)
        except Exception:
            pass

    def _map_timeframe(self, tf: str) -> int:
        if not MT5_AVAILABLE or mt5 is None:
            # Fallback/dummy values matching MT5 constants for non-Windows testing
            dummy_map = {
                "M1": 1, "M5": 5, "M15": 15, "M30": 30,
                "H1": 16385, "H4": 16388, "D1": 16408
            }
            return dummy_map.get(tf, 16385)

        tf_map = {
            "M1": getattr(mt5, "TIMEFRAME_M1", 1),
            "M5": getattr(mt5, "TIMEFRAME_M5", 5),
            "M15": getattr(mt5, "TIMEFRAME_M15", 15),
            "M30": getattr(mt5, "TIMEFRAME_M30", 30),
            "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
            "H4": getattr(mt5, "TIMEFRAME_H4", 16388),
            "D1": getattr(mt5, "TIMEFRAME_D1", 16408),
        }
        return tf_map.get(tf, getattr(mt5, "TIMEFRAME_H1", 16385))

    def get_connection_health(self) -> MT5ConnectionHealth:
        if not self._connected:
            return MT5ConnectionHealth(
                connected=False,
                terminal_path=self._terminal_path,
                server=self._server,
                login=self._login,
                ping=0.0,
                last_error="Connection lost to MT5 terminal.",
                last_successful_fetch=self._last_successful_fetch
            )

        if not MT5_AVAILABLE or mt5 is None:
            return MT5ConnectionHealth(
                connected=False,
                terminal_path=self._terminal_path,
                server=self._server,
                login=self._login,
                ping=0.0,
                last_error="MetaTrader5 Python package is not available in this environment.",
                last_successful_fetch=self._last_successful_fetch
            )

        try:
            if not self._initialized:
                if mt5.initialize():
                    self._initialized = True
                    self._update_diagnostics()
                else:
                    err_code, err_msg = mt5.last_error()
                    return MT5ConnectionHealth(
                        connected=False,
                        terminal_path=self._terminal_path,
                        server=self._server,
                        login=self._login,
                        ping=0.0,
                        last_error=f"MT5 initialization failed: {err_msg} (code {err_code})",
                        last_successful_fetch=self._last_successful_fetch
                    )

            term_info = mt5.terminal_info()
            if term_info is None:
                err_code, err_msg = mt5.last_error()
                return MT5ConnectionHealth(
                    connected=False,
                    terminal_path=self._terminal_path,
                    server=self._server,
                    login=self._login,
                    ping=0.0,
                    last_error=f"Failed to get terminal info: {err_msg} (code {err_code})",
                    last_successful_fetch=self._last_successful_fetch
                )

            if not getattr(term_info, "connected", False):
                return MT5ConnectionHealth(
                    connected=False,
                    terminal_path=self._terminal_path,
                    server=self._server,
                    login=self._login,
                    ping=0.0,
                    last_error="MT5 terminal is not connected to the broker.",
                    last_successful_fetch=self._last_successful_fetch
                )

            symbols = mt5.symbols_get()
            if symbols is None or len(symbols) == 0:
                return MT5ConnectionHealth(
                    connected=False,
                    terminal_path=self._terminal_path,
                    server=self._server,
                    login=self._login,
                    ping=0.0,
                    last_error="No symbols available from MT5 terminal.",
                    last_successful_fetch=self._last_successful_fetch
                )

            self._update_diagnostics()

            return MT5ConnectionHealth(
                connected=True,
                terminal_path=self._terminal_path,
                server=self._server,
                login=self._login,
                ping=self._ping,
                last_error=None,
                last_successful_fetch=self._last_successful_fetch
            )
        except Exception as e:
            return MT5ConnectionHealth(
                connected=False,
                terminal_path=self._terminal_path,
                server=self._server,
                login=self._login,
                ping=0.0,
                last_error=f"Exception in health check: {str(e)}",
                last_successful_fetch=self._last_successful_fetch
            )

    def check_health(self) -> ProviderHealthStatus:
        health = self.get_connection_health()
        if not health.connected:
            return ProviderHealthStatus.UNHEALTHY
        if health.ping > 100.0:
            return ProviderHealthStatus.DEGRADED
        return ProviderHealthStatus.HEALTHY

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        """Traditional external provider fetch handler using real MetaTrader5 API."""
        health = self.get_connection_health()
        if not health.connected:
            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message=health.last_error or "MT5 connection is offline."
            )

        # Dynamic Symbol Validation using mt5.symbol_info
        if MT5_AVAILABLE and mt5 is not None:
            try:
                sym_info = mt5.symbol_info(request.symbol)
                if sym_info is None:
                    return ExternalDataResponse(
                        request_id=request.request_id or "id",
                        provider_id=self._metadata.provider_id,
                        raw_data=[],
                        is_success=False,
                        error_message=f"Symbol {request.symbol} is not found on MetaTrader 5 terminal."
                    )
            except Exception as e:
                return ExternalDataResponse(
                    request_id=request.request_id or "id",
                    provider_id=self._metadata.provider_id,
                    raw_data=[],
                    is_success=False,
                    error_message=f"Exception during symbol info check: {str(e)}"
                )

        mt5_tf = self._map_timeframe(request.timeframe)
        try:
            start_dt = request.start_time
            end_dt = request.end_time
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt)
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt)

            rates = mt5.copy_rates_range(request.symbol, mt5_tf, start_dt, end_dt)
            if rates is None:
                err_code, err_msg = mt5.last_error()
                return ExternalDataResponse(
                    request_id=request.request_id or "id",
                    provider_id=self._metadata.provider_id,
                    raw_data=[],
                    is_success=False,
                    error_message=f"MT5 copy_rates_range returned None. Error: {err_msg} (code {err_code})"
                )

            rates_list = []
            for rate in rates:
                if isinstance(rate, dict):
                    time_val = rate.get("time")
                    open_val = rate.get("open")
                    high_val = rate.get("high")
                    low_val = rate.get("low")
                    close_val = rate.get("close")
                    vol_val = rate.get("tick_volume") or rate.get("volume", 0)
                else:
                    try:
                        time_val = rate["time"]
                        open_val = rate["open"]
                        high_val = rate["high"]
                        low_val = rate["low"]
                        close_val = rate["close"]
                        vol_val = rate["tick_volume"] if hasattr(rate, "dtype") and "tick_volume" in rate.dtype.names else rate["volume"]
                    except (TypeError, IndexError, ValueError, KeyError):
                        time_val = getattr(rate, "time")
                        open_val = getattr(rate, "open")
                        high_val = getattr(rate, "high")
                        low_val = getattr(rate, "low")
                        close_val = getattr(rate, "close")
                        vol_val = getattr(rate, "tick_volume", getattr(rate, "volume", 0))

                rates_list.append({
                    "time": int(time_val),
                    "open": float(open_val),
                    "high": float(high_val),
                    "low": float(low_val),
                    "close": float(close_val),
                    "tick_volume": float(vol_val)
                })

            # Update last successful fetch
            self._last_successful_fetch = datetime.now().isoformat()

            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=rates_list,
                is_success=True
            )
        except Exception as e:
            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message=f"Exception in fetch_data: {str(e)}"
            )

    def fetch_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """Advanced typed market data fetch handler."""
        start_time = time.time()

        health = self.get_connection_health()
        if not health.connected:
            latency = (time.time() - start_time) * 1000.0
            return MarketDataResponse(
                request=request,
                candles=[],
                metadata=MarketDataMetadata(self._metadata.provider_id, datetime.now(), latency),
                is_success=False,
                error_message=health.last_error or "MT5 connection is offline."
            )

        ext_req = ExternalDataRequest(
            symbol=request.instrument.symbol,
            timeframe=request.timeframe,
            start_time=request.start_time,
            end_time=request.end_time
        )
        ext_resp = self.fetch_data(ext_req)

        latency = (time.time() - start_time) * 1000.0
        meta = MarketDataMetadata(
            provider_id=self._metadata.provider_id,
            retrieved_at=ext_resp.retrieved_at,
            latency_ms=latency,
            additional_properties={"server": health.server}
        )

        if not ext_resp.is_success:
            return MarketDataResponse(
                request=request,
                candles=[],
                metadata=meta,
                is_success=False,
                error_message=ext_resp.error_message
            )

        candles = self._mapper.map_rates_to_candles(ext_resp.raw_data)
        return MarketDataResponse(
            request=request,
            candles=candles,
            metadata=meta,
            is_success=True
        )
