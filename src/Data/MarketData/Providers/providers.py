from datetime import datetime
from typing import Optional
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
# Target models
from src.Data.MarketData.Models.models import (
    MarketDataRequest as TargetMarketDataRequest,
    MarketDataResponse as TargetMarketDataResponse,
    MarketDataPoint as TargetMarketDataPoint
)
# Delegate provider and source models
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.Market.models import (
    MarketInstrument,
    MarketDataRequest as SourceMarketDataRequest
)
from src.Infrastructure.exceptions import ValidationException

class MetaTrader5Provider(IMarketDataProvider):
    """
    Adapter implementing IMarketDataProvider interface that delegates actual
    market data retrieval to the existing read-only MT5DataProvider.
    This avoids duplication of MT5 integration and mapping logic.
    """
    def __init__(self, delegate: Optional[MT5DataProvider] = None) -> None:
        self._delegate = delegate or MT5DataProvider(provider_id="mt5-marketdata-provider")

    @property
    def delegate(self) -> MT5DataProvider:
        return self._delegate

    def retrieve_market_data(self, request: TargetMarketDataRequest) -> TargetMarketDataResponse:
        """
        Translates target MarketDataRequest, delegates to MT5DataProvider,
        and translates the resulting CandleRecords into TargetMarketDataPoints.
        """
        # 1. Map TargetMarketDataRequest to SourceMarketDataRequest
        # Determine asset class. Standardize on FX but allow customization if needed.
        asset_class = "Metals" if "XAU" in request.Asset or "XAG" in request.Asset else "FX"
        instrument = MarketInstrument(symbol=request.Asset, asset_class=asset_class)

        source_request = SourceMarketDataRequest(
            instrument=instrument,
            timeframe=request.Timeframe,
            start_time=request.StartTime,
            end_time=request.EndTime
        )

        # 2. Fetch data from delegate
        try:
            source_response = self._delegate.fetch_market_data(source_request)
        except Exception as e:
            raise ValidationException(f"MT5 Adapter Error: Delegate fetch failed: {str(e)}") from e

        if not source_response.is_success:
            raise ValidationException(f"MT5 Adapter Error: {source_response.error_message}")

        # 3. Map CandleRecords to TargetMarketDataPoints
        target_points = []
        for candle in source_response.candles:
            point = TargetMarketDataPoint(
                AssetId=request.Asset,
                Timestamp=candle.timestamp,
                Open=candle.open,
                High=candle.high,
                Low=candle.low,
                Close=candle.close,
                Volume=candle.volume
            )
            target_points.append(point)

        # 4. Construct and return TargetMarketDataResponse
        return TargetMarketDataResponse(
            Request=request,
            DataPoints=target_points,
            RetrievedAt=source_response.metadata.retrieved_at
        )


class ExchangeProvider(IMarketDataProvider):
    """
    Placeholder provider implementation for direct exchange REST/WebSocket APIs (e.g., Binance, CCXT).
    Contains no real API connections or network requests.
    """
    def retrieve_market_data(self, request: TargetMarketDataRequest) -> TargetMarketDataResponse:
        dummy_point = TargetMarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=50000.0
        )
        return TargetMarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )


class FileImportProvider(IMarketDataProvider):
    """
    Placeholder provider implementation for raw local file system CSV/JSON historical imports.
    Contains no live filesystem file reading operations.
    """
    def retrieve_market_data(self, request: TargetMarketDataRequest) -> TargetMarketDataResponse:
        dummy_point = TargetMarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=50000.0
        )
        return TargetMarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )
