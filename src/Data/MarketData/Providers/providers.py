from datetime import datetime
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint

class MetaTrader5Provider(IMarketDataProvider):
    """
    Placeholder provider implementation for MetaTrader5 platform integration.
    Contains no real API connections or platform-specific libraries.
    """
    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        # Return a standardized mock response with a single dummy data point for safety
        dummy_point = MarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=50000.0
        )
        return MarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )


class ExchangeProvider(IMarketDataProvider):
    """
    Placeholder provider implementation for direct exchange REST/WebSocket APIs (e.g., Binance, CCXT).
    Contains no real API connections or network requests.
    """
    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        dummy_point = MarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=50000.0
        )
        return MarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )


class FileImportProvider(IMarketDataProvider):
    """
    Placeholder provider implementation for raw local file system CSV/JSON historical imports.
    Contains no live filesystem file reading operations.
    """
    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        dummy_point = MarketDataPoint(
            AssetId=request.Asset,
            Timestamp=request.StartTime,
            Open=100.0,
            High=105.0,
            Low=95.0,
            Close=102.0,
            Volume=50000.0
        )
        return MarketDataResponse(
            Request=request,
            DataPoints=[dummy_point],
            RetrievedAt=datetime.now()
        )
