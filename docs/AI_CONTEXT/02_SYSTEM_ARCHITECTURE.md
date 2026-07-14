# 02. System Architecture

## 1. Complete Structural Data Flow Diagram

```text
External Data Ingestion (MT5, Calendar, News)
        │
        ▼
   Data Gateway (ExternalDataGateway)
        │
        ▼
Validation Layer (DataQualityAnalyzer)
        │
        ▼
Normalization Pipeline (DataNormalizer)
        │
        ▼
  Research Engine (ResearchProcessor)
        │
        ▼
Strategy Assessment (StrategyEvaluator)
        │
        ▼
 Risk Verification (RiskAnalyzer)
        │
        ▼
Decision Layer (DecisionEngine)
        │
        ▼
Learning Optimization (LearningProcessor)
        │
        ▼
Compliance Audit (ComplianceAuditor)
        │
        ▼
Operational Suites (Backtesting, Demo, Shadow Mode)
```

---

## 2. Layer Boundaries & Core Responsibilities

The system is organized into clean, isolated subsystems matching the APES-FIN architecture:

### A. Data Layer (`src/Data/`)
Manages raw ingestion, health gateways, schema validation, format normalization, and reliability score trackers. It contains absolutely zero trading or execution commands.

### B. Core Layer (`src/Core/`)
Provides general, layer-independent entities (e.g. `Asset`, `MarketData`) and general interfaces.

### C. Application Layer (`src/Application/`)
Orchestrates pipelines (`IntelligencePipeline`), coordinates multi-agent supervisor loops, runs system audits, and deploys telemetry services.

### D. Decision Intelligence Core (`src/Decision/`)
Synthesizes research, strategy, and risk assessments into structured decision report contexts.

### E. Operational Subsystems (`src/Application/Demo/`, `Shadow/`, `Backtesting/`)
Provides synthetic/historical scenarios execution, live-rates read-only shadow tracking, and sliding metrics diagnostics.

---

## 3. Dependency Directions

Dependencies are strictly unidirectional:

$$\text{Data Ingestion} \rightarrow \text{Validation} \rightarrow \text{Normalization} \rightarrow \text{Research} \rightarrow \text{Decision} \rightarrow \text{Explainability}$$

Lower infrastructural elements are completely blocked from depending on upper decision layers. These boundaries are statically checked by Phase 25 architecture auditors.

---

## 4. Cross References
*   [04_INTELLIGENCE_PIPELINE.md](04_INTELLIGENCE_PIPELINE.md)
*   [06_DATA_LAYER.md](06_DATA_LAYER.md)
