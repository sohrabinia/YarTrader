from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MarketInstrument:
    symbol: str
    asset_class: str  # e.g., FX, Crypto, Equities
    digits: int = 5
    contract_size: float = 100000.0
    tick_size: float = 0.00001
    description: str = ""


@dataclass(frozen=True)
class CandleRecord:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketDataMetadata:
    provider_id: str
    retrieved_at: datetime
    latency_ms: float
    additional_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketDataRequest:
    instrument: MarketInstrument
    timeframe: str
    start_time: datetime
    end_time: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketDataResponse:
    request: MarketDataRequest
    candles: List[CandleRecord]
    metadata: MarketDataMetadata
    is_success: bool = True
    error_message: Optional[str] = None


@dataclass(frozen=True)
class CompactMarketState:
    """
    Compact market state containing primitive broker/market facts immediately adjacent to the MT5 adapter boundary.
    Contains strictly primitive market facts (prices, volume, spread, timestamp, freshness, validity)
    and NO technical indicators (NO ATR, NO RSI, NO MA, NO indicator-derived trend/momentum).
    """
    symbol: str
    timeframe: str
    timestamp: datetime
    current_price: float
    high: float
    low: float
    volume: float
    spread: float
    data_freshness_sec: float
    is_valid: bool
    bar_count: int
