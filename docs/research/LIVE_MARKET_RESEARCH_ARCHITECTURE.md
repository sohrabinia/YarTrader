# TradeYar AI — Live Market Research Production Architecture

This document defines the complete production architecture, data flow, worker lifecycle, and safety boundaries for the continuous read-only **Live Market Research Pipeline** targeting **XAUUSD H1** timeframe.

---

## 1. System Architecture & Flow

The live research architecture connects the real-time MT5 database safely with the passive feature extraction pipeline and analytical intelligence models:

```
┌──────────────────────────────────────────────────────────────────┐
│                           MetaTrader 5                           │
│                     (Real-Time H1 Rates Feed)                    │
└────────────────────────────────f─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   MT5DataProvider (Read-Only)                    │
│      - Handles real copy_rates_range connection queries          │
│      - Automatically isolated from trading transaction APIs      │
└────────────────────────────────f─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│               MetaTrader5Provider (Data Adapter)                 │
│      - Converts raw Rates Arrays into TargetMarketDataPoints     │
└────────────────────────────────f─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                  LiveResearchWorker (Daemon)                     │
│      - Triggers periodic fetching runs at configurable intervals │
│      - Detects new candle arrivals dynamically                   │
└────────────────────────────────f─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│             Mathematical Indicators & Feature Extract            │
│      - Computes SMA50, RSI, MACD, ATR, Pivot Support/Resistance  │
└────────────────────────────────f─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│               Existing Passive Intelligence Modules              │
│      - Calculates Market States: Volatility, Momentum, Regime    │
│      - Determines AI Bias, Confidence Score & reasoning          │
└────────────────────────────────f─────────────────────────────────┘
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│        Production APIs          │       │         Web Dashboard           │
│   GET /api/research/current     │       │   Real-time Farsi (RTL) &     │
│   GET /api/research/history     │       │   English (LTR) Live Monitor    │
│   GET /api/research/health      │       │   Panel (Auto-polling)          │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

---

## 2. Unidirectional Data Flow

1. **Retrieve:** The background worker constructs a query for XAUUSD H1 candles.
2. **Translate:** MT5DataProvider delegates to the local terminal, fetching standard arrays.
3. **Map Features:** Closes, Highs, Lows, and Volumes are mapped, and indicators (MA, RSI, MACD, ATR, Support, Resistance) are calculated.
4. **Analyze State:** Existing modules classify Trend, Momentum, Volatility, and Market Regime.
5. **AI Interpretation:** Price location versus MA and indicator momentum is translated into a Bias (Bullish, Bearish, Neutral), a Confidence Score (40% to 95%), and matching analytical reasoning blocks.
6. **Persist:** Latest findings append to `validation/research_history.json`.
7. **Expose:** Data is served via REST APIs and rendered on the Dashboard.

---

## 3. Background Worker Lifecycle

The `LiveResearchWorker` background worker starts automatically during FastAPI application boot-up:
- **Initialization:** Loads previous localized history from `validation/research_history.json`.
- **Worker Polling Loop:** Periodically pulls latest rates matching the `RESEARCH_INTERVAL_SECONDS` configuration.
- **Deduplication:** Updates state only if new candles are detected.
- **Robust Auto-Recovery:** If the MT5 terminal connection drops, the worker logs a reconnect warning, sleeps, recovers connections cleanly, and successfully logs recovery.
- **Crash Immunity:** Loop wraps inside high-level exception handlers ensuring it never terminates the host application.

---

## 4. REST APIs and Dashboard

### REST Endpoints
- **GET `/api/research/current`**: Retrieves latest parsed research payload.
- **GET `/api/research/history`**: Retrieves list of historical analysis items.
- **GET `/api/research/health`**: Retrieves diagnostic status including MT5 connected flag, worker running state, timestamps, and current latencies.

### Dashboard SPA Integration
A dedicated "Live Research Monitor" card is integrated on the Web Management Dashboard:
- Styled with **Vazirmatn** under right-to-left Persian layout.
- Styled with clean standard system-ui under English LTR.
- Automatically polls `/api/research/current` and `/api/research/health` dynamically without manual browser page refreshes.

---

## 5. Non-Trading Security Audit & Compliance

The entire live research pipeline conforms strictly to **APES-FIN** non-trading safety standards:
- **Zero Trading APIs:** No code or function definitions match forbidden symbols such as `order_send`, `order_check`, `positions_open`, `buy`, `sell`, `modify position`, or `close position` inside active paths.
- **Read-Only Enforcements:** Verified by comprehensive test audits executing recursively to guarantee zero order execution leakage.
- **Complete Isolation:** Demo and Simulation scripts remain strictly nested under isolated directories away from the live research worker.
