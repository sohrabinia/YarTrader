# YARTRADER COGNITIVE ARCHITECTURE REALITY AUDIT

This document establishes the verified reality of YarTrader's Cognitive Market Intelligence and Trading Engine architecture as verified by direct SRE inspection of source code and execution paths.

---

## 1. ARCHITECTURE REALITY TABLE

| Component | Intended Role | Actual Role | Direct Execution Access | Validation Stage | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Cognitive Brain** | Research / Behaviour Learning | Evaluates market structure nodes, liquidity maps, and pattern similarities recursively. | **NO** | Research | **PASS** |
| **Backtest** | Historical chronological validation | Chronological historical agent pipeline simulation. | **NO** | Backtest | **PASS** |
| **Demo** | Sequential simulation / Paper Trading | Tracks virtual account parameters, slippage, and SL/TP. | **NO** | Demo | **PASS** |
| **Shadow** | Real-time live-market paper execution | Tracks real-time ticks, SL/TP execution simulation without real money. | **NO** | Shadow | **PASS** |
| **Live** | Real broker execution | Safe routing layer with strict isolation gates. | **YES** | Live | **DISABLED** |
| **Risk Engine** | Risk governance | Enforces daily max loss and 2% safety boundaries server-side. | **Controlled** | All | **PASS** |
| **Candidate Governance** | Candidate promotion | Managed state transitions from hypothesis to qualified. | **Controlled** | All | **PASS** |

---

## 2. ARCHITECTURAL ISOLATION GUARANTEES
* **Independent Brain Output:** The Cognitive Brain does not contain any direct references or imports linking it to broker order placements or position managers. It outputs versioned, analytical PatternCandidates and structure maps.
* **Separated Validation stage Reports:** SRE report persistence ensures that Backtest outcomes, Demo simulation runs, and Shadow trading logs are saved to independent files under `runtime_logs/` (e.g. `backtest_history.json`, `paper_account.json`, `shadow_trades.json`), preventing cross-stage state contamination.
* **Fail-Closed Live Safety:** Live broker execution is completely deactivated and isolated under non-Windows environments, returning mock synthetic fallbacks only where authorized for DevOps tests.
