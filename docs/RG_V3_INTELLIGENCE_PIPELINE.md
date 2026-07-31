# TRADEYAR Intelligence Pipeline

The Application Intelligence Pipeline coordinates the execution flow across Data Ingestion, Research Analysis, Strategy Evaluation, Risk Auditing, and Decision Reasoning components.

---

## 1. Pipeline Mission

The core mission of the Intelligence Pipeline is to:
* **Orchestrate Unified Execution:** Manage the data-flow transition from raw database lookups into descriptive allocation decisions.
* **Guarantee Decoupled State Management:** Encapsulate execution parameters inside `PipelineContext` and track processing results cleanly inside `PipelineResult`.
* **Prevent Business logic leakages:** Standardize the orchestrator so that zero concrete strategy, risk, or execution calculations are compiled inside the application layer.

---

## 2. Dependencies and Direction

The Pipeline layer depends strictly on lower abstractions:
* **Dependencies:** Core, Data, Research, Strategy, Risk, and Decision package interfaces.
* **Separation:** It operates merely as a coordinator, injecting standard service adapters and calling their interfaces sequentially. It contains zero trading rules or direct broker connectors.
