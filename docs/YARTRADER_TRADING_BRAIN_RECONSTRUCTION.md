# YARTRADER TRADING BRAIN RECONSTRUCTION
**Full Forensic Reconstruction & Scientific Backtest Optimization Audit of YarTrader Decision & Execution Core**
**Classification: READ-ONLY AUDIT & FORENSIC DOCUMENTATION**
**Repository Version / Commit: YarTrader v7.0 (HEAD: `5b7e817d44f43131a8ce68193a36bcbf2fdbd0fc`)**

---

## EXECUTIVE SUMMARY

This forensic audit performs a full, evidence-based call-chain reconstruction of the YarTrader trading decision and execution brain. It addresses the exact executable reachability, parameter flow, risk enforcement, win rate fallbacks, learning loops, entry predicates, execution authority, and scientific backtest/optimization capabilities.

---

## SECTION 1 — CANONICAL BRAIN TRACE

### Production Entry Points & Reachability Chain
The production background service (`app/workers/service.py`) initializes and launches `ResearchWorker` (`app/workers/research_worker.py:65`) and `IntelligenceWorker` (`app/workers/intelligence_worker.py:25`).

#### 1. Real Runtime Call Chain (Market Data to Broker Order)
```text
app/workers/service.py:75 (YarTraderServiceHost.on_start)
    ↓
app/workers/research_worker.py:45 (ResearchWorker.start)
    ↓
app/workers/research_worker.py:100 (ResearchWorker._run_research_cycle)
    ↓
src/Application/Runtime/research_runtime.py:72 (ResearchRuntime.run_once)
    ↓
src/Intelligence/Execution/core.py:67 (ExecutionIntelligenceCore.evaluate_context)
    ↓
src/Intelligence/Execution/strategy_orchestrator.py:50 (StrategyOrchestrator.evaluate_all_strategies)
    ↓
src/Intelligence/Execution/execution_planner.py:15 (ExecutionIntelligencePlanner.generate_execution_plan)
    ↓
app/workers/research_worker.py:195–239 (Actionable BUY/SELL decision detection & reversal check)
    ↓
src/Execution/Services/demo_execution_engine.py:43 (DemoExecutionEngine.execute_demo_decision)
    ↓
src/Execution/Safety/demo_execution_gate.py:30 (DemoExecutionGate.verify_demo_execution_eligibility)
    ↓
src/Execution/Adapters/mt5_adapter.py:150 (RealMT5BrokerAdapter.place_order)
```

### Component Classification

| Component Name | File & Function | Reachability | Classification | Authority / Purpose |
| -------------- | --------------- | ------------ | -------------- | ------------------- |
| `StrategyOrchestrator` | `src/Intelligence/Execution/strategy_orchestrator.py:50` | REACHABLE | **CANONICAL** | Evaluates 6 active trading strategies (`FAST_SCALP`, `SCALP`, `DAY_TRADING`, `JUMP`, `PRICE_ACTION_RTM`, `FRACTAL`) on M1/M5/M15/H1 data. |
| `ExecutionIntelligenceCore` | `src/Intelligence/Execution/core.py:67` | REACHABLE | **CANONICAL** | Central coordinator evaluating narrative, liquidity, zones, alignment, and strategies. |
| `ExecutionIntelligencePlanner` | `src/Intelligence/Execution/execution_planner.py:15` | REACHABLE | **CANONICAL** | Synthesizes strategy setup candidates into final execution plan (`BUY`, `SELL`, `WAIT`, `AVOID`). |
| `DemoExecutionEngine` | `src/Execution/Services/demo_execution_engine.py:43` | REACHABLE | **CANONICAL** | Dispatches demo order requests to MT5 adapter. |
| `DemoExecutionGate` | `src/Execution/Safety/demo_execution_gate.py:30` | REACHABLE | **CANONICAL (HARD STOP)** | Enforces `LIVE_TRADING_ENABLED = False`, position exclusivity, and directional SL/TP safety boundaries. |
| `ProfessionalSignalEngine` | `src/Decision/Intelligence/professional_signal_engine.py:120` | UNREACHABLE FROM WORKER | **ADVISORY / PARALLEL** | Generates standalone `ProfessionalSignal` objects. Integrated into `AutonomousDecisionEngine` API routes, but NOT called by `ResearchWorker`. |
| `AutonomousDecisionEngine` | `src/Decision/Intelligence/engine.py:50` | UNREACHABLE FROM WORKER | **ADVISORY / REST API** | Used in REST web API endpoints (`web_dashboard.py`). Not directly in the background worker loop. |
| `PredictiveShadowEngine` | `src/ShadowTrading/Engine/PredictiveShadowEngine.py:40` | REACHABLE (PASSIVE) | **SHADOW / RETIRED** | Imported and updated passively by `ResearchRuntime.run_once()` (`src/Application/Runtime/research_runtime.py:252`). Does NOT generate production execution signals. |

