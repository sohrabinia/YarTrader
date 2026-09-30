import time
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from src.Data.Market.models import CandleRecord
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("CryptoProvider")

class CryptoProvider:
    """
    Real public Crypto Market Data Provider.
    Queries CoinBase Exchange public REST API for real, un-mocked OHLC cryptocurrency candles.
    """
    def __init__(self, provider_id: str = "crypto-provider") -> None:
        self.provider_id = provider_id
        # Map of symbol mappings
        self.symbol_mapping = {
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "SOLUSD": "SOL-USD",
            "ADAUSD": "ADA-USD",
            "XRPUSD": "XRP-USD",
            "LTCUSD": "LTC-USD",
            "BCHUSD": "BCH-USD",
            "LINKUSD": "LINK-USD"
        }

    def _map_timeframe_to_granularity(self, tf: str) -> int:
        tf_map = {
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "H1": 3600,
            "H4": 14400,
            "D1": 86400
        }
        return tf_map.get(tf.upper(), 3600)

    def fetch_real_candles(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[CandleRecord]:
        """Fetch actual crypto candles without synthetic fallback.

        Coinbase limits each candles response to 300 bars, so long research windows
        are split into bounded requests and merged chronologically.
        """
        cb_symbol = self.symbol_mapping.get(symbol.upper(), f"{symbol.upper()[:3]}-{symbol.upper()[3:]}")
        granularity = self._map_timeframe_to_granularity(timeframe)
        step = granularity * 299
        candles_by_ts = {}
        cursor = start_time
        while cursor < end_time:
            chunk_end = min(end_time, cursor + timedelta(seconds=step))
            start_iso = cursor.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z')
            end_iso = chunk_end.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z')
            url = f"https://api.exchange.coinbase.com/products/{cb_symbol}/candles?granularity={granularity}&start={start_iso}&end={end_iso}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "YarTrader/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_data = json.loads(response.read().decode())
                if not isinstance(raw_data, list):
                    raise ValidationException("Invalid response format received from Coinbase.")
                for item in raw_data:
                    if len(item) != 6:
                        raise ValidationException("Invalid candle shape received from Coinbase.")
                    ts = datetime.fromtimestamp(item[0], tz=timezone.utc).replace(tzinfo=None)
                    candles_by_ts[ts] = CandleRecord(timestamp=ts, open=float(item[3]), high=float(item[2]), low=float(item[1]), close=float(item[4]), volume=float(item[5]))
            except Exception as e:
                logger.error(f"Coinbase API query failed for {symbol}/{timeframe}: {e}")
                raise ValidationException(f"Real crypto market data unavailable for {symbol}/{timeframe}: {e}") from e
            if chunk_end >= end_time:
                break
            cursor = chunk_end
        return [candles_by_ts[k] for k in sorted(candles_by_ts)]
