# TRADEYAR Autonomous Financial Intelligence Platform
## Historical Data Intelligence Adapter Foundation (Phase 13)

This document provides a technical specification of the production-ready Historical Data Intelligence Adapter Layer designed in adherence with the **APES-FIN clean financial architecture standard**.

---

## 1. Architecture Overview

The Historical Data Adapter Layer decouples downstream research, strategy, and risk analysis from the raw mechanics of data ingestion and loading. It abstracts data sources (specifically CSV and JSON datasets) and provides unified, validated, and simulation-safe historical market data directly to the `IntelligencePipeline`.

The layer is fully comprised of the following key architectural components located under `src/Data/Adapters/`:

*   **`HistoricalDataAdapter`**: The primary gateway implementing `IMarketDataProvider`. It coordinates repository queries, translates parsed historical records to standardized domain market data points, and supports simulation-safe execution tracking.
*   **`MarketDataLoader`**: Responsible for reading raw dataset payloads from files or string buffers. It parses CSV and JSON formats and handles formatting variations or corrupted elements with clean error handling.
*   **`HistoricalDataValidator`**: A strict validator verifying the structural, relational, and physical correctness of records (e.g. non-negativity of prices, high-low boundary consistency, timestamp validity).
*   **`DatasetRepository`**: A thread-safe, high-performance in-memory repository managing the lifecycle, registration, and quick lookup of available datasets.

---

## 2. Unidirectional Data Flow

Data flows in a strictly unidirectional path from raw storage buffers down to portfolio decisions:

```
[ Raw CSV / JSON Dataset Source ]
                │
                ▼ (In-Memory Parsing / Case-Insensitive Headers)
       [ MarketDataLoader ]
                │
                ▼ (Relational & Physical Validations)
     [ HistoricalDataValidator ]
                │
                ▼ (Create HistoricalDataset)
       [ DatasetRepository ]
                │
                ▼ (Query Asset via IMarketDataProvider)
     [ HistoricalDataAdapter ]
                │
                ▼ (Standard MarketDataResponse)
     [ IntelligencePipeline ]  ─────► [ Research Layer ]
                │
                ▼
      [ Strategy Evaluation ]  ─────► [ Risk Assessment ]
                │
                ▼
       [ Decision Engine ]
```

---

## 3. Standardized Data Models

To avoid any framework or database locking, the adapter utilizes lightweight, immutable dataclasses. Under **APES-FIN design criteria**, these models are completely decoupled from database entities and omit any active trading properties (e.g., BUY/SELL signals, orders, positions, and profit executions are strictly prohibited).

The models reside under `src/Data/Models/`:

1.  **`DatasetMetadata`**: Holds identification, asset type, format details, timeframe, and tracking parameters of a loaded dataset.
2.  **`HistoricalRecord`**: Stores a standardized point-in-time pricing bar including:
    *   `AssetId` (Asset identifier)
    *   `Timestamp` (Date & Time of the observation)
    *   `Open`, `High`, `Low`, `Close` (OHLC prices)
    *   `Volume` (Market volume)
3.  **`HistoricalDataset`**: A combined structure grouping a `DatasetMetadata` record with its full list of `HistoricalRecord` objects.
4.  **`MarketDataBatch`**: A container holding all registered records for a single asset, offering a clean bulk retrieval interface.

---

## 4. Strict Validation Rules

The `HistoricalDataValidator` implements standard validation checks, raising `ValidationException` when any anomaly is encountered.

| Target | Validation Check | Failure Action |
| :--- | :--- | :--- |
| **Dataset** | Empty record set or null metadata | `ValidationException` |
| **Record** | Missing / blank `AssetId` or `Timestamp` | `ValidationException` |
| **Prices** | Negative value or unparseable text (NaN / Inf) | `ValidationException` |
| **Volume** | Negative or NaN / Inf values | `ValidationException` |
| **Logic** | `Low` is greater than `High` | `ValidationException` |
| **Logic** | `Open` / `Close` is higher than `High` | `ValidationException` |
| **Logic** | `Low` is higher than `Open` / `Close` | `ValidationException` |

---

## 5. Dataset Lifecycle Management

Datasets inside the `DatasetRepository` follow a standard, predictable lifecycle:

```
[ Raw Source ] ──► [ Load & Parse ] ──► [ Validate ] ──► [ Register ] ──► [ Retrieve / Query ] ──► [ Deregister / Delete ]
```

1.  **Registration**: Datasets are registered via `HistoricalDataAdapter.load_and_register_dataset(...)`. The loading, parsing, and logical validation are executed synchronously.
2.  **Storage**: The repository indexes datasets by both their unique `DatasetId` and their associated `AssetId`.
3.  **Deregistration**: `DatasetRepository.delete_dataset(dataset_id)` cleanly purges references, allowing garbage collection to reclaim memory.

---

## 6. Pipeline Integration

Because `HistoricalDataAdapter` implements `IMarketDataProvider`, it integrates natively into the `IntelligencePipeline` without any modification of existing orchestration logic.

### Integration Example:

```python
from datetime import datetime
from src.Data import HistoricalDataAdapter
from src.Application import IntelligencePipeline, PipelineContext, PipelineConfig
from src.Core.entities import RiskProfile

# 1. Initialize historical data layer
adapter = HistoricalDataAdapter()

# 2. Register CSV data
csv_data = "timestamp,open,high,low,close,volume,asset_id\n2026-03-01T00:00:00,100,105,98,102,15000,AAPL"
adapter.load_and_register_dataset(
    dataset_id="AAPL-D1-SET",
    name="AAPL Daily Historical",
    asset_id="AAPL",
    timeframe="D1",
    source=csv_data,
    format="CSV",
    is_filepath=False
)

# 3. Instantiate orchestration pipeline
pipeline = IntelligencePipeline(
    data_provider=adapter,
    research_engine=research_engine,
    strategy_evaluator=strategy_evaluator,
    risk_engine=risk_engine,
    decision_engine=decision_engine
)

# 4. Trigger safe simulation execution
context = PipelineContext(
    StartTime=datetime.fromisoformat("2026-03-01T00:00:00"),
    Asset="AAPL",
    Timeframe="D1",
    TargetRiskProfile=RiskProfile("Moderate", 1.0, 0.90)
)
result = pipeline.execute(context)
```

---

## 7. Extensions and Scalability

The Historical Data Adapter is designed to be highly extensible without requiring redesign of existing structures:

*   **Parquet / HDF5 Support**: By subclassing or extending `MarketDataLoader`, parquet loading can be introduced natively.
*   **SQL Database Backends**: The `DatasetRepository` can be subclassed to delegate dataset storage to SQL, NoSQL, or timeseries-oriented databases (e.g., InfluxDB, TimescaleDB).
*   **Timeframe Resampling**: New normalization modules can be plugged in to dynamically resample high-frequency records (e.g., M1) into lower frequencies (e.g., H1, D1) before validation.