---

## SECTION 2 — CONFIDENCE VS WIN PROBABILITY

- **Transformation Trace:**
  - In `src/Intelligence/Execution/execution_planner.py:85`: `confidence` is calculated as `min(95.0, max(50.0, base_confidence + alignment_bonus))`.
  - In `src/Risk/Services/professional_risk_engine.py:220`: `win_probability` is passed as a separate parameter (default `win_probability = 0.55`).
  - **Transformation `win_probability = confidence_pct / 100.0`:** NOT found in the canonical worker path. The risk engine uses its default `0.55` win probability unless explicitly provided by caller.

### Hardcoded Confidence Values Audit

| File & Line | Value | Purpose | Reaches Risk? | Reaches EV? | Reaches Final Order? | Status |
| ----------- | ----- | ------- | ------------- | ----------- | -------------------- | ------ |
| `strategy_orchestrator.py:210` | `60.0%` | Min confidence threshold for `FAST_SCALP` | YES | NO | YES | CANONICAL |
| `strategy_orchestrator.py:255` | `65.0%` | Min confidence threshold for `SCALP` | YES | NO | YES | CANONICAL |
| `strategy_orchestrator.py:314` | `70.0%` | Min confidence threshold for `DAY_TRADING` | YES | NO | YES | CANONICAL |
| `strategy_orchestrator.py:370` | `60.0%` | Min confidence threshold for `JUMP` | YES | NO | YES | CANONICAL |
| `strategy_orchestrator.py:428` | `68.0%` | Min confidence threshold for `PRICE_ACTION_RTM` | YES | NO | YES | CANONICAL |
| `strategy_orchestrator.py:481` | `70.0%` | Min confidence threshold for `FRACTAL` | YES | NO | YES | CANONICAL |

---

## SECTION 3 — TP / SL / RR FORENSIC RECONSTRUCTION

- **TP Distance = SL Distance * 2.2:**
  - Located in `src/Decision/Intelligence/professional_signal_engine.py:165`.
  - **Reachability:** UNREACHABLE from the production `ResearchWorker` loop. Used only when `ProfessionalSignalEngine` is directly invoked via REST API.
- **Canonical Strategy TP Multipliers:**
  - `FAST_SCALP`: `TP = SL * 1.5` (`strategy_orchestrator.py:202`). Reaches final order.
  - `SCALP`: `TP = SL * 2.0` (`strategy_orchestrator.py:248`). Reaches final order.
  - `DAY_TRADING`: `TP = SL * 2.5` (`strategy_orchestrator.py:345`). Reaches final order.
- **RR Inventory:**
  - Global Risk Gate: `Real Net RR >= 1.5` enforced in `ProfessionalRiskEngine.evaluate_trade_risk()` (`src/Risk/Services/professional_risk_engine.py:265`).

---

## SECTION 4 — RISK CONTRACT / C-01

### Per-Trade Risk Percentages
- `src/Intelligence/Execution/portfolio.py:14`: `max_risk_per_trade_pct = 0.5%` (Advisory limit in execution planner).
- `src/Risk/Services/professional_risk_engine.py:220`: `risk_percentage = 1.0%` (Default keyword arg in trade risk evaluation).
- `src/Risk/Services/campaign_manager.py:50`: `risk_pct = 2.0%` (Strict initial leg equity risk).

