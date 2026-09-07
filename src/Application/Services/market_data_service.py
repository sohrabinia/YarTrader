import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Normalization.normalization import MarketDataNormalizer
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)

CANONICAL_SYMBOLS = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"}
CANONICAL_INTERVALS = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}

class MarketDataService:
    """
    Application service that coordinates provider-independent market data retrieval,
    symbol/interval normalization, structural validation, and timezone handling.
    """
    def __init__(
        self,
        provider: Optional[IMarketDataProvider] = None,
        normalizer: Optional[MarketDataNormalizer] = None,
        validator: Optional[MarketDataValidator] = None
    ) -> None:
        self.provider = provider or MetaTrader5Provider()
        self.normalizer = normalizer or MarketDataNormalizer()
        self.validator = validator or MarketDataValidator()

    def normalize_symbol(self, raw_symbol: str) -> str:
        """Normalizes symbol string into canonical uppercase format."""
        if not raw_symbol or not isinstance(raw_symbol, str):
            raise ValidationException("Symbol parameter must be a non-empty string.")
        clean = raw_symbol.strip().upper().replace("/", "").replace("-", "")
        if clean not in CANONICAL_SYMBOLS:
            # Permit unlisted instruments if structurally valid alphanumeric 3-12 chars
            if not clean.isalnum() or len(clean) < 3 or len(clean) > 12:
                raise ValidationException(f"Invalid market symbol format: '{raw_symbol}'")
        return clean

    def normalize_interval(self, raw_interval: str) -> str:
        """Normalizes interval timeframe into canonical representation (e.g. M1, M5, H1, D1)."""
        if not raw_interval or not isinstance(raw_interval, str):
            raise ValidationException("Interval parameter must be a non-empty string.")
        clean = raw_interval.strip().upper()
        if clean.startswith("TF_"):
            clean = clean[3:]
        if clean not in CANONICAL_INTERVALS:
            raise ValidationException(f"Unsupported market data interval: '{raw_interval}'. Supported: {sorted(list(CANONICAL_INTERVALS.keys()))}")
        return clean

    def get_historical_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Retrieves and validates normalized historical OHLCV candles."""
        clean_symbol = self.normalize_symbol(symbol)
        clean_interval = self.normalize_interval(interval)

        if limit <= 0 or limit > 5000:
            raise ValidationException("Limit must be between 1 and 5000 records.")

        now_utc = datetime.now(timezone.utc)
        if not end_time:
            end_time = now_utc
        elif end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        if not start_time:
            minutes = CANONICAL_INTERVALS[clean_interval] * limit
            start_time = end_time - timedelta(minutes=minutes)
        elif start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        req = MarketDataRequest(
            Asset=clean_symbol,
            StartTime=start_time,
            EndTime=end_time,
            Timeframe=clean_interval
        )

        try:
            res: MarketDataResponse = self.provider.retrieve_market_data(req)
            data_points = res.DataPoints
        except Exception as e:
            logger.warning(f"Market data provider retrieval failed for {clean_symbol}: {e}")
            raise ValidationException(f"Unable to retrieve market data for {clean_symbol}: {str(e)}")

        # Validate points
        valid_points = [pt for pt in data_points if self.validator.validate_single_point(pt)]

        candles = [
            {
                "timestamp": pt.Timestamp.isoformat() if hasattr(pt.Timestamp, 'isoformat') else str(pt.Timestamp),
                "open": pt.Open,
                "high": pt.High,
                "low": pt.Low,
                "close": pt.Close,
                "volume": pt.Volume
            }
            for pt in valid_points
        ]

        return {
            "symbol": clean_symbol,
            "interval": clean_interval,
            "count": len(candles),
            "retrieved_at": now_utc.isoformat(),
            "candles": candles
        }

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Retrieves latest quote for specified instrument."""
        clean_symbol = self.normalize_symbol(symbol)
        hist = self.get_historical_candles(symbol=clean_symbol, interval="M1", limit=1)
        candles = hist.get("candles", [])
        now_utc = datetime.now(timezone.utc)

        if not candles:
            return {
                "symbol": clean_symbol,
                "bid": 0.0,
                "ask": 0.0,
                "last": 0.0,
                "timestamp": now_utc.isoformat(),
                "status": "UNAVAILABLE"
            }

        latest = candles[-1]
        close_price = latest["close"]
        spread = 0.20 if "XAU" in clean_symbol else 0.0002
        return {
            "symbol": clean_symbol,
            "bid": round(close_price - (spread / 2), 4),
            "ask": round(close_price + (spread / 2), 4),
            "last": close_price,
            "timestamp": latest["timestamp"],
            "status": "ACTIVE"
        }
