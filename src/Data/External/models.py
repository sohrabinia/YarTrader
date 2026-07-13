from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DataSourceType(str, Enum):
    MT5 = "MT5"
    EXCHANGE_API = "EXCHANGE_API"
    ECONOMIC_DATA = "ECONOMIC_DATA"
    NEWS_PROVIDER = "NEWS_PROVIDER"
    SIMULATION = "SIMULATION"


class ProviderHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True)
class DataProviderMetadata:
    provider_id: str
    source_type: DataSourceType
    supported_symbols: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalDataRequest:
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    request_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalDataResponse:
    request_id: str
    provider_id: str
    raw_data: List[Dict[str, Any]]
    retrieved_at: datetime = field(default_factory=datetime.now)
    is_success: bool = True
    error_message: Optional[str] = None