### Git History / Blame Analysis
- Commit `b41a98c` (PR #218): Introduced `PortfolioRiskIntelligenceEngine` with 0.5% max risk per trade as a portfolio exposure budget.
- Commit `e72b409` (Phase B): Introduced `CampaignLifecycleManager` with mandatory 2.0% equity risk for multi-leg trade campaigns.
- **Divergence:** `PortfolioRiskIntelligenceEngine` (0.5%) acts as an advisory warning system during planning, whereas `CampaignLifecycleManager` (2.0%) executes actual position lot sizing in campaign mode.

---

## SECTION 5 — WIN RATE FALLBACK FORENSICS

- `src/Risk/Services/professional_risk_engine.py:220`: Default `win_probability = 0.55` (55%).
- `src/Research/Brain/temporal_forecast_engine.py:105`: Fallback `win_rate = 0.5` (50%) if total trades == 0.
- `src/Intelligence/Execution/similarity.py:100`: Default fallback `success_rate_pct = 50.0%` when no historical matches exist.
- **Impact:** When historical pattern memory lacks data, the system defaults to 50% / 55% baseline probability. This allows baseline setups to pass Expected Value calculations if Real Net RR >= 1.5.

---

## SECTION 6 — LEARNING / FEEDBACK LOOP VERIFICATION

- **Closed Trade Event Path:**
  - Position Close -> `BacktestAndLearningEngine.record_trade_outcome()` (`src/Application/Backtesting/backtest_learning_engine.py:140`).
  - Pattern Outcome -> `FractalPatternMemory.record_pattern_outcome()` (`src/Research/Brain/fractal_memory.py:50`). Writes pattern wins/losses into `patterns_memory.json`.
- **Feedback Authority:** Real active pattern memory updates future similarity confidence scores (`similarity.py:42`).
- **Classification:** **REAL ACTIVE LEARNING** (Pattern Memory persistence & score calibration).

---

## SECTION 7 — ENTRY CONDITION BOOLEAN RECONSTRUCTION

### 1. FAST_SCALP (Canonical)
$$\text{BUY} = (\text{EMA5} > \text{EMA13}) \land (\text{Price} > \text{EMA5}) \land (\text{Spread} \le 1.5\text{ pips}) \land (\text{Confidence} \ge 60.0\%)$$
$$\text{SELL} = (\text{EMA5} < \text{EMA13}) \land (\text{Price} < \text{EMA5}) \land (\text{Spread} \le 1.5\text{ pips}) \land (\text{Confidence} \ge 60.0\%)$$
*File:* `src/Intelligence/Execution/strategy_orchestrator.py:170–215`

### 2. SCALP (Canonical)
$$\text{BUY} = (\text{Bullish MSB}) \land (\text{Bullish FVG or OB Retest}) \land (\text{Spread} \le 2.5\text{ pips}) \land (\text{Confidence} \ge 65.0\%)$$
$$\text{SELL} = (\text{Bearish MSB}) \land (\text{Bearish FVG or OB Retest}) \land (\text{Spread} \le 2.5\text{ pips}) \land (\text{Confidence} \ge 65.0\%)$$
*File:* `src/Intelligence/Execution/strategy_orchestrator.py:220–265`

---

## SECTION 8 — EXECUTION AUTHORITY / OVERRIDE MAP

| Order of Gate | Gate Name | File & Function | Override / Trigger Condition | Can Block Order? |
| ------------- | --------- | --------------- | ---------------------------- | ---------------- |
| 1 | Strategy Confidence Gate | `strategy_orchestrator.py` | Signal confidence < Strategy Min Confidence | YES |
| 2 | Risk Engine Gate | `professional_risk_engine.py:265` | Real Net RR < 1.5 OR Spread > 5.0 pips OR EV <= $0 | YES |
| 3 | Portfolio Heat Gate | `portfolio.py:97` | Total portfolio equity risk > 6.0% | YES |
| 4 | Position Exclusivity Guard | `demo_execution_gate.py:132` | Active BUY + SELL on same symbol | YES |
| 5 | Directional Safety Gate | `demo_execution_gate.py:113` | BUY SL >= Entry OR BUY TP <= Entry | YES |
| 6 | Live Trading Safety Gate | `demo_execution_gate.py:55` | `LIVE_TRADING_ENABLED = False` | **YES (FINAL HARD STOP)** |

---

## SECTION 9 — SCIENTIFIC BACKTEST / OPTIMIZATION AUDIT

- **Backtest Engine:** `BacktestAndLearningEngine` (`src/Application/Backtesting/backtest_learning_engine.py`).
- **Capabilities Audit:**
  - Automated Repeated Backtesting: YES (`run_backtest_with_learning()`).
  - Transaction Cost Modeling: YES (Models spread, $7/lot commission, 0.5 pip slippage).
  - Out-of-Sample (OOS) Validation: NOT IMPLEMENTED in current automated scripts.
  - Parameter Sweep / Grid Search: NOT IMPLEMENTED in runtime core.
  - Walk-Forward Optimization Loop: NOT IMPLEMENTED in runtime core.

---

## SECTION 10 — ANTI-CHEATING / BACKTEST INTEGRITY AUDIT

| Protection / Vulnerability | File & Line | Status | Forensic Finding |
| -------------------------- | ----------- | ------ | ---------------- |
| Look-Ahead Bias Protection | `backtest_learning_engine.py:80` | **PROTECTED** | Iterates strictly bar-by-bar using historical slice `[:i+1]`. |
| Transaction Cost Modeling | `professional_risk_engine.py:245` | **PROTECTED** | Includes spread + commission + slippage in net distance calculation. |
| Future Candle Access | `backtest_learning_engine.py:85` | **PROTECTED** | Future candles hidden during decision evaluation. |
| Parameter Overfitting Protection | N/A | **VULNERABLE** | System currently uses fixed static parameters without automated OOS validation. |

---

## SECTION 11 — PERFORMANCE METRICS

- **Calculated Metrics (`src/Application/Backtesting/backtest_learning_engine.py:180–200`):**
  - `Win Rate`: `(Wins / Total Closed Trades) * 100`
  - `Profit Factor`: `Gross Profits / Gross Losses`
  - `Expectancy`: `(Win Rate * Avg Win) - (Loss Rate * Avg Loss)`
  - `Max Drawdown`: Maximum peak-to-trough equity decline percentage.

---

## SECTION 12 — OPTIMIZATION OBJECTIVE

- **Optimization Objective:** `OPTIMIZATION OBJECTIVE = NOT FOUND` (No active automated parameter optimizer exists in static code).

---

## SECTION 13 — REPEATED SELF-IMPROVEMENT VERIFICATION

- **Status:** `REPEATED SELF-OPTIMIZATION = NOT FOUND` (Pattern memory records outcomes, but automated strategy parameter re-tuning loop is not implemented).

---

## SECTION 14 — OVERFITTING / GENERALIZATION TEST

- **Status:** `NOT DETERMINABLE FROM STATIC CODE` (Requires long-term walk-forward historical dataset execution across multiple market regimes).

---

## SECTION 15 — WORKED XAUUSD M5 EXAMPLE

- **Symbol:** XAUUSD | **Timeframe:** M5
- **Step 1: Data Ingestion:** Live Ask $2,000.00 / Bid $1,999.90 (Spread = 1.0 pip).
- **Step 2: Strategy Evaluation (`SCALP`):** M5 Bullish MSB detected + Bullish FVG retest. Confidence = 68.0% (>= 65.0% min).
- **Step 3: Signal Generation:** `BUY` signal generated. Raw Entry = $2,000.00 | Raw SL = $1,995.00 (SL Dist = $5.00) | Target TP = $2,010.00 (2.0x SL Dist).
- **Step 4: Risk Evaluation:**
  - Net Cost = 1.0 pip spread + 0.5 pip slippage = $0.15.
  - Net SL Dist = $5.15 | Net TP Dist = $9.85.
  - Net Real RR = $9.85 / $5.15 = **1.91** (>= 1.5 min threshold).
  - Expected Value = (0.55 * $191.00) - (0.45 * $100.00) = **+$60.05** (> $0).
- **Step 5: Position Sizing (2.0% Risk on $10,000 Equity):**
  - Risk Budget = $200.00.
  - Risk Per Lot = ($5.15 * 100) + $7.00 commission = $522.00.
  - Calculated Lots = $200.00 / $522.00 = 0.3831 -> **0.38 Lots**.
- **Step 6: Execution Safety Gate:** Checks `LIVE_TRADING_ENABLED = False`. Order dispatched to MT5 Paper Account in Demo Mode.

---

## SECTION 16 — FINAL FORENSIC VERDICT

| Area | Status | Evidence / Source File |
| ---- | ------ | ---------------------- |
| Canonical Brain | **REACHABLE** | `research_worker.py` -> `ResearchRuntime` -> `ExecutionIntelligenceCore` -> `StrategyOrchestrator` |
| Confidence Flow | **ADVISORY TO STRATEGY** | Enforced at strategy entry gate (`strategy_orchestrator.py`) |
| Win Probability | **HARDCODED DEFAULT (0.55)** | `professional_risk_engine.py:220` |
| Risk Contract C-01 | **2.0% CAMPAIGN / 0.5% ADVISORY** | Campaign execution uses 2.0% (`campaign_manager.py:50`) |
| Execution Safety | **HARD LOCKED (`LIVE_TRADING_ENABLED=False`)** | `demo_execution_gate.py:55` |
| Scientific Backtest | **IMPLEMENTED (ZERO LOOK-AHEAD)** | `backtest_learning_engine.py` |
| Automated Self-Optimization | **NOT FOUND** | No active parameter grid-search optimizer in runtime code |
