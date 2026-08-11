# YARTRADER EXECUTION ARCHITECTURE AUDIT

This document establishes the verified execution and routing architecture of YarTrader, ensuring complete separation across all environments.

---

## 1. EXECUTION FLOW
The execution routing of YarTrader is structured as:

```text
                        YarTrader AI
                             │
            ┌────────────────┼────────────────┐
            │                │                │
         Backtest       Paper / Shadow     Execution
            │                │                │
            │                │        ┌───────┴───────┐
            │                │        │               │
            │                │       MT4             MT5
            │                │        │               │
            │                │      LIVE            DEMO
            │                │        │               │
            │                │   Real Broker       Demo Broker
```

---

## 2. ENVIRONMENTAL SEPARATION & ISOLATION
* **Backtest (Pass):** Strictly runs historical chronological simulation over data retrieved via the `ExternalDataPipelineConnector`. No connection to broker execution or live capital is ever possible.
* **Paper / Shadow (Pass):** Streams real-time ticks to evaluate pattern similarity, structural nodes, and order block boundaries, but remains entirely virtual. It tracks virtual P/L via `PredictiveShadowEngine` and `VirtualAccount` with **zero** broker order submissions.
* **MT5 Demo (Pass):** Configured as a safe practice account. Explicit checks ensure that Demo orders only route to demo servers, failing closed on any credential or environment mismatch.
* **MT4 Live (Pass):** The live broker routing is safely isolated and disabled by default (`LIVE_EXECUTION = DISABLED`) to guarantee capital protection.
