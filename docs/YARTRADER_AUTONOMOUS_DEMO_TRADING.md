# YarTrader — Autonomous Demo Trading Architecture & Verification Certification

## Executive Overview

This document records the architectural audit, implementation, risk governance, mode isolation, and empirical verification for **Autonomous Demo Trading** in YarTrader.

**Primary Goal:** YarTrader autonomously consumes market data, executes its multi-stage intelligence/strategy/risk/decision pipeline, and dispatches simulated DEMO orders under DEMO account `52961173` on `Alpari-MT5-Demo` without requiring a manual API trigger (`POST /api/demo/run`) for every individual trade.

**Non-Negotiable Safety Gate:** Live trading remains 100% hard-blocked (`LIVE_TRADING_ENABLED=False`). Zero real orders or live broker connectivity are reachable during DEMO operation.

---

## 1. End-to-End Autonomous Execution Architecture

```text
Market Data Stream (MT5 / External Provider)
    ↓
Feature Generation Engine
    ↓
ResearchWorker Polling Loop
    ↓
ProfessionalSignalEngine & Decision Intelligence
    ↓
ProfessionalRiskEngine Evaluation
    ↓
DemoExecutionGate (9 Mandatory SRE Safety Checks)
    ↓
DemoExecutionEngine Order Placement
    ↓
Persistence Journal (runtime_logs/demo_trades.json)
    ↓
Web Dashboard / Monitoring Telemetry
```

### Key Components

1. **Market Data Layer:** Configured provider (`MT5Provider` or external fallback) fetches price ticks and OHLC candles.
2. **ResearchWorker (`app/workers/research_worker.py`):** Background thread managing periodic analysis cycles across registered active symbols (`SymbolRegistry`).
3. **Signal & Risk Pipeline:** Converts feature outputs into actionable directional signals (`BUY` / `SELL`) with SL/TP targets and volume sizing.
4. **DemoExecutionGate (`src/Execution/Safety/demo_execution_gate.py`):** Validates 9 SRE DEMO safety rules:
   - Check 1: Demo mode flag explicitly set (`demo_mode_flag=True`)
   - Check 2: Live trading disabled & MetaTraderSafetyGate verification
   - Check 3: Verified DEMO account (`52961173`) and server (`Alpari-MT5-Demo`) with `trade_mode == 0`
   - Check 4: Terminal trading permissions active
   - Check 5: Symbol tradeable (full trade mode)
   - Check 6: Account balance and margin sufficiency
   - Check 7: Position sizing limits (`0.01` min, `100.0` max)
   - Check 8: SL/TP bounds on correct side of entry price
   - Check 9: Duplicate order & cooldown protection
5. **DemoExecutionEngine (`src/Execution/Services/demo_execution_engine.py`):** Submits order requests to broker adapter and writes execution telemetry logs under `TradeYarStorageRoot`.

---

## 2. Trading Mode Hard Isolation Audit

To guarantee zero cross-mode contamination, YarTrader enforces strict physical and logical storage separation:

| Mode | Purpose | Persistence File / Engine | Cross-Contamination Status |
| :--- | :--- | :--- | :--- |
| **BACKTEST** | Historical strategy simulation | `runtime_logs/backtest_runs.json` (`IntelligenceBacktestEngine`) | **ISOLATED.** Does not alter Demo or Shadow state. |
| **DEMO** | Autonomous paper execution on DEMO feed | `runtime_logs/demo_trades.json` (`DemoExecutionEngine`) | **ISOLATED.** Does not alter Shadow or Backtest state. |
| **SHADOW** | Live paper strategy tracking & memory learning | `runtime_logs/shadow_trades.json` (`PredictiveShadowEngine`) | **ISOLATED.** Does not alter Demo or Backtest state. |
| **LIVE** | Real money broker execution | **HARD-BLOCKED** (`LIVE_TRADING_ENABLED=False`) | **BLOCKED.** `MetaTraderSafetyGate` rejects all live operations. |

---

## 3. Runtime Health & Semantics Matrix

YarTrader truthfully distinguishes process service availability from live production readiness:

- **Service Process Status:** `SERVICE_READY` (FastAPI container process and background worker loops active)
- **Production Trading Status:** `Not Ready` / `SERVICE_READY_DEGRADED` (When MT5 is disconnected or simulated fallback is active)
- **Autonomous Demo Status:** `DEMO_READY` / `DEMO_RUNNING` (Operates independently of live trading readiness)

---

## 4. Verification & Verification Drill Evidence

### Git Integrity
- **Commit Hash:** `3194285fac11570a842283b9c25cf53d04c9f414`
- **Branch:** `jules-14471198806759338167-0d3c95e2`
- **Staged Files:** Clean status relative to remediation branch.

### Test Suite Execution
- **Targeted Autonomous Demo Tests (`test_autonomous_demo_trading.py`):** 6 passed / 6 total (100%)
- **Targeted Remediation Tests (`test_shadow_readiness_remediation.py`):** 10 passed / 10 total (100%)
- **Full Repository Test Suite:** **1,561 passed / 1,561 total (100%)**

### Autonomous Verification Drill Results
- **Cycles Run:** 10 continuous research cycles
- **Decisions Evaluated:** 2 actionable signals (`BUY`)
- **Executed Demo Trades:** 1 trade executed, 1 signal skipped by cooldown protection
- **Shadow Journal Impact:** 3 trades before drill, 3 trades after drill (0 trades written to Shadow)

---

## 5. Master Certification

- **Autonomous Demo Trading:** `PASS`
- **Backtest Execution & Isolation:** `PASS`
- **Shadow Trading Isolation:** `PASS`
- **Live Trading Hard Boundary:** `BLOCKED`

**Final Verdict:**
`DEMO AUTONOMOUS TRADING — PASS`
