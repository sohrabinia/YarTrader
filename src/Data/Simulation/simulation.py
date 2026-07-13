from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.External.interfaces import IDataProvider


class SimulationDataProvider(IDataProvider):
    """
    Simulation Provider delivering mock candle data to test external integration pipelines.
    Supports failure, missing data, and corrupted data injection.
    """
    def __init__(
        self,
        provider_id: str = "sim-provider-1",
        supported_symbols: Optional[List[str]] = None,
        health: ProviderHealthStatus = ProviderHealthStatus.HEALTHY
    ) -> None:
        supported_symbols = supported_symbols or ["AAPL", "BTCUSD", "EURUSD"]
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.SIMULATION,
            supported_symbols=supported_symbols,
            rate_limit_per_minute=1000
        )
        self._health = health

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def set_health(self, health: ProviderHealthStatus) -> None:
        self._health = health

    def check_health(self) -> ProviderHealthStatus:
        return self._health

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        # Check health: if unhealthy, return failure response
        if self._health == ProviderHealthStatus.UNHEALTHY:
            return ExternalDataResponse(
                request_id=request.request_id or str(datetime.now().timestamp()),
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message="Simulation Provider is currently unhealthy."
            )

        scenario = request.parameters.get("scenario", "VALID")

        if scenario == "FAILURE":
            return ExternalDataResponse(
                request_id=request.request_id or str(datetime.now().timestamp()),
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message="Simulated provider failure triggered."
            )

        if scenario == "EXCEPTION":
            raise RuntimeError("Simulated remote provider connection crashed.")

        # Build records
        records = []
        current_time = request.start_time
        base_price = 100.0

        # Create 10 mock points
        for i in range(10):
            if current_time > request.end_time:
                break

            record: Dict[str, Any] = {
                "symbol": request.symbol,
                "timestamp": current_time.isoformat()
            }

            if scenario == "VALID":
                record.update({
                    "open": base_price + i,
                    "high": base_price + i + 2,
                    "low": base_price + i - 1,
                    "close": base_price + i + 1,
                    "volume": 1000.0 + i * 50
                })
            elif scenario == "MISSING_FIELDS":
                # missing 'high' and 'low'
                record.update({
                    "open": base_price + i,
                    "close": base_price + i + 1,
                    "volume": 1000.0
                })
            elif scenario == "CORRUPTED_PRICES":
                # Low price exceeds High price
                record.update({
                    "open": base_price + i,
                    "high": base_price + i,
                    "low": base_price + i + 10,  # corrupted!
                    "close": base_price + i,
                    "volume": 500.0
                })
            elif scenario == "DUPLICATES":
                # Same timestamp
                record.update({
                    "open": base_price + i,
                    "high": base_price + i + 2,
                    "low": base_price + i - 1,
                    "close": base_price + i + 1,
                    "volume": 1000.0
                })
                # Append twice
                records.append(record.copy())
            elif scenario == "INVALID_TIMESTAMPS":
                record.update({
                    "timestamp": "this-is-not-a-datetime",  # corrupted!
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000.0
                })

            records.append(record)
            current_time += timedelta(minutes=15)

        return ExternalDataResponse(
            request_id=request.request_id or str(datetime.now().timestamp()),
            provider_id=self._metadata.provider_id,
            raw_data=records,
            is_success=True
        )
