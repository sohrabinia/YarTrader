# YarTrader V1.1 Runtime Intelligence Pipeline Audit

## Executed Pipeline Trace

```
Market Data
    ↓ [src.Data.Providers.MT5.mt5.MT5DataProvider]
Market Analysis
    ↓ [src.Research.MarketAnalysis.Services.services.MarketAnalysisService]
Trading Style Selector
    ↓ [src.Research.Brain.multi_timeframe]
Timeframe Selection
    ↓ [src.Research.Brain.multi_timeframe.MultiTimeframePerception]
Strategy Decision
    ↓ [src.Strategy.Evaluation.evaluation.StrategyEvaluationService]
Risk / Reward Engine
    ↓ [src.Decision.Intelligence.engine.DecisionEngine]
Trade Approval Gate
    ↓ [src.Decision.Intelligence.engine.DecisionEngine]
Trade Simulation
    ↓ [src.Application.Backtesting.engine.IntelligenceBacktestEngine]
Trade Result
    ↓ [src.ShadowTrading.Services.TradeEvaluator.TradeEvaluator]
Experience Memory Update
    ↓ [src.Research.Brain.memory.MarketMemorySystem.add_experience]
```

## Runtime Component Audit Table

| Component | Location | Runtime Usage | Evidence |
| :--- | :--- | :--- | :--- |
| **Market Data** | `src/Data/Providers/MT5/mt5.py` | Ingests real candles (XAUUSD, EURUSD, GBPUSD, BTCUSD, ETHUSD) across M1-D1 | Verified active tick/candle stream & historical bar ingestion |
| **Market Analysis** | `src/Research/MarketAnalysis/Services/services.py` | Extracts trend, volatility, momentum, ATR, and regime structure | Generated `MarketObservation` & `MarketInsight` datastructures |
| **Trading Style Selector** | `src/Research/Brain/multi_timeframe.py` | Dynamic style selection (FAST_SCALPING, SCALPING, INTRADAY, SWING) based on regime & ATR | Style parameters mapped directly into signal generation & SL/TP bounds |
| **Timeframe Selection** | `src/Research/Brain/multi_timeframe.py` | Reconciles hierarchical timeframes (M1, M5, M15, H1, H4, D1) | Multi-timeframe trend alignment verified across 6 timeframes |
| **Strategy Decision** | `src/Strategy/Evaluation/evaluation.py` | Scores strategy candidates (Mean Reversion, Breakout, Trend Following) | Candidate evaluation scores & trade signal generation verified |
| **Risk / Reward Engine** | `src/Decision/Intelligence/engine.py` | Calculates dynamic SL/TP, R:R ratio, Spread impact, and Expected Value (EV) | Active R:R calculation (`EV = (WinProb * Reward) - (LossProb * Risk)`) |
| **Trade Approval Gate** | `src/Decision/Intelligence/engine.py` | Enforces fail-closed gates (WinProb >= 50%, R:R >= 1.5, EV > 0, Max Spread) | Direct REJECT / APPROVE verdicts emitted with explicit reason codes |
| **Trade Simulation** | `src/Application/Backtesting/engine.py` | Simulates tick execution, spread, commission, and slippage | Point-in-time trade simulation with exact PnL and equity curve |
| **Trade Result** | `src/ShadowTrading/Services/TradeEvaluator.py` | Independent Judge Brain evaluates trade execution quality and outcome | Structured evaluation with quality metrics and lessons learned |
| **Experience Memory Update** | `src/Research/Brain/memory.py` | Stores trade experience, adjusts pattern weights dynamically | Dynamic confidence score updates (+weight on win, -weight on loss) |

## Runtime Execution Verification
- **Audit Execution Timestamp:** 2026-08-24 15:41:42 UTC
- **Active Decision ID:** rep-5e9ef24a-a084-4eaa-97cc-2910de22a534
- **Pipeline Execution Status:** VERIFIED & FULLY OPERATIONAL (10/10 Stages Active in Runtime)
