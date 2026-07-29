# TradeYar AI — Architecture Current State Audit

This document reviews the actual implementation, responsibilities, dependencies, and risks of the modules currently composing TradeYar AI as of the Architecture Stabilization Gate.

## 1. Current Components and Responsibilities

### 1.1 Market Data Layer
- **Responsibility:** Establish read-only connection to MetaTrader 5 (MT5), retrieve raw historical and streaming candle bars, convert formats, and provide health/connection diagnostics.
- **Strict Constraint:** Decoupled from any active trading or order modification APIs. Safe fallback mechanisms are provided for non-Windows and non-desktop testing systems.

### 1.2 Data Reality Layer (Trading Reality)
- **Responsibility:** Simulates execution frictions including volatility-based dynamic bid/ask spreads, Gaussian slippage distributions, commissions, and execution delay models.
- **Reasoning:** Keeps analysis objective by decoupling pure price observation from the execution costs environment.

### 1.3 Newborn Market Discovery Brain
- **Responsibility:** Watches raw price action, processes chronological events, groups consecutive directional candles, and computes scale-invariant sequence footprints.
- **Anti-Pattern Protection:** Contains no technical indicators (RSI, MACD, SMAs) in its decision-making core.

### 1.4 Memory System
- **Event Memory:** Raw observed sequences of price movements and chronological changes.
- **Pattern Memory:** Recurrent structures indexed and compared via cosine/Jaccard similarity signatures.
- **Experience Memory:** Episodic context logging Situation, simulated Decision, final simulated Outcome, and Lesson learned.

### 1.5 Simulation / Shadow Trading Brain
- **Responsibility:** Replays market events, executes simulated virtual orders (BUY, SELL, WAIT) internally, and tracks Adverse Excursions (MAM) and Favorable Excursions (MFM).
- **Scope:** Zero live broker execution capabilities.

### 1.6 Judge Brain
- **Responsibility:** Performs post-execution independent assessments of virtual decisions versus real market outcomes, adjusting confidence parameters and detecting accidental "lucky wins".

---

## 2. Dependencies and Data Flow

```
+------------------+     +--------------------+
|  Market Data     | --> | Data Reality Layer |
|  (MT5 Read-Only) |     | (Friction Models)  |
+------------------+     +--------------------+
         |                         |
         v                         v
+------------------+     +--------------------+
| Observation      | --> | Simulation Brain   |
| Brain            |     | (Virtual Trading)  |
+------------------+     +--------------------+
         |                         |
         v                         v
+------------------+     +--------------------+
| Pattern Memory   | --> | Judge Brain        |
| (Footprints)     |     | (Feedback Update)  |
+------------------+     +--------------------+
```

---

## 3. Known Architectural Risks

1. **Self-Deception & Bias:** A model evaluating its own simulated performance might overfit small samples of success while discounting contextual failures.
2. **Future Leakage:** Testing hypothetical decisions with look-ahead data or utilizing candles from after the trade entry moment.
3. **Memory Congestion:** Storing redundant or unvalidated market observations in long-term memory leading to performance drag.
4. **Interface Leakage:** Allowing interactive components (like future chat layer/conversation interfaces) to write directly to Memory or trigger execution routines.
