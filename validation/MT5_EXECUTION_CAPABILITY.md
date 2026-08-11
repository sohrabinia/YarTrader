# YARTRADER MT5 EXECUTION CAPABILITY REPORT

This document audits the physical ability of the YarTrader platform to execute orders on MetaTrader 5 (MT5).

---

## 1. INTENDED VS. ACTUAL CAPABILITY
* **Intended Capability:** Demands an end-to-end broker demo order execution pipeline (`order_send` / `order_check`).
* **Actual Capability:** Strictly **read-only / passive non-trading** (Zero execution capability).
* **Security & Regulatory Invariants:** Standard SRE Abstract Syntax Tree (AST) scanners (implemented under `test_research_runtime.py` and `test_virtual_capital_safety.py`) scan the active codebase to verify that forbidden keys like `order_send`, `place_order`, `send_transaction`, and `order_modify` are never defined or called. This is mandated to conform strictly to APES-FIN passive advisory guidelines and prevent real-money leaks.

---

## 2. SHADOW VS. DEMO EXECUTION
* **Shadow Trading:** Executes entirely virtually inside the isolated `PredictiveShadowEngine` and `VirtualAccount` with **zero** MT5 order placements.
* **Demo / Live Broker Execution:** Non-existent in the active codebase to enforce regulatory compliance.

---

## 3. FINAL CAPABILITY STATUS
* **Status:** **BLOCKED — REAL MT5 DEMO EXECUTION NOT VERIFIED** (Because the active codebase is governed by AST compliance checkers that explicitly ban `order_send` / `order_check` commands).
