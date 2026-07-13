# RG_V3 Data Connector Architecture

This document describes the architectural design and unidirectional data flow of the **External Data Intelligence Connector (Phase 23)** of the RG_V3 Platform.

---

## 1. Architectural Overview & Design Pattern

The External Data Connector Layer provides a secure, provider-independent abstraction layer to ingest financial, economic, and news data from external sources (such as MT5, Exchange APIs, news, etc.) without creating compile-time or runtime dependencies on specific external brokers.

### Unidirectional Data Flow

```
External Provider (MT5, API, News)
        │
        ▼
   Data Gateway (ExternalDataGateway)  <── [ProviderRegistry & Resolver]
        │
        ▼
Validation Layer (DataQualityAnalyzer)  ───> [Generates DataIntegrityReport]
        │
        ▼
Normalization Pipeline (DataNormalizer) ───> [Generates NormalizedMarketRecords]
        │
        ▼
Reliability Tracker (DataSourceReliabilityTracker)
        │
        ▼
Internal Historical Repositories / Research Engine
        │
        ▼
    Agent Ecosystem / Intelligence Core
```

---

## 2. Core Service Components

### A. Data Gateway Layer (`src/Data/Gateway/`)
*   **ProviderRegistry**: Manages registrations of providers (`IDataProvider`) in memory.
*   **ProviderResolver**: Searches and matches the best healthy registered provider supporting a specific asset symbol.
*   **DataRequestRouter**: Dispatches retrieval payloads and handles failovers. If the primary provider connection crashes or fails, it automatically routes request payloads to alternate healthy providers to ensure safe degradation.

### B. Validation Intelligence (`src/Data/Validation/`)
*   **MarketDataValidator**: Performs schema structure and required field verification.
*   **DataQualityAnalyzer**: Performs multi-factor quality audits on records to measure:
    *   *Completeness*: Presence of expected fields and non-null values.
    *   *Timestamp Validity*: Correctness and structure of datetime parameters.
    *   *Uniqueness*: Duplicate timestamp detections.
    *   *Consistency*: Pricing rules checks (e.g. low $\le$ high, open/close inside range).
*   **DataIntegrityReport**: Contains scores and unacceptable anomalies lists. If the composite score falls below $0.80$, the dataset is rejected.

### C. Normalization Pipeline (`src/Data/Normalization/`)
*   **DataNormalizer**: Maps custom raw provider fields into standard `NormalizedMarketRecords` (standard datetime types, symbols, and float metrics) using `NormalizationRules` without losing original source metadata.

### D. Source Reliability Tracker (`src/Data/Reliability/`)
*   **DataSourceReliabilityTracker**: Logs metric records (availability, error rate, consistency, completeness) per provider to track and score performance over time.

---

## 3. Strict Security Boundaries (Zero Leakage)

To ensure absolute adherence to APES-FIN platform guidelines, the data connector layer enforces strict boundaries:
1.  **Zero Execution Access**: Absolutely no imports or references to `Broker`, `Order`, `Execution`, or `Position` namespaces.
2.  **No Action States**: External data is processed entirely passively, allowing simulation-only analysis without triggering BUY/SELL signaling or order dispatching.
3.  **Simulation Provider**: `SimulationDataProvider` supports off-grid scenario tests (valid, failures, exceptions, duplicates, low quality, price corruption) without requiring connection to live brokers.
