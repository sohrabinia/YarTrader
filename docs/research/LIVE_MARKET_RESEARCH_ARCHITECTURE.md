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
9. **Dashboard Integration & API (`src/Application/Services/web_dashboard.py`)**: Exposes the REST endpoints and renders a beautiful bilingual live visual card on the single-page application dashboard.

---

## 3. REST API Contract

The following endpoints comprise the finalized, production-hardened Live Market Research API Contract:

### A. GET `/api/research/current`
Returns the latest completed market research snapshot, checking disk storage snapshots first for true persistence across boots, with in-memory fallback.
* **Response Schema:**
  ```json
  {
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "bias": "Bullish",
    "confidence": 77,
    "reasoning": [
      "Price is trading above the SMA20 short-term trend line.",
      "RSI is in bullish territory (>50) with positive demand accumulation.",
      "MACD histogram remains above zero, confirming upward momentum."
    ],
    "timestamp": "2026-07-29T10:29:19.486497",
    "indicators": {
      "sma_20": 2305.05,
      "ema_12": 2305.45,
      "rsi": 100.0,
      "atr": 0.3
    }
  }
  ```

### B. GET `/api/research/latest`
Returns the latest completed market research analysis. Alias of `/api/research/current`.

### C. GET `/api/research/history`
Returns a list of the previous analyses (up to the latest 50 files) read dynamically from disk serialized snapshots for absolute persistence.

### D. GET `/api/research/health`
Returns details on worker lifecycle states, connection states, and polling metrics metadata.
* **Response Schema:**
  ```json
  {
    "mt5_status": "ONLINE",
    "worker_running": true,
    "last_analysis_time": "2026-07-29T10:29:19.486497",
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "worker_started_at": "2026-07-29T10:28:19.001254",
    "last_successful_cycle": "2026-07-29T10:29:19.486497",
    "cycle_count": 1,
    "last_error": null,
    "last_candle_time": "2026-07-29T10:29:19.486497",
    "last_result_id": "rpt-XAUUSD-3636238b"
  }
  ```

### E. GET `/v1/dashboard/live-research`
Backward-compatible alias of `/api/research/current`.

---

## 4. Dashboard Integration Flow

The single-page application (SPA) Dashboard integrates with the Live Market Research worker dynamically:
1. **On Load**: Detects user language (defaulting to Persian `fa` with an RTL layout and system/Vazirmatn fonts; supports switching to English `en` LTR layout).
2. **Periodic Polling**: Connects to the `/api/research/current` REST endpoint every 5 seconds.
3. **Dynamic Translation & Mapping**: Updates all labels, market bias (Bullish/Bearish/Neutral), confidence levels, technical metrics, and qualitative AI explanations dynamically using zero template literal syntax to avoid any leakage or parsing failures.
4. **Validation Center Sync**: Automatically loads the existing `validation/production_acceptance_report.json` report on FastAPI boot to initialize the Production Readiness Score card with real results (e.g., 100% Readiness) on page load instead of displaying 0%.

---

## 5. Strict APES-FIN Safety Boundaries & Security Model

TradeYar AI is structurally restricted to a passive, read-only administrative control center. The following design parameters enforce absolute safety:

- **Trading Commands Prohibited**: No endpoints, methods, variables, or packages exist for executing trades, sending transactions, opening/modifying/closing positions, or adjusting leverage and account settings.
- **Forbidden Keywords Scanned**: Standard Abstract Syntax Tree (AST) compliance scanners inspect the codebase to verify that forbidden keys like `order_send`, `place_order`, `send_transaction`, and `order_modify` are never defined or called.
- **Connection Isolation**: The MetaTrader 5 API connection is established strictly in read-only terminal mode, forbidding administrative broker or transaction operations.

---

## 6. Configuration & Troubleshooting

### Deployment Instructions

To launch the Live Market Research Platform:
1. Ensure the Python environment is set up with dependencies pinned in `requirements.txt`.
2. Run the main web management gateway dashboard:
   ```bash
   PYTHONPATH=. uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
   ```
3. Navigate to `http://localhost:8000` to view the localized dashboard and live panel.

### Troubleshooting Guide

- **MT5 Status Shows DISCONNECTED / OFFLINE**:
  1. Verify the MT5 Terminal is running on the host system.
  2. Confirm "Allow Algorithmic Trading" is checked in the MT5 Terminal Settings.
  3. Ensure that the active network broker account is connected.
- **Running on Linux/MacOS Non-Windows Environment**:
  - The system detects the environment and automatically runs in **Synthetic Fallback Mode**, generating high-fidelity mock candles matching standard XAUUSD behaviors, enabling continuous testing, local execution, and verification.
