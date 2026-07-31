# TRADEYAR Shadow Mode / Live Intelligence Platform (Read-Only) Specification

## Overview
This specification details the design, architecture, metrics evaluation, and security validations for the **TRADEYAR_AI Shadow Mode Platform** (Phase 36).

Shadow Mode enables continuous, read-only validation of the complete TRADEYAR_AI multi-agent intelligence pipeline using real-time rates without any live broker or execution risk.

---

## 1. Subsystem Architecture & Execution Flow
Shadow Mode executes the advanced multi-factor unidirectional pipeline inside an active tick observation loop:

```
                  Real-Time MT5 Data Ingest
                             ↓
                 Market Indicator Extraction
                             ↓
                  Multi-Agent Orchestration
                             ↓
              Advanced Decision Synthesis (Report)
                             ↓
                 Compliance & Safety Audit
                             ↓
                 Sliding Telemetry Aggregate
```

### Components
* **ShadowModeEngine**: Manages session lifecycles, schedules execution ticks, coordinates the underlying `IntelligencePipeline`, and structures performance diagnostics.
* **ShadowMetricsEvaluator**: Evaluates real-time decision quality, latency averages, and mathematical decision consistency.
* **MetaTrader5Provider**: Connects to the MT5 terminal and maps raw tick rates to standard `CandleRecord` representations.

---

## 2. Sliding Indicator Calculations
To audit real-time consistency without trading exposure, the evaluator computes sliding snapshots on:
- **Decision Consistency**: Standard deviation-based tracking of the confidence scores.
- **Average Quality**: The decision quality scores determined by the `DecisionQualityEvaluator`.
- **Pipeline Latency**: Precise end-to-end execution times (in ms).
- **Alert Ingestion**: Telemetry alert counts raised during low confidence spikes (< 60%).

---

## 3. Strict Non-Trading & Domain Separation Safeguards
To comply with standard APES-FIN clean guidelines, the platform enforces:
* **Simulation-Only Bound**: The advanced pipeline config remains strictly bound to `SimulationMode = True`.
* **Zero Leakage Scanner**: An active regex keyword detector scans session memory and blocks any execution triggers (`order_placement`, `execute_order`).
* **Passive Analytics**: State classifications (`Approved`, `Rejected`) only represent target analytical states; no actions or order routing are performed.
