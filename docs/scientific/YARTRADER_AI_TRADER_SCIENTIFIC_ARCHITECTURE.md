# YarTrader — AI Trader Scientific Architecture Specification

## 1. Executive Summary
This document establishes the authoritative scientific architecture of the YarTrader Autonomous Financial Intelligence Platform. It codifies the terminal constraints, lifecycle boundaries, multi-scale fractal intelligence mapping, risk veto authority, and scientific validation gates governing all trade research and execution.

## 2. Canonical Architectural Principles
1. **Architecture vs Scientific Validation:** Architecture defines what the system is allowed to do; Scientific Validation determines which lifecycle policy actually works.
2. **Representations are Hypotheses:** Price Action, RTM, and Fractal representations are hypotheses to be empirically tested, not beliefs to be hard-coded.
3. **Intelligence is Not Execution Authority:** Intelligence can observe, interpret, and propose, but has zero order placement authority.
4. **Independent Risk Veto:** Risk is an independent veto authority that can reject any proposed decision for any reason.
5. **RL Boundary:** Reinforcement Learning (RL) operates strictly as a proposal mechanism and does NOT own or override Risk or EOD constraints.
6. **EOD Flatten as Terminal Safety Constraint:** No position may remain open after the defined trading day. Overnight positions are strictly forbidden.
7. **Trading Style Constraint:** Fast Scalp and Scalp are the only permitted execution styles (M1–M15 execution timeframes). Higher timeframes (H1, H4, D1) provide context only.
8. **Evidence > Assertion:** Every operational claim must be backed by reproducible empirical evidence. Demo/simulation is not Production; Software PASS is not Scientific PASS.

## 3. Mandatory Trading Policy & Execution Boundary
* **Permitted Styles:** Fast Scalp, Scalp.
* **Execution Timeframes:** M1, M5, M15.
* **Context Timeframes:** H1, H4, D1, W1, MN1 (Context, Regime, Liquidity, and Alignment only).
* **Overnight Rule:** ABSOLUTELY FORBIDDEN.
* **Multi-Day Rule:** ABSOLUTELY FORBIDDEN.
* **EOD Flatten:** Mandatory full closure of all open live, paper, and shadow positions prior to session cutoff.

## 4. End-to-End System Pipeline
```text
Market Data
    ↓
Data Integrity Check
    ↓
Multi-Timeframe Fractal Engine
    ↓
Price Action / RTM Feature Extraction
    ↓
Regime Identification Engine
    ↓
Execution Intelligence Core
    ↓
Decision Engine (Propose Entry/Management)
    ↓
Professional Risk Engine (Independent Veto)
    ↓
Position Lifecycle Manager
    ↓
Execution Adapter (MT5 / Demo / Shadow)
    ↓
EOD Flatten Monitor (Terminal Safety)
    ↓
Outcome Analyzer & Trade Journal
```

## 5. Position Lifecycle & State Machine
The position lifecycle enforces strict terminal transitions:
```text
ENTRY_PENDING
      ↓
ACTIVE_SCALP
      │
      ├── CONTINUE
      ├── PARTIAL_EXIT
      ├── TIGHTEN_PROTECTION
      ├── RECLASSIFY_TO_RUNNER (Same Trading Day Only)
      └── INVALIDATE
               ↓
          EXIT_PENDING
               ↓
             CLOSED

RUNNER (Intraday Only)
      │
      ├── CONTINUE
      ├── PARTIAL_EXIT
      └── INVALIDATE
               ↓
             CLOSED

ANY STATE
      ↓
EOD CUTOFF REACHED
      ↓
FORCED_EXIT
      ↓
VERIFY BROKER FLAT
      ↓
CLOSED
```

## 6. EOD Flatten & Failure Handling
If an open position exists when the session cutoff threshold is reached:
1. `EOD_FLATTEN` trigger fires immediately.
2. Market close order is dispatched to execution adapter.
3. Broker position verification is queried (`mt5.positions_get`).
4. If flat confirmation is not received within 5 seconds, an `EOD_FLATTEN_FAILURE` critical alert is emitted, emergency execution retry is initiated, and trading is locked.
5. Account state MUST be reconciled to `OPEN_POSITIONS = 0` before the next trading day begins.

## 7. Scientific Validation Pipeline Gates
To achieve Scientific Trading Release, a candidate strategy must sequentially pass:
* **Gate 0:** Dataset Provenance & Integrity (Verified RAW SHA256, 0 missing/duplicate bars).
* **Gate 1:** Look-Ahead & Leakage Prevention (Strict causal time boundaries `t_feature <= t_decision`).
* **Gate 2:** Baseline Comparison (Outperform null baseline and fixed benchmark).
* **Gate 3:** Out-Of-Sample (OOS) & Walk-Forward Validation.
* **Gate 4:** Regime Robustness (Evaluated across Trend, Range, High Volatility, and Low Volatility).
* **Gate 5:** Realistic Transaction Costs & Slippage (Spread, commission, and slippage stress testing).
* **Gate 6:** Multiple Testing / Data Snooping Controls.
* **Gate 7:** Standalone Expectancy & Economic Significance (`Expectancy > $0.00`, `Profit Factor > 1.0`).

## 8. Current Scientific Baseline Evidence
* **Dataset:** XAUUSD M1 Dukascopy 2021–2026 (2,460,951 bars, SHA256 `7adaf622f4513e0e5509c57d6adaa1404f43067174760269eb86a3cda25e85d7`).
* **Standalone Base Breakout Strategy:**
  - Expectancy: -$4.60/oz
  - Win Rate: 30.73%
  - Profit Factor: 0.86
  - Net P&L: -$2,066.52
* **Baseline Strategy:**
  - Expectancy: -$7.90/oz
  - Win Rate: 22.20%
  - Profit Factor: 0.81
* **Scientific Verdict:** `SCIENTIFIC_TRADING_RELEASE = BLOCKED` (Positive expectancy not yet established).

## 9. Live Trading Safety Isolation
* **`LIVE_TRADING_ENABLED = False`** (Hard-locked repository-wide).
* **`REAL_ORDERS = 0`** (Hard-locked repository-wide).
* **Execution Target:** Restricted strictly to DEMO account `52961173` on `Alpari-MT5-Demo` or local shadow execution.
