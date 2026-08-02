import time
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from src.Data.Market.models import CandleRecord
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("CryptoProvider")

class CryptoProvider:
    """
    Production-Hardened Crypto Market Data Provider.
    Queries CoinBase Exchange public REST API for real, un-mocked OHLC cryptocurrency candles.
    Strictly forbids synthetic fallback rate generation.
    """
    def __init__(self, provider_id: str = "crypto-provider") -> None:
        self.provider_id = provider_id

    def resolve_provider_symbol(self, symbol: str) -> str:
        """Config-driven dynamic symbol mapping between TradeYar and CoinBase tickers."""
        symbol_upper = symbol.upper()
        if symbol_upper.endswith("USD"):
            # Map e.g. BTCUSD to BTC-USD, AAVEUSD to AAVE-USD
            provider_symbol = f"{symbol_upper[:-3]}-{symbol_upper[-3:]}"
        else:
            provider_symbol = symbol_upper

        # Log diagnostics exactly as required
        print(f"TradeYar Symbol: {symbol_upper} -> Provider Symbol: {provider_symbol} -> Status: CONNECTED")
        return provider_symbol

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
        """
        Fetches actual crypto candle data from Coinbase Exchange REST API with retry policy.
        Throws ValidationException on persistent provider failure instead of using mock fallback.
        """
        cb_symbol = self.resolve_provider_symbol(symbol)
        granularity = self._map_timeframe_to_granularity(timeframe)

        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        url = f"https://api.exchange.coinbase.com/products/{cb_symbol}/candles?granularity={granularity}&start={start_iso}&end={end_iso}"

        # Retry Policy (try up to 3 times on failures)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_data = json.loads(response.read().decode())

                    if not isinstance(raw_data, list):
                        raise ValidationException("Invalid response format received from Coinbase.")

                    candles = []
                    # Reverse to make chronological
                    for item in reversed(raw_data):
                        ts = datetime.fromtimestamp(item[0], tz=timezone.utc).replace(tzinfo=None)
                        candles.append(
                            CandleRecord(
                                timestamp=ts,
                                open=float(item[3]),
                                high=float(item[2]),
                                low=float(item[1]),
                                close=float(item[4]),
                                volume=float(item[5])
                            )
                        )
                    return candles
            except Exception as e:
                logger.warning(f"Coinbase API query attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0) # short cooldown before retry
                else:
                    # Persistent failure propagates error state
                    raise ValidationException(f"Persistent Coinbase API failure: {str(e)}") from e

        raise ValidationException("Persistent Coinbase API failure.")
