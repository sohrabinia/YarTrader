# TRADEYAR Data Intelligence Layer Foundation

The Data Intelligence Layer is responsible for the ingest, validation, normalization, and abstraction of financial market data across the TRADEYAR Autonomous Financial Intelligence Platform. In strict adherence to the Clean Architecture principles, this layer provides a decoupling between external data feeds and downstream research, strategy, and risk logic.

---

## 1. Data Layer Mission

The core mission of the Data Intelligence Layer is to:
* **Establish Trustworthy Inputs:** Enforce zero-tolerance structural validation rules to guarantee that all down-stream calculations operate on mathematically correct, coherent financial feeds.
* **Normalize Schema Heterogeneity:** Abstract away the formatting differences between exchange providers, local files, and enterprise trading platforms (e.g., MetaTrader 5).
* **Provide Storage Agnosticism:** Maintain highly optimized interfaces for historical time-series storage, allowing seamless transitions between in-memory mock repositories and enterprise time-series databases with zero impact on the core domain layer.
* **Prepare for Future Streaming:** Establish robust asynchronous streaming contracts to support real-time feeds when streaming data engines are integrated.

---

## 2. Data Architecture

The architecture of `src/Data/` is strictly segmented into highly coherent modules to maintain separation of concerns:

```text
src/Data/
├── MarketData/
│   ├── Models/            # Standard structures (MarketDataPoint, MarketDataRequest, etc.)
│   ├── Providers/         # Provider adapters (MT5, Exchange, File Import)
│   ├── Normalization/     # Translation, validation, and data quality checker engines
│   └── Interfaces/        # Abstraction boundaries for data acquisition
├── HistoricalData/
│   ├── Models/            # Data models specific to local persistence
│   ├── Repository/        # Local disk/memory storage engine implementations
│   └── Interfaces/        # Abstract contracts for historical query/write gateways
├── Streaming/
│   ├── Models/            # Stream metadata and connection descriptors
│   └── Interfaces/        # Contracts for real-time asynchronous streaming subscriptions
└── Common/                # Globally used shared data models (e.g. DataQualityReport)
```

---

## 3. Market Data Flow

The platform handles market data processing in a highly linear, secure pipeline:

1. **Acquisition:** A `MarketDataRequest` is submitted to a provider implementing `IMarketDataProvider` (e.g., `MetaTrader5Provider` or `ExchangeProvider`).
2. **Translation & Normalization:** Raw third-party responses (JSON, CSV, or custom dictionaries) are passed to the `MarketDataNormalizer` to be converted into unified `MarketDataPoint` lists.
3. **Validation & Quality Control:** The normalized list goes through the `MarketDataValidator` and `DataQualityChecker` to audit price boundaries, mathematically impossible high/low ranges, volume formats, and abnormal outliers. An audit report (`DataQualityReport`) is generated.
4. **Local Archiving:** Validated records are stored locally via `IHistoricalDataRepository`.
5. **Consumption:** Downstream analytical engines query clean, pre-validated historical datasets through standard interfaces, keeping the domain circles completely unaware of the original source or format.

---

## 4. Historical vs. Streaming Architecture

The architecture distinguishes between batch-based historical ingestion and stream-based real-time subscriptions:

* **Historical Ingestion (`HistoricalData`):** Handles bulk back-filling, simulation queries, and passive analytical scoring. It is pull-based, executing requests within start/end boundaries, and is completely optimized for bulk reads and linear caching.
* **Streaming Subscription (`Streaming`):** Planned for future real-time feeds, it will be push-based and asynchronous. Subscriptions are established per asset using active event-driven listeners (e.g., WebSockets), allowing other modules to register callbacks to receive live pricing ticks as they arrive.

---

## 5. Provider Abstraction Philosophy

External market data sources are highly volatile, frequently changing their APIs, limits, and authentication schemas.

* **No Vendor Lock-In:** The platform does not directly import or bind itself to any commercial client library (e.g. MetaTrader5, exchange-specific client SDKs).
* **Interface-Driven Design:** Every provider is merely an implementation of `IMarketDataProvider`. Swapping out MetaTrader 5 for direct REST connectivity or a CSV file import is as simple as injecting a different provider class at bootstrap. No core strategy, decision, or risk logic changes are required.

---

## 6. Data Quality Principles

High-quality decisions require flawless data quality. The layer enforces three main quality checks:

1. **Structural Validation:** Prices must be strictly positive (> 0), volume must be non-negative, and the High/Low values must conform to logical boundaries (High >= Open/Close >= Low).
2. **Temporal Integrity:** Timestamps must be monotonic (strictly ascending) and must not represent a timestamp in the future.
3. **Volume and Outlier Warnings:** Flag bars with exactly zero volume or anomalous gaps to prevent downstream mathematical distortion in indicator calculators (e.g., historical volatility and momentum rating).
