# Phase 21 — Live Research Runtime Repository Audit

This document presents a comprehensive, production-grade audit of the repository's current market data integration structures, research engines, persistence layers, and test suites, paving the way for the Phase 21 Live Research Runtime implementation.

---

## 1. Existing Market Data Contract

### A. Core Interfaces
The core interface for retrieving market data is `IMarketDataProvider`, located in `src/Data/MarketData/Interfaces/interfaces.py`:
* **Interface Definition**:
  ```python
  class IMarketDataProvider(ABC):
      """Interface defining contracts for obtaining market data from upstream providers."""
      @abstractmethod
      def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
          """Retrieves market data based on specified request parameters."""
          pass
  ```
* **Other Market Data Abstractions**:
  - `IMarketDataNormalizer`: Translates dynamic third-party data payloads into standardized structures.
  - `IMarketDataValidator`: Performs structural validation on data points.
  - `IDataQualityChecker`: Generates data quality reports checking for anomalies.

### B. Read-Only Policy Implementation
* There are multiple providers defined under `src/Data/MarketData/Providers/providers.py` (e.g., `MetaTrader5Provider`, `ExchangeProvider`, `FileImportProvider`). These are currently minimal placeholder adapters returning static mockup data points for safety.
* Crucially, the system defines an advanced `MT5DataProvider` in `src/Data/Providers/MT5/mt5.py` implementing `IDataProvider`. This provider adheres to a strict read-only design, isolating all market data retrieval and preventing any trading commands, order placements, position modifications, or account inquiries.

---

## 2. Current Data Models

Standardized data models reside in `src/Data/MarketData/Models/models.py`.

### A. MarketDataPoint
Represents a standardized point-in-time OHLCV bar for an asset:
* **Fields**:
  - `AssetId: str`
  - `Timestamp: datetime`
  - `Open: float`
  - `High: float`
  - `Low: float`
  - `Close: float`
  - `Volume: float`
* **Properties**: Standardized lowercase properties (`asset_id`, `timestamp`, `open`, `high`, `low`, `close`, `volume`) map directly to the camel-cased internal fields to support flexible dictionary mapping.

### B. MarketDataRequest
Represents a standardized query for historical or live market data:
* **Fields**:
  - `Asset: str`
  - `StartTime: datetime`
  - `EndTime: datetime`
  - `Timeframe: str` (e.g., `"M1"`, `"M15"`, `"H1"`, `"D1"`)

### C. MarketDataResponse
Encapsulates retrieved market data:
* **Fields**:
  - `Request: MarketDataRequest`
  - `DataPoints: List[MarketDataPoint]`
  - `RetrievedAt: datetime`

---

## 3. Research Integration Point

### A. FeatureExtractionResearchEngine Entry Point
The primary integration point resides in `src/Research/MarketAnalysis/Services/services.py`:
* **Class**: `FeatureExtractionResearchEngine` implementing `IResearchEngine` (Decorator pattern).
* **Execution Flow**:
  1. Accepts a standard `ResearchRequest`.
  2. Queries the injected `IMarketDataProvider` to fetch raw market data points via a constructed `MarketDataRequest`.
  3. Executes the underlying `FeaturePipeline` to produce a calculated `MarketFeatureSet`.
  4. Enriches the `ResearchRequest` context dict with `"market_feature_set"` and `"extracted_features"`.
  5. Delegates research processing to the core `ResearchEngine` (`src/Research/Engine/services.py`).
  6. Returns an enriched `ResearchResult` compiling the base findings, feature sets, and observations.

### B. Required Input/Output Contracts
* **Input**: `ResearchRequest`
  - Must contain the target `Asset` (e.g., `"XAUUSD"`), the temporal boundaries (`StartTime`, `EndTime`), and optionally custom configurations inside the `Context` (such as `"timeframe"`).
* **Output**: `ResearchResult`
  - Contains the original request, structured `Findings` dictionary (including `"feature_set"`, `"observation_summary"`), a `ConfidenceScore`, and generation metadata.

---

## 4. Persistence Pattern

### A. Existing Storage Approach & Repositories
The system uses isolated, thread-safe, memory-based repository patterns:
* **Historical Data Storage**: Implemented via `HistoricalDataRepository` in `src/Data/HistoricalData/Repository/repository.py` conforming to `IHistoricalDataRepository`. It stores `MarketDataPoint`s in an in-memory dictionary grouped by `AssetId` and sorted chronologically.
* **Research Storage**: Implemented via `ResearchProcessor`'s internal class `ResearchHistory` in `src/Research/MarketAnalysis/Services/services.py`. It records completed `ResearchResult`s in local list collections.
* **Knowledge Preservation**: Conforms to clean separation rules where analytical outcomes are stored securely without active DB integrations or external dependencies, ensuring 100% decoupling from execution environments.

---

## 5. Test Architecture

### A. Test Projects & Structures
The codebase has a highly structured, comprehensive test configuration located under `tests/`:
* **Unit and Service Tests**: Standard tests checking domain behavior (e.g., `tests/test_research_intelligence.py`, `tests/test_feature_extraction.py`, `tests/test_strategy_evaluation.py`).
* **Advanced Multi-Agent & Orchestration Tests**: Located in `tests/TRADEYAR_AI.Tests/` validating agent memory, performance trackers, supervisor ordering, and collaboration scenarios.
* **Integration and Production Readiness**: Validates clean architecture boundaries and configuration mappings.

### B. Testing Style & Patterns
* Uses both `unittest.TestCase` and `pytest` style assertions.
* Heavy emphasis on **mock-based boundary testing** to ensure zero active execution leakages.
* Comprehensive **Scenario Testing** (e.g., Normal Market, High Volatility, Conflicting Intelligence, Data Failure).
* Robust testing verifies error thresholds, exception boundaries, validation constraints, and safe fallbacks.

---

## 6. Minimal Implementation Plan

To connect real MetaTrader 5 market data into the existing Research Engine safely, reliably, and cleanly without breaking current architecture and under strict **READ ONLY APES-FIN** limits, we will implement the following minimal changes:

1. **Implement Concrete `MetaTrader5MarketDataProvider`**:
   - Locate/extend in `src/Data/MarketData/Providers/providers.py` (or a dedicated provider module).
   - Inherit directly from `IMarketDataProvider`.
   - Adapt the existing read-only `MT5DataProvider` (or map from it) to cleanly convert `CandleRecord` structures into standard `MarketDataPoint` structures.
   - Restrict functionality purely to `retrieve_market_data()`. Absolutely no trading-related functionality (orders, transactions, account balance, margin) will be included.

2. **Establish the Research Runtime Engine**:
   - Create a runtime coordinator under `src/Application/Runtime/research_runtime.py`.
   - Structure a cyclic polling process (e.g., polling cycle or scheduled interval) that:
     1. Establishes/verifies connection to the read-only MT5 provider.
     2. Ingests the latest candle (Asset: `XAUUSD`, Timeframe: `H1`).
     3. Converts and standardizes incoming rates into `MarketDataPoint` instances.
     4. Constructs an enriched `ResearchRequest`.
     5. Triggers the `FeatureExtractionResearchEngine` to run calculations (Price, Volatility, Trend features) and invoke the core `ResearchEngine`.
     6. Stores/Logs the compiled `ResearchResult` securely.
     7. Waits for the next cycle.

3. **Verify and Protect Boundaries**:
   - Add targeted integration tests covering connection, mapping validation, bad data fallbacks, and execution safety scans (ensuring no forbidden execution keywords are triggered).
   - Confirm all existing 1293 tests remain fully passing.
