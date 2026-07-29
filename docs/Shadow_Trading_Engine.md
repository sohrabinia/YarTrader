# Shadow Trading Engine

## 1. Overview
The **Shadow Trading Engine** creates a complete simulated trading environment, testing the `AnalysisBrain` and `DecisionEngine` under realistic trading costs (spread, slippage, execution delay, and commission) while strictly guaranteeing zero live broker order execution.

---

## 2. Dynamic Option Space
The shadow engine supports four distinct decision states:
- `BUY`
- `SELL`
- `WAIT`
- `NO TRADE`
WAIT and NO TRADE are fully valid decisions, ensuring that the system is never forced to execute a trade.
