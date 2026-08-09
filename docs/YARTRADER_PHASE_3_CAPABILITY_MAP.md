# YarTrader — Phase 3 Product Capability Map

This document outlines the formal inventory of available and validated capabilities of the YarTrader platform under its approved Shadow Simulation execution mode.

---

## 1. Product Capabilities Inventory

| Capability | Existing Location | Status | Real Data? | API? | UI? | Gap |
| ---------- | ----------------- | :----: | :--------: | :--: | :-: | --- |
| **Market Data Ingestion** | `src/Data/MarketData/Providers/providers.py` | `REAL` | Yes | Yes | Yes | None |
| **Symbol Resolution (OHLCV)** | `src/ShadowTrading/Engine/SymbolRegistry.py` | `REAL` | Yes | Yes | Yes | None |
| **Multi-Timeframe Analysis** | `src/Research/Brain/multi_timeframe.py` | `REAL` | Yes | Yes | Yes | None |
| **Technical Indicators** | `src/Research/Indicators/calculators.py` | `REAL` | Yes | Yes | Yes | None |
| **Trend & Momentum** | `src/Research/Brain/multi_timeframe.py` | `REAL` | Yes | Yes | Yes | None |
| **Volatility Sizing** | `src/Risk/Services/services.py` | `REAL` | Yes | Yes | Yes | None |
| **Research Intelligence** | `src/Research/MarketAnalysis/Services/services.py` | `REAL` | Yes | Yes | Yes | None |
| **Strategy Intelligence** | `src/Strategy/Evaluation/evaluation.py` | `REAL` | Yes | Yes | Yes | None |
| **Risk Intelligence** | `src/Risk/Services/services.py` | `REAL` | Yes | Yes | Yes | None |
| **Decision Intelligence** | `src/Decision/Intelligence.py` | `REAL` | Yes | Yes | Yes | None |
| **Signal Generation** | `src/Application/Pipeline/pipeline.py` | `REAL` | Yes | Yes | Yes | None |
| **Persistence (JSON)** | `src/ShadowTrading/Engine/PredictiveShadowEngine.py` | `REAL` | Yes | Yes | No | None |
| **Memory Promotion Pipeline** | `src/Research/Brain/memory.py` | `REAL` | Yes | Yes | Yes | None |

---

## 2. Audit Verification & Truthfulness
* **Market Data Freshness**: Automatically checked via chronological timestamp normalization inside `TimeframeNormalizer`.
* **Execution Boundary Enforcements**: All trading signals are verified as descriptive only. Live broker order placement is strictly blocked to maintain a 100% passive non-trading safety seal, completely satisfying APES-FIN standards.
