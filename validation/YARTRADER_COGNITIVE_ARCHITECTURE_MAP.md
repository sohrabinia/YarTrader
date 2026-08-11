# YARTRADER COGNITIVE ARCHITECTURE MAP

This document illustrates the complete and verified information, knowledge, and execution flow of YarTrader's Cognitive Market Intelligence lifecycle.

---

## 1. FLOW CHART

```text
                 Market Data (Raw Price Action)
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │               MARKET OBSERVER               │  [CURRENTLY ACTIVE]
        │                LEARNING BRAIN               │
        └──────────────────────┬──────────────────────┘
                               │
                      Pattern Candidates
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │            RESEARCH / CANDIDATE             │  [CURRENTLY ACTIVE]
        │                INTELLIGENCE                 │
        └──────────────────────┬──────────────────────┘
                               │
                        Quality Control
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │               VALIDATION GATE               │  [CURRENTLY ACTIVE]
        └──────────────────────┬──────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   [BACKTEST]               [DEMO]                 [SHADOW]
  Historical Replay     Simulated Sequential    Live-Market Ticks
  Chronological Data     Order Lifecycle         Virtual Capital
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │            CANDIDATE SELECTION              │  [CURRENTLY ACTIVE]
        │               & GOVERNANCE                  │
        └──────────────────────┬──────────────────────┘
                               │
                        Approved Models
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │                  RISK GATE                  │  [CURRENTLY ACTIVE]
        │              Max 2% Daily Loss              │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │             EXECUTION BOUNDARY              │  [SIMULATION ONLY]
        │            Authorized Broker ONLY           │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │                SIGNAL / LIVE                │  [FUTURE / NOT ENABLED]
        │             Real Capital Trades             │
        └─────────────────────────────────────────────┘
```

---

## 2. STATE CLASSIFICATIONS
* **Market Observer (Active):** Reads tick buffers and establishes structural maps and liquidity zones dynamically from clean price-action changes without technical indicators.
* **Validation Stage Gates (Active):** Separates backtest replays, demo sequential lifecycle tracking, and shadow paper accounts cleanly.
* **Live Execution (Safely Isolated):** Completely isolated from cognitive observation to prevent accidental broker execution or live capital leaks.
