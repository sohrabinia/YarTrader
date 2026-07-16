# MetaTrader 5 Autonomous Market Research Runtime Platform

This guide documents the architecture, configuration parameters, execution loops, and Shadow Mode compliance policies for the Phase 40 Autonomous Market Research Runtime.

## 1. Runtime Architecture

The Autonomous Market Research Runtime continuously ingests live or synthetic market candles from MetaTrader 5, validates the structure and quality, computes advanced indicators (features), and triggers automated research pipelines to compile descriptive intelligence reports.

```
          MetaTrader 5 Terminal
                    |
                    v
      MetaTrader5MarketDataProvider
                    |
                    v
         Data Quality Validation
                    |
                    v
    FeatureExtractionResearchEngine
                    |
                    v
            FeaturePipeline
                    |
                    v
             ResearchEngine
                    |
                    v
        InMemoryResearchRepository
```

## 2. Configuration & Execution

The runtime is fully configurable through command-line options and environment variables:

- `--asset`: Asset symbol to evaluate (e.g. `XAUUSD`, `EURUSD`).
- `--timeframe`: Target interval timeframe (`M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`).
- `--bars`: Count of historical candles to analyze (default: `10`).
- `--interval`: Polling interval in seconds (default: `5`).
- `--once`: Set to `true` to run a single iteration and exit immediately.

### Launching the Runtime

Execute the standalone program from the command line:

```bash
python -m src.Runtime.research_runtime --asset XAUUSD --timeframe H1
```

## 3. Strict Shadow-Mode Constraints

In compliance with APES-FIN financial rules, this runtime is **100% read-only and analytical**.
- **No Trading Execution**: No transactions are submitted, no orders are created, and no active capital is managed.
- **Data Confinement**: Extracted metrics, patterns, and compiled research reports are persisted strictly to the `InMemoryResearchRepository` and isolated storage.
- **Validation Layers**: Structural validators ensure that zero trading signals or buy/sell execution actions can leak into downstream components.
