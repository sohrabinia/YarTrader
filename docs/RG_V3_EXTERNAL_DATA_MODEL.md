# RG_V3 External Data Model

This document outlines the standard data models and contract schemas governing external data ingestion in **Phase 23 Real Data Intelligence Connector Foundation**.

---

## 1. Provider Contracts

All data providers must implement the core abstract contract `IDataProvider`:

```python
class IDataProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> DataProviderMetadata:
        pass

    @abstractmethod
    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        pass

    @abstractmethod
    def check_health(self) -> ProviderHealthStatus:
        pass
```

---

## 2. Ingestion Models

### ExternalDataRequest
Represents a structured data request payload to external providers:
*   `symbol`: `str` (e.g. `"AAPL"`)
*   `timeframe`: `str` (e.g. `"M15"`)
*   `start_time`: `datetime`
*   `end_time`: `datetime`
*   `request_id`: `str`
*   `parameters`: `Dict[str, Any]` (e.g. `{"scenario": "VALID"}`)

### ExternalDataResponse
Represents the raw, un-normalized response returned by external providers:
*   `request_id`: `str`
*   `provider_id`: `str`
*   `raw_data`: `List[Dict[str, Any]]`
*   `retrieved_at`: `datetime`
*   `is_success`: `bool`
*   `error_message`: `str`

---

## 3. Standardized Output Model

### NormalizedMarketRecord
Represents normalized, validated, and structurally uniform records consumed by the platform's research and strategy layers:
*   `timestamp`: `datetime`
*   `symbol`: `str` (mapped to uniform standard names)
*   `open_price`: `float`
*   `high_price`: `float`
*   `low_price`: `float`
*   `close_price`: `float`
*   `volume_size`: `float`
*   `original_source`: `str` (identifying origin provider)
*   `source_metadata`: `Dict[str, Any]` (preserving custom original provider metadata parameters)

---

## 4. Multi-Factor Quality Formulation

Data quality scores are formulated dynamically across four dimensions:

$$\text{Overall Score} = 0.3 \cdot Q_{\text{completeness}} + 0.2 \cdot Q_{\text{timestamp}} + 0.2 \cdot Q_{\text{uniqueness}} + 0.3 \cdot Q_{\text{consistency}}$$

Where:
*   $Q_{\text{completeness}}$ measures the ratio of non-null expected keys present in records.
*   $Q_{\text{timestamp}}$ measures the validity and parseability of datetime fields.
*   $Q_{\text{uniqueness}}$ measures the ratio of duplicate timestamps.
*   $Q_{\text{consistency}}$ checks bounds constraints ($Price_{\text{low}} \le Price_{\text{high}}$ and $Open/Close \in [Price_{\text{low}}, Price_{\text{high}}]$).
