# TRADEYAR Intelligence Demo Scenario Platform — Architecture & Specifications

## Overview
The **Intelligence Demo Scenario Platform** (Phase 34) provides a reusable, trace-complete, and non-trading demonstration environment. It allows developer and auditor simulation of the entire end-to-end `TRADEYAR_AI` pipeline, tracing the processing flow across all architectural layers.

Crucially, the Demo Scenario Platform strictly adheres to the **APES-FIN** Clean Architecture standard and is bound to **Simulation-Only Mode**, guaranteeing absolute zero execution leakage or active broker/order management hooks.

---

## 1. Pipeline Architecture & Execution Flow
The pipeline operates as a strictly unidirectional directed acyclic graph (DAG) to maintain domain isolation and flow clarity:

```
Historical Data Ingestion (Input)
        ↓
Feature Extraction (Observations & Indicators)
        ↓
Research Intelligence (Observations, Patterns, Insights)
        ↓
Strategy Intelligence (Scoring & Evaluations)
        ↓
Risk Intelligence (Limits & Exposure Verification)
        ↓
Decision Intelligence (Advanced Synthesis & Conflict Resolution)
        ↓
Validation Layer (Compliance Checker & Integrity Auditor)
        ↓
Explainable Intelligence Report (Text Summary & Trace Pathway)
```

### Stage Explanations
1. **Input Ingestion**: Historical or synthetic OHLCV `MarketDataPoint` streams are loaded via a custom `IMarketDataProvider` adapter.
2. **Feature Extraction**: Standard technical features (volatility, trend, range expansions) are calculated via the `FeaturePipeline`.
3. **Research Intelligence**: Features are mapped into technical pattern observations and qualitative market insights.
4. **Strategy Intelligence**: Multiple candidate strategies are compared and evaluated contextually, assigning overall scores.
5. **Risk Intelligence**: Multi-factor parameters stress-test proposed single-asset exposure limits against active Risk Profiles.
6. **Decision Intelligence**: Resolves layer contradictions (e.g. conflict resolver) to emit an analytical state (`Approved`, `Rejected`, `ReviewRequired`, etc.).
7. **Validation Layer**: Scans the execution context and verifies zero broker connections or trading signals.
8. **Explainable Report**: Emits the finalized `ExplainableIntelligenceReport` and trace-timeline of execution durations.

---

## 2. Reusable Scenario Library
The library implements five distinct, reproducible demonstration scenarios under `src/Application/Demo/scenarios.py`:

| Scenario Name | Key Characteristics | Expected Core Outputs |
| :--- | :--- | :--- |
| **Trend Continuation** | Healthy upward price drift, high volume, low volatility. | `APPROVED` state, high confidence, full exposure. |
| **Trend Reversal** | Sudden sharp drop in price on rising volume. | `REJECTED` or `REVIEW_REQUIRED` state. |
| **High Volatility** | Extreme price range oscillations exceeding standard bounds. | `REJECTED` state, low exposure override. |
| **Low Liquidity** | Flat price movement with near-zero volumes. | `REVIEW_REQUIRED` or `INSUFFICIENT_DATA` state. |
| **Conflicting Signals** | Upward drift but falling volume and weak strategy scores. | `REVIEW_REQUIRED` state via conflict resolution. |

---

## 3. Agent Participation & Explainability
Multi-Agent components actively participate and record their logical rationales within each execution trace:
* **ResearchAgent**: Translates extracted technical indicator matrices into technical double-bottom patterns and trend classifiers.
* **StrategyAnalystAgent**: Assigns overall scores to concept strategies based on historical and research alignment.
* **RiskAgent**: Stress-tests portfolio exposure, ensuring allocations fit strict volatility-scaled constraints.
* **ValidationAgent**: Performs independent compliance auditing, verifying strict domain-level isolation.
* **LearningAgent**: Continuously ingests outcomes to log stability suggested improvements.

Explanations are compiled into standard trace pathways (e.g., Ingestion -> Research -> Decision) using `DecisionTraceEngine` and formatted into high-grade layouts via `EvidenceVisualizationModels`.

---

## 4. Platform Limitations & Safety Guidelines
1. **Simulation-Only Bound**: The system cannot place actual trades, interface with live brokers, or accept real cash balances.
2. **Deterministic Inputs**: Market scenarios utilize deterministic inputs to guarantee exact repeatability.
3. **No Retraining**: Learning optimizations provide mathematical suggestion logs but do not retraining active ML weights in real-time.

---

## 5. Architectural Recommendations
* **Expanded Stress Scenarios**: Introduce geopolitical or macroeconomic calendar event markers to expand Risk scenario triggers.
* **Asynchronous Tracing**: Implement parallel telemetry recording in the dashboard services to monitor non-blocking performance statistics.
