# 06. Data Layer

## 1. Provider-Independent Gateway Ingestion

The data layer abstracts external connections (`IDataProvider`) through the `ExternalDataGateway` façade:
*   **ProviderRegistry**: Manages registrations in memory.
*   **ProviderResolver**: Dynamic matching of symbols and health.
*   **DataRequestRouter**: Dispatches payloads and implements fallback failover routing.

---

## 2. Ingestion Processing Pipeline

```text
External Providers (MT5, Calendar, News, Simulation)
        │
        ▼
   Data Gateway (Resolver / Failover Routing)
        │
        ▼
Validation Layer (completeness, uniqueness, consistency)
        │
        ▼
Normalization Pipeline (Standard formats mapping)
        │
        ▼
Source Reliability Tracker (Latency & health reports)
```

---

## 3. Data Integrity & Quality Scores

The `DataQualityAnalyzer` validates:
*   *Completeness*: keys exist and are non-null.
*   *Timestamp Validity*: datetime types parse correctly.
*   *Uniqueness*: duplicate timestamps count is zero.
*   *Consistency*: price boundaries hold ($low \le high$ and $open/close \in [low, high]$).

Datasets are rejected if the composite score falls below $0.80$ or consistency falls below $0.80$.

---

## 4. Normalization Rules & Simulation

*   **DataNormalizer**: Maps raw fields to standard `NormalizedMarketRecords` (float values, ISO dates) while preserving original source metadata.
*   **SimulationDataProvider**: Off-grid simulation provider injected with clean, missing, timed out, or corrupted datasets to test robustness.

---

## 5. Cross References
*   [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
*   [04_INTELLIGENCE_PIPELINE.md](04_INTELLIGENCE_PIPELINE.md)
