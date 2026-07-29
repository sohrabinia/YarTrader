# Live Market Research Architecture & Intelligence Pipeline

This document details the design, data flow, component layout, configuration, troubleshooting steps, and safety guidelines of the **TradeYar AI Live Market Research & Intelligence Pipeline**.

---

## 1. High-Level Data Flow

The flow of information moves in a strictly unidirectional, descriptive-analytical pipeline, ensuring that real MetaTrader 5 market data reaches the AI analysis layers while enforcing absolute read-only safety:

```
┌────────────────────────────────────────────────────────┐
│                  MetaTrader 5 Terminal                 │
│                 (Real Current & Historical Rates)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              MT5DataProvider (Read-Only)               │
│               (Normalizes raw MT5 rates)               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             MarketData Provider Adapter                │
│            (Maps CandleRecord to MarketDataPoint)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                Research Runtime Worker                 │
│         (Daemon Polling Thread - Scheduled Runs)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                Market Research Engine                  │
│       (Orchestrates Analytical Pipelines & AI Layers)  │
└───────────────────────────┬────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌────────────────────────────────┐    ┌────────────────────────────────┐
│   Technical Analysis Engine    │    │   Feature Engineering Layer    │
│  (EMA, SMA, RSI, ATR, Support) │    │  (Calculators, FeatureSets)    │
└───────────────┬────────────────┘    └───────────────┬────────────────┘
                │                                     │
                └───────────────────┬─────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────┐
│            Market Regime & Pattern Detection           │
│      (Trend direction, volatility state, regimes)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Smart Interpretation Engine                │
│    (AI Bias, Confidence Score, Qualitative Reasoning)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Research Storage Snapshots               │
│               (JSON disk persistence layer)            │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI Dashboard / REST API              │
│       (Exposes state, health, history, and UI Panel)   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystem Components

1. **MT5DataProvider (`src/Data/Providers/MT5/mt5.py`)**: Responsible for establishing direct read-only connection to the MetaTrader 5 terminal, fetching high-frequency historical bars (rates range), and converting them into standard `CandleRecord` models. On non-Windows platforms, it automatically activates a high-fidelity synthetic fallback sequence generator.
2. **MetaTrader5Provider Adapter (`src/Data/MarketData/Providers/providers.py`)**: Converts raw `CandleRecord` arrays into normalized `MarketDataPoint` sequences, satisfying clean decoupled layer separation.
3. **ResearchRuntime Worker (`src/Application/Runtime/research_runtime.py`)**: Spawns a background polling daemon loop executing every 60 seconds (configurable). It polls the latest candles from MT5, triggers the analysis pipeline, and stores serialized research snapshots to disk.
4. **Market Research Engine (`src/Research/MarketAnalysis/Services/services.py`)**: Integrates and coordinates the six math and AI modules.
5. **Technical Analysis Engine (`src/Research/analysis_pipeline.py`)**: Calculates indicators including Simple Moving Average (SMA), Exponential Moving Average (EMA), Relative Strength Index (RSI), Average True Range (ATR), and support/resistance levels.
6. **Feature Engineering Layer (`src/Research/analysis_pipeline.py`)**: Executes the standard registered feature pipeline to extract multi-factor price, statistical, trend, and volatility properties.
7. **Market Regime Detection (`src/Research/analysis_pipeline.py`)**: Classifies the market regime state (e.g. Quiet Range-Bound, High Volatility Breakout/Expansion, Strong Trending).
8. **Smart Interpretation Engine (`src/Research/analysis_pipeline.py`)**: Evaluates compiled signals to synthesize a final market bias (Bullish/Bearish/Neutral), quantitative confidence score, and qualitative reasoning bullet points.
9. **Dashboard Integration & API (`src/Application/Services/web_dashboard.py`)**: Exposes four dedicated endpoints (`/v1/dashboard/research`, `/api/research/current`, `/api/research/history`, `/api/research/health`) and renders a beautiful live visual card on the single-page application dashboard.

---

## 3. Strict APES-FIN Safety Boundaries

TradeYar AI is structurally restricted to a passive, read-only administrative control center. The following design parameters enforce absolute safety:

- **Trading Commands Prohibited**: No endpoints, methods, variables, or packages exist for executing trades, sending transactions, opening/modifying/closing positions, or adjusting leverage and account settings.
- **Forbidden Keywords Scanned**: Standard Abstract Syntax Tree (AST) compliance scanners inspect the codebase to verify that forbidden keys like `order_send`, `place_order`, `send_transaction`, and `order_modify` are never defined or called.
- **Connection Isolation**: The MetaTrader 5 API connection is established strictly in read-only terminal mode, forbidding administrative broker or transaction operations.

---

## 4. Configuration & Troubleshooting

### Configuration

The background polling loop frequency is configured via the standard scheduled parameter:

```python
RESEARCH_INTERVAL_SECONDS = 60.0
```

Snapshots are automatically persisted under:
`runtime_logs/research_snapshots/snapshot_<report_id>.json`

### Troubleshooting

- **MT5 Status Shows DISCONNECTED**:
  1. Verify the MT5 Terminal is running on the host system.
  2. Confirm "Allow Algorithmic Trading" is checked in the MT5 Terminal Settings.
  3. Ensure that the active network broker account is connected.
- **Running on Linux/MacOS Non-Windows Environment**:
  - The system detects the environment and automatically runs in **Synthetic Fallback Mode**, generating high-fidelity mock candles matching standard XAUUSD behaviors, enabling continuous testing, local execution, and verification.
