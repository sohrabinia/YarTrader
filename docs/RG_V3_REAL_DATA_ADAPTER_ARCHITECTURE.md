# RG_V3 Real Market Data Intelligence Adapter Layer Architecture

This document describes the architectural design, connection monitoring, and secure read-only operations of the **Real Market Data Intelligence Adapter Layer (Phase 24)**.

---

## 1. Architectural Overview & Ingestion Flow

The Real Market Data Adapter Layer connects the platform with external real-world financial data feeds (MT5, macroeconomic calendars, news providers) through the secure, provider-independent gateway architecture established in Phase 23.

```
+───────────────────────────────────────────────+
|               Data Providers                  |
|                                               |
|  +──────────+   +───────────+   +──────────+  |
|  |   MT5    |   | Economic  |   |   News   |  |
|  +────┬─────+   +─────┬─────+   +────┬─────+  |
+───────┼───────────────┼──────────────┼────────+
        │               │              │ (fetch typed records)
        ▼               v              ▼
+───────────────────────────────────────────────+
|                 Data Gateway                  |
|                                               |
|   +---------------------------------------+   |
|   |         ExternalDataGateway           |   |
|   +---------------------------------------+   |
+───────────────────────┬───────────────────────+
                        │ (unidirectional flow)
                        ▼
+───────────────────────────────────────────────+
|         Validation & Normalization            |
|                                               |
|   +---------------------------------------+   |
|   |         DataQualityAnalyzer           |   |
|   +----------------───┬───────────────────+   |
|                       │                       |
|                       ▼                       |
|   +---------------------------------------+   |
|   |            DataNormalizer             |   |
|   +───────────────────┬───────────────────+   |
+───────────────────────┼───────────────────────+
                        │
                        ▼
+───────────────────────────────────────────────+
|         Source Reliability & Health           |
|                                               |
|   +---------------------------------------+   |
|   |     DataSourceReliabilityTracker      |   |
|   |      [Connection, Latency, Log]       |   |
|   +───────────────────┬───────────────────+   |
+───────────────────────┼───────────────────────+
                        ▼
            Research Intelligence Layer
```

---

## 2. Core Provider Modules

### A. MetaTrader 5 (MT5) Ingestion (`src/Data/Providers/MT5/`)
*   **MT5DataProvider**: Read-only historical rates and snapshot retriever. Tracks terminal connection status and pings.
*   **MT5DataMapper**: Transforms raw MT5 prices format into uniform standard `CandleRecords` or skips individual malformed entries safely.
*   **MT5ConnectionHealth**: Contains connectivity states, ping times (ms), server credentials, and terminal logs.

### B. Economic Calendar Ingestion (`src/Data/Providers/Economic/`)
*   **EconomicDataProvider**: Gathers macroeconomic updates (YoY CPI, NFP Payrolls, GDP indices) based on country, timestamp, and impact metrics. Contains zero forecast or predictive algorithms.

### C. News Feed Ingestion (`src/Data/Providers/News/`)
*   **NewsDataProvider**: Gathers passive text articles and metadata from verified sources. bar-guarded from creating direct automated transaction overrides or sentiment-based signals.

---

## 3. Advanced Provider Health Monitoring

`DataSourceReliabilityTracker` is extended with active connection check, response latency, and failure logs indicators to issue structured reports:

*   **Availability Score**: Chronological ratio of healthy connections.
*   **Response Latency Tracking**: Moving latency values (ms).
*   **Failure History Logs**: Chronological log of error messages capped to preserve memory bounds.

---

## 4. Security Rules & Non-Trading Bot Boundary

Every adapter contains absolute zero capabilities to execute financial transactions:
1.  **Strict Read-Only Mode**: Enforced in both code structure and contract boundaries. No order routing, positions, or account mutators can be compiled.
2.  **Compliance Checks**: Automatically scan and reject any modules featuring `Order`, `Execute`, `Trade`, `BrokerCommand`, or `PositionManagement` in namespace or AST nodes.
