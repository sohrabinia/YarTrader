import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Data.External.interfaces import IDataProvider
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.Market.models import MarketInstrument, CandleRecord, MarketDataMetadata, MarketDataRequest, MarketDataResponse
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class MT5ConnectionHealth:
    connected: bool
    server: str
    ping_ms: float
    last_error: Optional[str] = None


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
    """
    def __init__(
        self,
        provider_id: str = "mt5-provider",
        server: str = "Demo-Server",
        supported_symbols: Optional[List[str]] = None
    ) -> None:
        supported_symbols = supported_symbols or ["EURUSD", "GBPUSD", "USDJPY"]
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.MT5,
            supported_symbols=supported_symbols
        )
        self._server = server
        self._connected = True
        self._ping = 15.4
        self._mapper = MT5DataMapper()

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def get_connection_health(self) -> MT5ConnectionHealth:
        return MT5ConnectionHealth(
            connected=self._connected,
            server=self._server,
            ping_ms=self._ping if self._connected else 0.0,
            last_error=None if self._connected else "Connection lost to MT5 terminal."
        )

    def check_health(self) -> ProviderHealthStatus:
        if not self._connected:
            return ProviderHealthStatus.UNHEALTHY
        if self._ping > 100.0:
            return ProviderHealthStatus.DEGRADED
        return ProviderHealthStatus.HEALTHY

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        """Traditional external provider fetch handler."""
        if not self._connected:
            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message="MT5 connection is currently offline."
            )

        # Simulate read historical rates
        raw_rates = []
        curr = request.start_time
        base_price = 1.1000 if "JPY" not in request.symbol else 145.0
        increment = 0.0001 if "JPY" not in request.symbol else 0.01

        # Generates simulated historical ticks/rates
        for i in range(10):
            if curr > request.end_time:
                break
            raw_rates.append({
                "time": int(curr.timestamp()),
                "open": base_price + i * increment,
                "high": base_price + (i + 2) * increment,
                "low": base_price + (i - 1) * increment,
                "close": base_price + (i + 1) * increment,
                "tick_volume": 150.0 + i * 10
            })
            curr += timedelta(minutes=15)

        return ExternalDataResponse(
            request_id=request.request_id or "id",
            provider_id=self._metadata.provider_id,
            raw_data=raw_rates,
            is_success=True
        )

    def fetch_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """Advanced typed market data fetch handler."""
        start_time = time.time()

        # Guard connection
        if not self._connected:
            latency = (time.time() - start_time) * 1000.0
            return MarketDataResponse(
                request=request,
                candles=[],
                metadata=MarketDataMetadata(self._metadata.provider_id, datetime.now(), latency),
                is_success=False,
                error_message="MT5 connection is offline."
            )

        # Retrieve raw via standard fetch
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
            additional_properties={"server": self._server}
        )

        if not ext_resp.is_success:
            return MarketDataResponse(
                request=request,
                candles=[],
                metadata=meta,
                is_success=False,
                error_message=ext_resp.error_message
            )

        # Map to typed CandleRecords
        candles = self._mapper.map_rates_to_candles(ext_resp.raw_data)
        return MarketDataResponse(
            request=request,
            candles=candles,
            metadata=meta,
            is_success=True
        )
