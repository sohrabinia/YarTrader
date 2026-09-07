import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Services.market_data_service import MarketDataService, CANONICAL_SYMBOLS, CANONICAL_INTERVALS
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Data.MarketData.Normalization.normalization import MarketDataNormalizer
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Infrastructure.exceptions import ValidationException

client = TestClient(app)

class MockMarketDataProvider:
    """Deterministic mock market data provider for testing without external broker network calls."""
    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        now = request.StartTime or datetime.now(timezone.utc)
        points = []
        base_price = 2300.0 if "XAU" in request.Asset else 100.0
        for i in range(10):
            pt = MarketDataPoint(
                AssetId=request.Asset,
                Timestamp=now + timedelta(minutes=i * 15),
                Open=base_price + i,
                High=base_price + i + 2.0,
                Low=base_price + i - 1.0,
                Close=base_price + i + 1.0,
                Volume=100.0 + i * 10
            )
            points.append(pt)
        return MarketDataResponse(Request=request, DataPoints=points, RetrievedAt=datetime.now(timezone.utc))

def test_1_valid_symbol_normalization():
    service = MarketDataService(provider=MockMarketDataProvider())
    assert service.normalize_symbol("xauusd") == "XAUUSD"
    assert service.normalize_symbol("EUR/USD") == "EURUSD"
    assert service.normalize_symbol(" btc-usd ") == "BTCUSD"

def test_2_invalid_symbol_rejection():
    service = MarketDataService(provider=MockMarketDataProvider())
    with pytest.raises(ValidationException, match="Invalid market symbol"):
        service.normalize_symbol("$$$")
    with pytest.raises(ValidationException, match="non-empty string"):
        service.normalize_symbol("")

def test_3_valid_interval_normalization():
    service = MarketDataService(provider=MockMarketDataProvider())
    assert service.normalize_interval("m15") == "M15"
    assert service.normalize_interval("TF_H1") == "H1"
    assert service.normalize_interval("D1") == "D1"

def test_4_invalid_interval_rejection():
    service = MarketDataService(provider=MockMarketDataProvider())
    with pytest.raises(ValidationException, match="Unsupported market data interval"):
        service.normalize_interval("P10Y")

def test_5_ohlcv_validation_correctness():
    validator = MarketDataValidator()
    now = datetime.now(timezone.utc)

    # Valid candle
    valid_pt = MarketDataPoint(AssetId="XAUUSD", Timestamp=now, Open=2000.0, High=2010.0, Low=1995.0, Close=2005.0, Volume=100.0)
    assert validator.validate_single_point(valid_pt) is True

    # Invalid candle (High < Low)
    invalid_pt = MarketDataPoint(AssetId="XAUUSD", Timestamp=now, Open=2000.0, High=1990.0, Low=2010.0, Close=2005.0, Volume=100.0)
    assert validator.validate_single_point(invalid_pt) is False

def test_6_historical_candles_retrieval():
    service = MarketDataService(provider=MockMarketDataProvider())
    data = service.get_historical_candles("XAUUSD", "M15", limit=10)
    assert data["symbol"] == "XAUUSD"
    assert data["interval"] == "M15"
    assert data["count"] == 10
    assert len(data["candles"]) == 10
    assert data["candles"][0]["open"] == 2300.0

def test_7_latest_quote_retrieval():
    service = MarketDataService(provider=MockMarketDataProvider())
    quote = service.get_latest_quote("XAUUSD")
    assert quote["symbol"] == "XAUUSD"
    assert quote["bid"] > 0
    assert quote["ask"] >= quote["bid"]
    assert quote["status"] == "ACTIVE"

def test_8_api_historical_endpoint_success():
    res = client.get("/api/market/historical?symbol=XAUUSD&interval=M15&limit=5")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "Success"
    assert json_data["data"]["symbol"] == "XAUUSD"
    assert len(json_data["data"]["candles"]) > 0

def test_9_api_quote_endpoint_success():
    res = client.get("/api/market/quote?symbol=XAUUSD")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "Success"
    assert json_data["data"]["symbol"] == "XAUUSD"
    assert "bid" in json_data["data"]

def test_10_api_auth_protection_denies_invalid_token():
    res = client.get("/api/market/historical?symbol=XAUUSD&token=invalid_session_token")
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]
