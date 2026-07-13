from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Data.External.interfaces import IDataProvider
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class EconomicCalendarRecord:
    event_id: str
    name: str
    country: str
    timestamp: datetime
    impact: str  # Low, Medium, High
    actual: Optional[float] = None
    previous: Optional[float] = None
    expected: Optional[float] = None


@dataclass(frozen=True)
class EconomicEvent:
    record: EconomicCalendarRecord
    parsed_at: datetime = field(default_factory=datetime.now)


class EconomicDataProvider(IDataProvider):
    """
    Economic Data Ingestion Provider.
    Retrieves passive macroeconomic calendar events and indexes impact metrics.
    No forecasting or predictions.
    """
    def __init__(self, provider_id: str = "economic-provider") -> None:
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.ECONOMIC_DATA,
            supported_symbols=["US_CPI", "US_PAYROLL", "EUR_GER_GDP"]
        )
        self._health = ProviderHealthStatus.HEALTHY

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def set_health(self, health: ProviderHealthStatus) -> None:
        self._health = health

    def check_health(self) -> ProviderHealthStatus:
        return self._health

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        if self._health == ProviderHealthStatus.UNHEALTHY:
            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message="Economic Provider is unhealthy."
            )

        # Simulate fetching economic calendar
        events = []
        curr = request.start_time

        # Match request to generate specific passive macros
        if request.symbol == "US_CPI":
            events.append({
                "event_id": "ev-us-cpi-1",
                "name": "Consumer Price Index (YoY)",
                "country": "US",
                "timestamp": curr.isoformat(),
                "impact": "High",
                "actual": 3.1,
                "previous": 3.2,
                "expected": 3.0
            })
        elif request.symbol == "US_PAYROLL":
            events.append({
                "event_id": "ev-us-nfp-1",
                "name": "Non-Farm Payrolls",
                "country": "US",
                "timestamp": curr.isoformat(),
                "impact": "High",
                "actual": 175000.0,
                "previous": 210000.0,
                "expected": 185000.0
            })
        else:
            events.append({
                "event_id": f"ev-{request.symbol.lower()}-1",
                "name": f"Macro Indicator: {request.symbol}",
                "country": "Global",
                "timestamp": curr.isoformat(),
                "impact": "Medium",
                "actual": 1.5,
                "previous": 1.4,
                "expected": 1.6
            })

        return ExternalDataResponse(
            request_id=request.request_id or "id",
            provider_id=self._metadata.provider_id,
            raw_data=events,
            is_success=True
        )

    def fetch_calendar_events(self, request: ExternalDataRequest) -> List[EconomicEvent]:
        resp = self.fetch_data(request)
        if not resp.is_success:
            return []

        parsed_events = []
        for r in resp.raw_data:
            try:
                rec = EconomicCalendarRecord(
                    event_id=r["event_id"],
                    name=r["name"],
                    country=r["country"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    impact=r["impact"],
                    actual=float(r["actual"]) if r.get("actual") is not None else None,
                    previous=float(r["previous"]) if r.get("previous") is not None else None,
                    expected=float(r["expected"]) if r.get("expected") is not None else None
                )
                parsed_events.append(EconomicEvent(record=rec, parsed_at=datetime.now()))
            except Exception as e:
                raise ValidationException(f"Economic Parsing Error: Failed to parse calendar record. Details: {e}")
        return parsed_events
