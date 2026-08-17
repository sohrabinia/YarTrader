# YARTRADER V1.0 INTELLIGENCE ARCHITECTURE REALITY MAP

## Executive Summary
This document provides a technical map of the complete YarTrader V1.0 intelligence pipeline, evaluating each component from Market Data Ingestion to Learning Updates under strict evidence-based production reality criteria.

---

## Complete Pipeline Reality Mapping

```
Market Data (MT5 Raw / Sandbox Provider)
      |
      v
Data Normalization (Tick / Candle Aggregation)
      |
      v
Feature & Multi-Timeframe Structure Extraction (8 Timeframes: 1, 4, 16, 64, 256, 1024, 4096, 16384)
      |
      v
Backtesting Engine (IntelligenceBacktestEngine)
      |
      v
Simulation Results (P&L, Drawdown, Sharpe, Equity Curve)
      |
      v
Learning Engine (MarketMemorySystem & Outcome Ledger)
      |
      v
Pattern Memory (Concept Memory / Cosine Similarity)
      |
      v
Decision Engine (DecisionIntelligenceEngine)
      |
      v
Risk Engine (PortfolioRiskService & Safety Gate)
      |
      v
Execution Intelligence (Demo / Shadow / MT5 Adapter)
      |
      v
Feedback Loop (Post-Trade Outcome Recording)
      |
      v
Learning Update (Parameter Tuning & Concept Promotion)
```

---

## Subsystem Component Reality Classification

| Pipeline Stage | Subsystem | Code Location | Runtime Reality Status | Evidence Reference |
| :--- | :--- | :--- | :--- | :--- |
| **1. Market Data** | MT5 Data Provider | `src/Data/Providers/MT5/mt5.py` | **REAL / DUAL MODE** | Native MT5 API in production; friendly sandbox mock in dev. |
| **2. Normalization** | Custom Time Engine | `src/ShadowTrading/Engine/TimeEngine.py` | **REAL** | 4^x tick aggregation building 8 canonical internal timeframes. |
| **3. Structure Extraction**| Multi-Timeframe Perception | `src/Research/Brain/multi_timeframe.py` | **REAL** | Pure price action Swing High/Low and OB/FVG extraction without lagging indicators. |
| **4. Backtesting Engine** | Intelligence Backtest Engine | `src/Application/Backtesting/engine.py` | **REAL** | Multi-asset point-in-time historical simulation with SL-first ambiguity and cost accounting. |
| **5. Learning Engine** | Outcome Ledger & Memory | `src/Learning/` | **REAL** | Post-trade outcome logging, P&L attribution, and minimum sample gates ($N \ge 5$). |
| **6. Pattern Memory** | Concept Memory System | `src/Learning/Services/` | **REAL** | Cosine similarity pattern matching against historical market structure signatures. |
| **7. Decision Engine** | Decision Intelligence Engine | `src/Decision/Intelligence/engine.py` | **REAL** | Dynamic delegation adapter unifying Signal, Strategy, Risk, and XAI reasoning traces. |
| **8. Risk Engine** | Safety Gate & Portfolio Risk | `src/Execution/Safety/safety_gate.py` | **REAL** | SRE fail-closed isolation blocking unauthorized live real-money trades. |
| **9. Execution** | Real MT5 Adapter & Shadow Engine | `src/Execution/Adapters/mt5_adapter.py` | **REAL** | Real MetaTrader5 Python C-API wrapper for order checks and submissions. |
| **10. Feedback Loop** | Outcome Recorder | `src/Learning/Services/` | **REAL** | Trades automatically record exit price and P&L feedback into memory. |
| **11. Learning Update** | Model Refinement Loop | `src/Learning/Optimization/` | **REAL** | Threshold-gated pattern weight updates based on out-of-sample win rates. |
