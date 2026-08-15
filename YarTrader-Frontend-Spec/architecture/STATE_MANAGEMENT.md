# STATE_MANAGEMENT.md — State Management

This document defines how client-side state is structured, updated, and synchronized in TradeYar AI.

## 💾 Core Stores

The frontend state is partitioned into three independent stores to prevent cross-contamination of concerns and maximize rendering efficiency:

```
                  ┌─────────────────────────────────────────┐
                  │           Client-Side Stores            │
                  └────┬─────────────────┬──────────────┬───┘
                       │                 │              │
                       ▼                 ▼              ▼
           ┌──────────────────────┐┌───────────┐┌───────────────┐
           │    Terminal Store    ││SRE Store  ││  Auth Store   │
           ├──────────────────────┤├───────────┤├───────────────┤
           │ - Symbol registry    ││- Telemetry││- User role    │
           │ - Active 8 TFs state ││- Health   ││- Session      │
           │ - Shadow positions   ││- Incidents││- AI limits    │
           │ - Market metrics     ││- Logs     ││- Auth history │
           └──────────────────────┘└───────────┘└───────────────┘
```

---

### 1. Terminal Store (`useTerminalStore`)
Responsible for preserving active symbols, the configured 8-timeframe analytical matrix (M1 to MN1), real-time price updates, and virtual position states.

- **Primary States:**
  - `activeSymbols`: Array of active trading symbols (max limit: 30 Symbols governed by `config/system_limits.yaml`).
  - `selectedSymbol`: Current symbol chosen by user (e.g. `XAUUSD`).
  - `selectedTimeframe`: Standard chosen timeframe.
  - `marketDataMatrix`: Mapping of `{ symbol: { timeframe: { price, trend_state, intelligence_score, risk_status, decision_state } } }`.
  - `virtualPositions`: Array of simulated open/closed virtual trades synced from the Shadow Trading Engine.
- **Sync Actions:**
  - `fetchActiveSymbols()`: Populates symbols from `GET /api/user/markets`.
  - `updateTick(tickData)`: Reducer to patch specific symbol/timeframe tick fields in real-time from the WebSocket.
  - `fetchShadowPositions()`: Re-sync virtual position status on user request or heartbeat intervals from `GET /api/admin/shadow-trades` or `GET /api/user/history`.

---

### 2. SRE & Observability Store (`useSreStore`)
Stores runtime metrics, system states, and service status parameters monitored by SRE Operators.

- **Primary States:**
  - `apiStatus`: Process liveness and API responsiveness metrics (Healthy/Degraded/Critical).
  - `mt5Status`: Core MetaTrader5 connection status, broker latency, account number, connection server, and last successful fetch timestamp.
  - `workerStatuses`: Object representing status of:
    - `ResearchWorker`: (STARTING/RUNNING/IDLE/FAILED/STOPPED)
    - `IntelligenceWorker`: (STARTING/RUNNING/IDLE/FAILED/STOPPED)
    - `ShadowWorker`: (STARTING/RUNNING/IDLE/FAILED/STOPPED)
  - `memoryStats`: Diagnostic stats on loaded patterns, cognitive hypotheses, validated/rejected concepts, and database file parse integrity (`auth.json`).
  - `incidentLogs`: SRE logs and incident alerts.
- **Sync Actions:**
  - `pollSreDiagnostics()`: Background worker that executes a query to `GET /api/v1/health` and `GET /api/devops/metrics` every 10 seconds.
  - `handleIncidentAlert(alert)`: Inserts a critical incident card into the top of the SRE Admin timeline.

---

### 3. Authentication & Session Store (`useAuthStore`)
Stores credentials, roles, session tokens, and daily usage counters.

- **Primary States:**
  - `user`: `{ email, role: 'ADMIN'|'USER'|'PRO'|'PREMIUM', name }`
  - `sessionToken`: Secure cryptographic string.
  - `supportUsageCount`: Number of AI support queries executed today (USER: max 10, PRO: max 100, PREMIUM: max 500, ADMIN: unlimited).
- **Sync Actions:**
  - `loginUser(credentials)`: Calls `POST /api/auth/login`.
  - `logoutUser()`: Invokes `POST /api/auth/logout` and clears state.
  - `incrementAiUsage()`: Increments and synchronizes usage metrics with backend limits database (`runtime_logs/auth.json`).

---

## 🔀 Synchronization Strategy

1. **Optimistic UI Updates:** Allowed only for virtual position cancellations. If a shadow position is closed, the UI updates the position state to "CLOSING" instantly before the server acknowledges.
2. **Read-Only Enforcements:** Cognitive data and SRE telemetry can never be modified locally; they must be fully populated via downstream read-only APIs or real-time WebSocket feeds.
3. **Session Expiry Hook:** Global middleware triggers an automatic redirect to `/` with a session-expired warning if any request returns `401 Unauthorized`.
