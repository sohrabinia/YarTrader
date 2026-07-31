# Shadow Trading Engine Implementation
*TradeYar AI — Live Cognitive Forward-Testing Architecture*

---

## 1. Architectural Overview

The **Shadow Trading Engine** provides a fully simulated, high-fidelity virtual trading environment for TradeYar AI. It allows the system to execute, monitor, and audit trading hypotheses on real-time market data streams without exposing real capital or making real-world broker execution calls.

This module is designed in strict compliance with the **APES-FIN non-trading read-only guidelines**. It has absolutely zero order-execution, balance-funding, or real order-placement capabilities.

---

## 2. Core Domain Models

The engine utilizes three primary domain models located under `src/ShadowTrading/Domain/`:

### A. VirtualAccount
* Tracks virtual account variables (`Balance` and `Equity`).
* Tracks active/open and completed/closed position dictionaries.
* Recalculates `Equity` in real-time as:
  $$\text{Equity} = \text{Balance} + \sum \text{Floating Position Profits/Losses}$$

### B. VirtualPosition
* Models simulated execution positions containing ID, symbol, direction (`BUY` or `SELL`), entry price, current price, stop-loss, take-profit, open/close timestamps, P/L, and matched evidence.
* Evaluates real-time price updates and returns positive/negative yields depending on `BUY`/`SELL` logic.

### C. TradeState
* Declares standard lifecycle states for positions:
  - `PositionStatus.OPEN`: Newly opened, awaiting first rate update.
  - `PositionStatus.MONITORING`: Actively tracking price fluctuations.
  - `PositionStatus.CLOSED`: Execution finalized on manual or SL/TP breach.

---

## 3. End-to-End Data Flow & Lifecycle

```
[MT5 Live Rates] ──► [ResearchRuntime] ──► [Decision Intelligence]
                             │                       │
                             ▼                       ▼
                     [Update Prices]       [handle_decision()]
                             │                       │
                             ▼                       ▼
                     [Position Lifecycle Monitoring & SL/TP Check]
                             │
                             ▼ (If Hit/Exit)
                      [Virtual Close]
                             │
                             ▼
                     [TradeEvaluator]
                             │
                     ├───────┼────────┐
                     ▼                ▼
               [JudgeBrain]   [MarketMemorySystem] (ExperienceMemory)
```

1. **Simulated Decision Consumption**: When the decision intelligence pipeline produces an approved bias (`Bullish` -> `BUY`, `Bearish` -> `SELL`), the `ShadowTradingEngine` registers a new `VirtualPosition` at the current market price with default or parameterized SL/TP boundaries.
2. **Price Stream Polling**: The continuous `ResearchRuntime` daemon feed ticks the current close price to `update_market_price()`.
3. **Execution & Exit Checking**: Open positions check current prices against their stop-loss and take-profit thresholds.
4. **Independent Evaluation (Judge Integration)**: Closed positions are routed to the independent `JudgeBrain` to calculate Reasoning Quality vs. Decision Quality and assess "lucky wins."
5. **Memory Consolidation**: Closed positions are permanently chronicled as standard `ExperienceMemory` objects inside the existing file-based database for learning optimization.

---

## 4. Limitations & Safe Separations

* **No Broker Integration**: Position updates, margins, and account balances reside entirely in-memory and are backed strictly by local file persistence. There is no active broker or trading server interface.
* **Passive Execution Multithreading**: Price polling is handled on background polling threads, ensuring that performance checks have zero overhead or latency impact on the research runtime core.
* **Non-Trading Security Boundary**: All components are strictly isolated, ensuring that transitioning from Shadow simulation to real-world live trading in the future will require explicit, separate configuration wrappers, preventing accidental real capital exposure.
