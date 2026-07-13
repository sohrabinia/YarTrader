# 04. Intelligence Pipeline

## 1. Pipeline Stages overview

```text
External Ingest (MT5 / Calendar) ──> Gateway ──> Validator ──> Normalizer
                                                                    │
                                                                    ▼
Research (Insights & Patterns) <── Agent Ecosystem <── Normal Market Data
      │
      ▼
Strategy Score ──> Risk Audit Limits ──> Decision Synthesis ──> Learning Feed
```

---

## 2. Stages Inputs, Outputs, and Artifacts

### A. Data Ingestion & Gateway
*   **Input**: `ExternalDataRequest`
*   **Output**: `ExternalDataResponse`
*   **Artifacts**: Chronological raw provider rates and calendar events.

### B. Validation & Normalization
*   **Input**: `ExternalDataResponse`
*   **Output**: `NormalizedMarketRecord` list and `DataIntegrityReport`.
*   **Artifacts**: Standardized candle files, data quality scores.

### C. Research Intelligence
*   **Input**: `ResearchRequest`
*   **Output**: `ResearchResult`
*   **Artifacts**: `MarketInsight` and `PatternObservation` lists.

### D. Strategy Suitability Scoring
*   **Input**: `StrategyCandidate`
*   **Output**: `StrategyEvaluation`
*   **Artifacts**: `StrategyScore` across multiple criteria (stability, complexity, risk).

### E. Risk Audit Bounds
*   **Input**: Proposed asset weights dict, `RiskProfile`.
*   **Output**: `RiskAssessment`
*   **Artifacts**: Approved status, expected volatility, drawdown limits.

### F. Decision Synthesis & Conflict Resolution
*   **Input**: `DecisionIntelligenceContext`
*   **Output**: `DecisionIntelligenceReport`
*   **Artifacts**: State reports, conflict resolutions, confidence scoring, audit logs.

### G. Feedback & Parameters Optimization
*   **Input**: `LearningFeedback`
*   **Output**: Actionable parameter recommendations list.
*   **Artifacts**: History of performance metrics.

---

## 3. Cross References
*   [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
*   [06_DATA_LAYER.md](06_DATA_LAYER.md)
*   [08_DECISION_ENGINE.md](08_DECISION_ENGINE.md)
*   [09_LEARNING_SYSTEM.md](09_LEARNING_SYSTEM.md)
