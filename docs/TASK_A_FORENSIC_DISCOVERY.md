# YARTRADER TASK A — FORENSIC DISCOVERY REPORT
**Date:** 2026-08-15
**Auditor:** YarTrader SRE & Forensic Intelligence Team
**Subject:** Discovery of Backtesting Engines, Memory Layers, Data Connectors, Safety Gates & Persistence Boundaries

---

## 1. Executive Summary
A forensic discovery audit was conducted across YarTrader's intelligence pipeline, backtesting engine, memory layers, and safety boundaries to map all components involved in historical processing and learning admission.

---

## 2. Key Subsystem Inventory

| Subsystem | Primary Module / Path | Key Class / Interface | Responsibility | Status |
|---|---|---|---|---|
| **Backtesting Engine** | `src/Application/Backtesting/engine.py` | `IntelligenceBacktestEngine` | Runs chronological interval loops over scenarios. | **ACTIVE / HARDENED** |
| **Data Connector** | `src/Data/connector.py` | `ExternalDataPipelineConnector` | Bridges raw market providers (`MT5DataProvider`) with agent contexts. | **ACTIVE** |
| **Agent Context** | `src/Application/Agents/context.py` | `AgentContextBuilder` | Constructs enriched point-in-time contexts for agents. | **ACTIVE** |
| **Learning Memory** | `src/Research/Brain/memory.py` | `MarketMemorySystem` | 4-layer memory (Event -> Experience -> Pattern -> Concept). | **ACTIVE** |
| **Safety Gate** | `src/Execution/Safety/safety_gate.py` | `MetaTraderSafetyGate` | Fail-closed gate separating MT5 DEMO (`52961173`) and MT4 LIVE (`143056202`). | **ACTIVE / HARD-BLOCKED** |
| **Real Broker Adapter** | `src/Execution/Adapters/mt5_adapter.py` | `RealMT5BrokerAdapter` | Concrete adapter implementing native `MetaTrader5` C-API. | **ACTIVE** |
| **UI Locales (933R)** | `trader-terminal/public/locales/fa.json` | `average_rr: "933.1R"` | Static visual example label in frontend. | **ISOLATED / NOT IN MEMORY** |

---

## 3. Data Isolation Invariants
- **Backtest Execution:** Operates strictly in memory (`BacktestResult`) without calling `RealMT5BrokerAdapter.send_order_to_broker()`.
- **Live Trading:** Hard-blocked (`LIVE_TRADING_ENABLED = False`).
- **Data Provenance:** Historical candle filtering enforces `record.timestamp <= current_time` to prevent future bar leakage.
