# TRADEYAR Intelligence Pipeline Implementation Foundation

This document details the architecture, execution flow, dependency injection (DI) structure, and extension points of the first working autonomous intelligence pipeline for the **TRADEYAR Autonomous Financial Intelligence Platform**.

---

## 1. Pipeline Architecture

The **Intelligence Pipeline** is the end-to-end orchestrator of the APES-FIN platform. It acts as a unidirectional coordinator, ensuring data flows strictly in one direction from ingestion down to learning feedback, while keeping the modules loosely coupled and decoupled from execution/state logic.

```
       [ PipelineContext ] (Inputs)
                │
                ▼
        ┌──────────────┐
        │ Ingest/Data  │ ◄── IMarketDataProvider
        └──────┬───────┘
               │ (MarketDataResponse)
               ▼
        ┌──────────────┐
        │   Research   │ ◄── IResearchEngine
        └──────┬───────┘
               │ (ResearchResult)
               ▼
        ┌──────────────┐
        │   Strategy   │ ◄── IStrategyEvaluator
        └──────┬───────┘
               │ (StrategyEvaluation)
               ▼
        ┌──────────────┐
        │     Risk     │ ◄── IRiskEngine
        └──────┬───────┘
               │ (RiskAssessment)
               ▼
        ┌──────────────┐
        │   Decision   │ ◄── IDecisionEngine
        └──────┬───────┘
               │ (DecisionResult)
               ▼
        ┌──────────────┐
        │   Learning   │ ◄── ILearningEngine
        └──────────────┘
               │ (LearningFeedback)
               ▼
       [ PipelineResult ] (Outputs)
```

### Key Design Goals:
* **Interface-Based Coupling:** No concrete implementations of lower layers are imported directly. The orchestrator references abstract interfaces (e.g., `IMarketDataProvider`, `IResearchEngine`, `IStrategyEvaluator`, `IRiskEngine`, `IDecisionEngine`, `ILearningEngine`).
* **Dependency Injection (DI):** Implementations are supplied as parameters at construction time, facilitating flexible configuration, testing, and mocking.
* **Separation of Concerns:** Zero concrete business logic or trading rules are written inside the pipeline. It merely coordinates the sequential output-to-input propagation.
* **Safety First (Simulation-Only Mode):** The orchestrator strictly validates the configuration and only permits simulation mode. It prohibits any real trading, real money operations, or direct live broker connections.

---

## 2. Execution Flow

The sequence of the pipeline execution is strictly unidirectional:

1. **Pipeline Context Initialization:** A `PipelineContext` is initialized, holding parameters like `StartTime`, `Asset`, `Timeframe`, `TargetRiskProfile`, and arbitrary `Metadata`.
2. **Safety Verification:** The pipeline validates that `SimulationMode` is enabled. If not, it throws a `ValueError` immediately, stopping execution.
3. **Data Acquisition Layer:** The pipeline queries historical market data from the injected `IMarketDataProvider`.
4. **Research Layer:** The pipeline takes the obtained `MarketDataResponse` and routes it to the `IResearchEngine` to compile research observations and qualitative indicators.
5. **Strategy Evaluation Layer:** Based on the research findings, a passive `StrategyCandidate` is constructed and sent to the `IStrategyEvaluator` for comparative scoring.
6. **Risk Assessment Layer:** The proposed scoring profile is evaluated by `IRiskEngine` against safety rules (e.g., leverage limits, single-asset allocation limits).
7. **Decision Layer:** The `IDecisionEngine` synthesizes the strategy weights and risk assessment status to formulate a final `DecisionResult`.
8. **Learning Layer Feedback Loop:** The decision outcome is compiled alongside an actual performance outcome metric and routed to the `ILearningEngine` to update mathematical optimization parameter traces.
9. **Pipeline Result compilation:** The final `PipelineResult` aggregates all multi-layer logs and is returned cleanly.

---

## 3. Extension Points

The `IntelligencePipeline` foundation provides modular extension points for future development:

* **Injected Adapters:** Any new provider or engine can be seamlessly plugged in by implementing the respective interface contract (e.g., hooking up a new exchange-data provider or an alternative mathematical risk model).
* **Configurable Parameterizations:** `PipelineConfig` supports customizable lookback windows, default outcome parameters, and arbitrary custom settings via the `CustomSettings` dictionary.
* **Mathematical Optimization suggestors:** The `ILearningEngine` tracks mathematical feedback traces, enabling external layers to request optimal parameter recommendations without invoking machine learning models.
