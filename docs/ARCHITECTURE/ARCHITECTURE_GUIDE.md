# TRADEYAR_AI Architecture Guide

## 1. Clean Architecture Design
The platform implements a highly disciplined Clean Architecture model where data flows in a strict unidirectional path:

```
Ingestion (Adapters) → Feature Extraction → Technical Patterns → Research Insights
                                                                       ↓
Final Analytics Report ← Health Verification ← Decision Synthesis ← Risk Audit Bounds
```

### Domain Boundaries
1. **Core / Entities**: Represents independent entity definitions (e.g. `MarketDataPoint`).
2. **Business Rules**: Implements calculators and scoring rules (e.g. `StrategyEvaluator`, `RiskAnalyzer`).
3. **Interface Adapters**: Adapts raw rates or MT5 structures into CandleRecords (`MT5DataMapper`).
4. **Platform Orchestrators**: Coordinates live tracking sessions or backtest chronological slices (`ShadowModeEngine`, `IntelligencePipeline`).

---

## 2. SOLID Design Principles Auditing
* **Single Responsibility (SRP)**: Classes are highly cohesive with one clear responsibility.
* **Open/Closed (OCP)**: Interfaces enable decorators (`FeatureExtractionResearchEngine`) to wrap engines without mutating source code.
* **Dependency Inversion (DIP)**: Subsystems interact exclusively through abstract dependency contracts rather than low-level file writers.
