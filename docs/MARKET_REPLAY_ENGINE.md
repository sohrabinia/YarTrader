# Market Replay Engine

## 1. Overview
The **Market Replay Engine** (`IReplayEngine`) provides a controlled, sequential historical environment where the Analyst Brain can repeatedly practice and experience real market situations.

---

## 2. Timeless Structural Replays
The engine is not limited to static MetaTrader calendar grids. Instead, it replays price changes across dynamically discovered, state-based internal scales (e.g., 37-minute or 256-minute structures), evaluating structural patterns chronologically.

---

## 3. Strict Future Leakage Protection
At every simulation step, the engine hides all future candle and tick outcomes. Only historical memory, the current state, and previously learned knowledge can guide decisions.
