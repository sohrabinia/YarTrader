# TradeYar AI — Module Boundaries & Interface Contracts

This document establishes strict input/output boundaries and dependency rules to prevent spaghetti coupling and preserve 100% read-only integrity.

## 1. Boundary Rules Matrix

| Module | Allowed Inputs | Allowed Outputs | Allowed Dependencies | Forbidden Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **Market Data** | MT5 Terminal API | Raw candles stream | MT5 client package | Brain memory, Order routing |
| **Observation Brain** | Raw candle lists | `MarketSequence`, events | Mathematical structures | Any execution, UI, Strategy |
| **Memory System** | Event, Pattern, and Experience records | Saved files, query answers | JSON serializer, Thread locks | Live broker, Web UI, Order executors |
| **Simulation Brain** | Historical replay series | `VirtualTrade` records, excursions | Data Reality Layer | Real order APIs, live accounts |
| **Judge Brain** | Closed trades, Context evidence, Outcomes | Ratings, Confidence adjustments | Memory System | Decision making, live broker |
| **Conversation Layer (Future)** | Human query input | Query reports, read-only results | Knowledge Query Interface | Direct memory writing, Simulated order placement |

---

## 2. Forbidden Interface Connections

1. **Conversation Layer $\rightarrow$ Memory Write:** Conversation interfaces must NEVER have access to write/update memory layers directly. All memory modifications must go through the independent Judge Brain $\rightarrow$ Learning Update chain.
2. **Analysis Brain $\rightarrow$ Live Broker / Order Execution:** The Analysis Brain has absolutely no pathways or imports to call live trade placement APIs.
3. **Simulation $\rightarrow$ Live Broker:** Any virtual replay must be simulated over simulated data files or read-only cached candle data streams; no live broker feeds can be manipulated or used for execution feedback.
