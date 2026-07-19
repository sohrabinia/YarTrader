# Phase 21 — Live Research Runtime & MT5 Data Integration

This document outlines the design, data flow, runtime lifecycle, safety boundaries, extension points, and known limitations of the **Phase 21 Live Research Runtime** implementing real-time market observation for the **XAUUSD** symbol on the **H1** timeframe under strictly read-only non-trading parameters.

---

## 1. Final Runtime Architecture

The Live Research Runtime is built as a highly decoupled, clean architecture module integrating the passive analytical elements of the application layer with external data gateways:

```
┌────────────────────────────────────────────────────────┐
│                   Application Layer                    │
│                                                        │
│               ┌───────────────────────┐                │
│               │    ResearchRuntime    │                │
│               └───────────┬───────────┘                │
│                           │                            │
│                           ▼                            │
│         ┌───────────────────────────────────┐          │
│         │ FeatureExtractionResearchEngine   │          │
│         └─────────────────┬─────────────────┘          │
│                           │                            │
└───────────────────────────┼────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────┐
│                    Data & Domain Layer                 │
│                           │                            │
│                           ▼                            │
│               ┌───────────────────────┐                │
│               │ MetaTrader5Provider   │                │
│               └───────────┬───────────┘                │
│                           │                            │
│                           ▼                            │
│               ┌───────────────────────┐                │
│               │    MT5DataProvider    │                │
│               └───────────────────────┘                │
│                                                        │
└────────────────────────────────────────────────────────┘
```

- **MetaTrader5Provider** (`src/Data/MarketData/Providers/providers.py`): An Adapter class implementing `IMarketDataProvider`. It receives target-level data models, translates them, delegates the actual rate-fetching to the existing `MT5DataProvider`, and maps results to standard `MarketDataPoint` OHLCV instances.
- **ResearchRuntime** (`src/Application/Runtime/research_runtime.py`): The central polling orchestrator that initiates periodic polling runs or synchronous single cycles, handles execution logs, and records complete evidence footprints under `runtime_logs/`.

---

## 2. Unidirectional Data Flow

The flow of information moves in a strictly unidirectional, passive analytical pipeline:

1. **Trigger**: `ResearchRuntime` starts an iteration for symbol `XAUUSD`, timeframe `H1`.
2. **Retrieve**: The runtime constructs a `MarketDataRequest` and calls `MetaTrader5Provider.retrieve_market_data()`.
3. **Delegate**: `MetaTrader5Provider` delegates data retrieval to the read-only `MT5DataProvider`, fetching raw rates.
4. **Normalize**: Raw rates are converted to standard `CandleRecord`s and mapped to target `MarketDataPoint`s.
5. **Enrich**: `FeatureExtractionResearchEngine` computes mathematical features (Price, Volatility, Trend, Statistical) from standard candles and wraps them in a `MarketFeatureSet` inside the request context.
6. **Analyze**: The core `ResearchEngine` analyzes features, matching behavioral pattern observations and producing qualitative insights.
7. **Store & Log**: The finalized `ResearchResult` containing research reports is cached in runtime memory, and complete execution details are appended to the local logs.

---

## 3. Runtime Lifecycle

The runtime implements a robust, thread-safe execution lifecycle:
- **Initialization**: Instantiates providers and injected engines, verifying directory permissions and fallback states.
- **Start / Polling Loop**: Initiates asynchronous or synchronous iterations.
- **Recovery and Cooldown**: If an iteration encounters an MT5 connection drop or invalid data payload, the runtime records a warning log, cools down, and safely resumes the polling sequence without interrupting the platform.
- **Teardown**: Signals the loop to terminate, flushing log buffers and releasing locks.

---

## 4. Extension Points

- **Additional Upstream Providers**: Create alternative data sources conforming to `IMarketDataProvider` (e.g. `ExchangeProvider` or `FileImportProvider`) and seamlessly hot-swap them via dependency injection.
- **Analytical Feature Calculators**: Extend `IFeatureCalculator` to inject custom descriptors (e.g., custom momentum oscillators or support levels) without altering the core pipeline.
- **Persistence Adaptability**: Swap the internal in-memory history log for high-performance time-series databases by implementing `IResearchRepository`.

---

## 5. Safety Boundaries & APES-FIN Compliance

The Live Research Runtime complies 100% with standard **APES-FIN** (Autonomous Portfolio and Execution Safety - Financial) guidelines:
- **Absolute Non-Trading Enforcement**: Strictly limits MT5 interaction to read-only historical and current rate queries. Absolutely no functions, variables, or definitions related to order placement, transaction messaging, leverage, margin, balance, or broker state exist in the runtime codebase.
- **Execution Leakage Protection**: Verified by context-aware compliance scanners ensuring no active trading instructions are generated or processed.
- **Decoupled Logic**: No external trading APIs have access to or dependencies on core domain business rules.

---

## 6. Known Limitations

- **Simulated Windows Fallback**: Since the official MT5 Python Library is restricted to Windows OS environments, non-Windows systems (including standard Docker/Linux environments) automatically execute using a synthetic historical sequence generator within `MT5DataProvider`, ensuring complete environment portability and validation coverage.
- **In-Memory Retention**: Currently records completed report states in memory caches. Production rollouts should swap memory stores for highly durable persistent databases under high frequency or long execution periods.
