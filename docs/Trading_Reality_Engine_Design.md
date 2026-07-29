# Trading Reality Engine & Spread Awareness Layer Design

## 1. Overview
The **Trading Reality Engine** is designed to capture real-world execution conditions (bids, asks, spreads, slippage, and commissions) from live market data streams without contaminating the **Market Discovery Brain's** pure price-action learning model.

This maintains a clear separation between **Market Understanding** (learning price behavior patterns) and **Trading Reality Simulation** (real-world execution friction and costs).

---

## 2. Core Architecture Rules
To avoid the cognitive bias of associating execution costs directly with underlying price behaviors, the system strictly separates these memories:

1. **Market Understanding (Price Behavior Learning)**:
   - Evaluates: Price Sequence, Duration, Consecutive runs, and Reaction/Retracement shapes.
   - Strictly independent of spread, commission, and execution slippage.

2. **Trading Reality Simulation (Execution Quality Evaluation)**:
   - Evaluates: Bid/Ask differences, Spread Expansion/Contraction, Volatility-driven Slippage, and Commission rates.

```
+----------------------------------------+
|             Raw Market Data            |
+----------------------------------------+
                    |
                    v
+----------------------------------------+
|           Data Reality Layer           |
+----------------------------------------+
         |                        |
         v                        v
+------------------+    +--------------------+
| Price-Action     |    | Execution-Reality  |
| Event Discovery  |    | Analysis           |
+------------------+    +--------------------+
         |                        |
         v                        v
+------------------+    +--------------------+
| Market Experience|    | Trading Reality    |
| Memory (Sequences|    | Memory (Execution  |
| and Reactions)   |    | Quality/Costs)     |
+------------------+    +--------------------+
```

---

## 3. Data Collection Requirements
The engine tracks:
- **Spread Data**: bid, ask, spread value, spread percentage, spread change.
- **Price Execution Data**: expected vs actual simulated entry, execution difference, and slippage.
- **Market Conditions**: session time, volatility index, and liquidity ticks.

---

## 4. Integration with Simulation Brain
The `SimulationBrain` and `VirtualTradingEngine` use these real bid/ask spreads to simulate non-perfect entries and exits:
- For `BUY` trades: Entry occurs at `Ask` price, exit occurs at `Bid` price.
- For `SELL` trades: Entry occurs at `Bid` price, exit occurs at `Ask` price.
- Stop-Loss and Target checkpoints are evaluated using the adverse/favorable bid-ask boundaries to guarantee realism.

---

## 5. Anti-Bias Protection
The `ObservationBrain` and `PatternDiscoveryEngine` must never consume spread data as decision features. Spread data is classified purely as execution cost tracking, preventing accidental strategy creation based on broker spreads.
