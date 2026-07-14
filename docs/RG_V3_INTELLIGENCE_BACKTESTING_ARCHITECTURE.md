# RG_V3 Intelligence Backtesting Framework

This document describes the architectural design and unmodifiable evaluation flow of the **Non-Trading Historical Backtesting Framework (Phase 33)** of the RG_V3 Platform.

---

## 1. Architectural Overview & Chronological Ingestion

The Non-Trading Intelligence Backtesting Framework enables developers and operators to validate the long-term analytical quality of the platform's research, strategy scoring, and risk checking.

It evaluates these components iteratively across historical chronological data slices without introducing any trading commands or broker connections.

### Operational Backtesting Flow

```
Backtest Scenario Configuration (Symbol, Timeframe, Date Bounds)
        │
        ▼
   Iterative Chronological Loop (e.g. 120-minute interval steps)
        │
        ▼
   Data Ingestion via Gateway (SimulationDataProvider / MT5 Provider)
        │
        ▼
   Multi-Agent Ingestion & Enrichment (Research -> Strategy -> Risk -> Validation)
        │
        ▼
   Decision Synthesis Report (DecisionEngine.evaluate_intelligence_context)
        │
        ▼
   Historical Caching & Evaluation (IntelligenceMetricsEvaluator)
        │
        ▼
   Composite Intelligence Scores & Compliance Audit Outputs
```

---

## 2. Core Service Components

### A. Backtest Engine (`src/Application/Backtesting/engine.py`)
*   **IntelligenceBacktestEngine**: Runs the chronological loop, resolves and retrieves historical records, coordinates supervisor loops, compiles decision reports, and builds performance metrics history.
*   **BacktestScenario / BacktestResult**: Standardized, immutable data models representing configured ranges and finished run logs.

### B. Metrics Evaluator (`IntelligenceMetricsEvaluator`)
Calculates mathematical performance parameters across historical runs:
*   **Decision Consistency**: Measures confidence stability and variance across reports.
*   **Research Accuracy**: Assesses the reliability of generated research insights and trend observations.
*   **Overall Intelligence Score**: Computes a weighted overall rating of the platform's reasoning capabilities over time.

---

## 3. Strict Safety & non-Trading Boundaries

Every component is guarded by:
1.  **Passive Role Adherence**: Absolute zero BUY/SELL instructions, order triggers, or portfolio sizing modifiers.
2.  **String Payload Scanning**: Scans scenario configs and parameters to reject raw execution keywords instantly.
3.  **Staging / Backtest Verdict**: Issues the definitive 'STATUS: READY FOR BACKTEST' with zero stumbles or blockers.
