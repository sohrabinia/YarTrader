# Multi-Asset & Multi-Resolution Cognitive Intelligence Architecture
## TradeYar AI v3.3 - Enterprise Production Edition

This document details the architectural specifications, designs, and isolation boundaries of the **Multi-Asset & Multi-Resolution Cognitive Intelligence Platform** implemented inside TradeYar AI v3.3.

---

## 1. Architectural Mission & Objectives

To support professional-grade, multi-asset institutional research, the platform must process and analyze multiple concurrent symbols and internal timeframes without performance degradation or data cross-contamination.

The architecture provides:
- **Concurrent Asset Management**: Support for up to 30 concurrent symbols dynamically managed.
- **Broker-Timeframe Independence**: Complete decoupling of AI research structures from MT5 standard candles.
- **Absolute Memory Isolation**: Encapsulation of cognitive assets (Ticks, Shadow Trades, Bases, Nodes, Patterns, and Learning updates) per symbol/timeframe context.
- **Strict Interface Decoupling**: Admin Deep-Dive analytics are completely isolated from clean, user-visible horizon signals.

---

## 2. Multi-Resolution Cognitive Framing

The system constructs custom, integer-based time structures pure mathematically from raw ticks, discarding broker timeframes (such as M1, M5, etc.).

### 2.1 Default Frames
- `1` / `4`: Short Horizon views.
- `16` / `64`: Medium Horizon views.
- `256` / `1024`: Long Horizon views.

### 2.2 Accumulation State
Each resolution frame operates its own local state buffer containing the duration, high, low, open, close, and price ranges of tick blocks.

---

## 3. Isolated Cognitive Contexts (`SymbolTimeContext`)

The fundamental unit of system isolation is the `SymbolTimeContext`. It binds a unique Symbol and an Internal Frame together (e.g., `BTCUSD_256`).

```
                              PredictiveShadowEngine
                                        │
           +----------------------------┼----------------------------+
           │                            │                            │
  [XAUUSD_64 Context]           [BTCUSD_256 Context]         [EURUSD_4 Context]
   ├── Ticks Buffer              ├── Ticks Buffer             ├── Ticks Buffer
   ├── Base/Node Memories        ├── Base/Node Memories       ├── Base/Node Memories
   ├── Pattern Outcomes          ├── Pattern Outcomes         ├── Pattern Outcomes
   ├── Learning History          ├── Learning History         ├── Learning History
   └── Shadow Trades             └── Shadow Trades            └── Shadow Trades
```

- **Data Contamination Prevention**: Pattern outcomes and weight calibrations registered in the `BTCUSD` context are physically separated from those of `XAUUSD`, avoiding confirmation biases and strategy pollution.
- **Independent Statistics**: Each context compiles its own win rate, total trade cycles, and average confidence indicators without merging metrics.

---

## 4. Concurrent Predictive Shadow Trading

Predictive virtual orders are placed and evaluated within their specific `SymbolTimeContext` domain.
- **State Machine Lifecycle**: Orders are created *before* the market price arrives at the target zone (`CREATED` -> `RUNNING` -> `TARGET_HIT` / `STOP_HIT`).
- **Retrospective Reviews**: Retrospective outcomes are audited by the independent Judge Brain and written exclusively to the context's local pattern outcome history.

---

## 5. Secure Route & Interface Isolation

To preserve high-end, proprietary research logic and support multi-user operations securely:

### 5.1 Admin Supervision Panel (`/api/admin/`)
- Protected behind the `check_admin_guard` requiring JWT role attributes.
- **Symbols Management (`/symbols`)**: Lists and monitors active contexts. Enforces a maximum operational limit of 30 active symbols dynamically.
- **Timeframes Overview (`/timeframes`)**: Exposes structural health indicators of isolated contexts.
- **Reports Dashboard (`/reports`)**: Generates separate, unmerged analytics reports filterable by symbol and frame context.

### 5.2 User Application Panel (`/api/user/`)
- Exposed to authenticated user sessions.
- **Markets (`/markets`)**: Lists simplified, intuitive categories.
- **Signals (`/signals`)**: Serves cleaned horizon-mapped trading signals (Direction, Entry Zone, Target, Invalidation, Confidence, Status) derived strictly from underlying context shadow trades, hiding all raw mathematical matrices.

---

## 6. SRE Resource Limits & Governance

- **System Limit Config**: Hard-capped at 30 concurrent symbols defined inside `config/system_limits.yaml`.
- **Hydration Bypass**: Existing historical records loaded from `runtime_logs/shadow_trades.json` on startup are hydrated directly into their contexts, bypassing SRE limit checks to ensure non-destructive cumulative data storage under all conditions.
