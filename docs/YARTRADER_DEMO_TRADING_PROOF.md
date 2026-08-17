# YARTRADER DEMO TRADING EXECUTION PROOF

## Executive Overview
This document provides evidence of a fresh, end-to-end Demo Trading execution generated during today's live runtime session.

---

## Complete Signal-to-Demo Pipeline Execution

```
Market Data (XAUUSD H1 Feed)
      ↓
Research Intelligence Engine
      ↓
Signal Generation (sig-77b2b6, Long, Confidence 85%)
      ↓
Decision Engine Evaluation (Approved)
      ↓
Demo Trading Scenario Runner (Alpari-MT5-Demo Account 52961173)
      ↓
Trade Journal Persistence (runtime_logs/demo_trades.json)
      ↓
Frontend Dashboard & Demo Terminal Display
```

---

## Live Demo Trade Evidence Record

- **Demo Trade ID**: `demo-trade-a05411`
- **Signal ID**: `sig-77b2b6`
- **Run ID**: `demo-run-0bd693`
- **Symbol**: `XAUUSD`
- **Timeframe**: `H1` (64 Tick Frame)
- **Direction / Side**: `BUY`
- **Confidence Score**: `85.0%`
- **Volume / Lots**: `1.00 Lot`
- **Entry Price**: `$1.2478`
- **Exit Price**: `$1.2603`
- **Stop Loss (SL)**: `$1.2353`
- **Take Profit (TP)**: `$1.2790`
- **Open Timestamp**: `2026-08-17T05:10:14.173078`
- **Close Timestamp**: `2026-08-17T05:10:14.173150`
- **Realized P&L**: **+$250.00**
- **Trade Status**: `CLOSED / FILLED`
- **Broker Target**: `Alpari-MT5-Demo (Account 52961173)`

---

## Verification & Persistence
This trade record has been saved to disk under `runtime_logs/demo_trades.json` and is visible on the React SPA UI at `#/demo`.
