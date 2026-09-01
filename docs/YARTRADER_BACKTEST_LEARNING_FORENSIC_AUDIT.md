# YARTRADER BACKTEST + LEARNING FORENSIC AUDIT
**Forensic Audit of YarTrader's Backtest, Learning, Pattern-Memory, and Outcome-Feedback Infrastructure**
**Classification: AUDIT & RESEARCH ARCHITECTURE DOCUMENTATION ONLY — NO SOURCE CODE CHANGES**
**Repository Version / Commit: YarTrader v7.0 (HEAD: `5b7e817d44f43131a8ce68193a36bcbf2fdbd0fc`)**
**Branch Name: `forensic-backtest-learning-audit`**

---

## EXECUTIVE SUMMARY

This forensic audit evaluates the actual executable state of YarTrader's backtest engine, historical pattern memory, statistical feedback loops, and learning capabilities. It provides an unvarnished analysis of what the codebase currently implements, what it stores passively, where data leakage or vulnerabilities exist, and what architecture is required before constructing a safe, regime-aware self-optimization loop.

---

## CANONICAL RUNTIME BASELINE VERIFICATION

The production worker execution path was verified from source code:
```text
app/workers/service.py:75 (YarTraderServiceHost.on_start)
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
app/workers/research_worker.py:239 (DemoExecutionEngine.execute_demo_decision)
    ↓
src/Execution/Safety/demo_execution_gate.py:30 (DemoExecutionGate.verify_demo_execution_eligibility)
    ↓
LIVE_TRADING_ENABLED = False (Hard Lock)
```

---

## SECTION 1 — EXISTING BACKTEST ENGINE

- **Engine Implementation:** `BacktestAndLearningEngine` (`src/Application/Backtesting/backtest_learning_engine.py:15`).
- **Sequential Execution:** YES. Iterates chronologically bar-by-bar (`for i in range(start_index, len(candles)):`, Line 70).
- **Bar-by-Bar Processing:** YES (`history_candles = candles[:i+1]`, Line 72).
- **Future Candle Isolation:** YES. Only `history_candles` up to index `i` are passed to `ExecutionIntelligenceCore.evaluate_context()`.
- **Trade Simulation:**
  - Entry Simulation: YES (`plan.get("entry", current_price)`, Line 163).
  - Stop Loss Simulation: YES (`low_price <= sl` / `high_price >= sl`, Lines 92, 101).
  - Take Profit Simulation: YES (`high_price >= tp` / `low_price <= tp`, Lines 95, 104).
  - Trade Closure & PnL: YES (`pnl_dist * volume * multiplier`, Lines 113-116).
- **Cost & Execution Features:**
  - Spread Modeling: NOT INCLUDED in `BacktestAndLearningEngine` order exit calculations (uses raw bar high/low).
  - Commission & Slippage: NOT DEDUCTED from trade PnL in `BacktestAndLearningEngine`.
  - Execution Delay: NOT MODELED (simulates immediate fill at bar close / limit price).
  - Multiple Positions: NO (`open_position` supports max 1 position at a time per symbol).

---

## SECTION 2 — LOOK-AHEAD / DATA LEAKAGE FORENSICS

| Data / Feature | Source File & Line | Reachability at Timestamp T | Status |
| -------------- | ------------------ | --------------------------- | ------ |
| Candle `T+1` to `T+N` | `backtest_learning_engine.py:72` | Hidden (`candles[:i+1]`) | **SAFE** |
| Future High / Low / Close | `backtest_learning_engine.py:73` | Hidden | **SAFE** |
| Future ATR / Volatility | `src/Research/Features/calculators.py:45` | Computed on slice `[:i+1]` | **SAFE** |
| Future Pattern Label / Memory | `src/Research/Brain/memory.py:250` | Written POST-TRADE only | **SAFE (CAUSAL)** |
| Static Risk Engine Default Win Rate | `src/Risk/Services/professional_risk_engine.py:220` | Hardcoded constant `0.55` | **POTENTIAL BIAS** |

---

## SECTION 3 — TRAIN / VALIDATION / TEST SEPARATION

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** `BacktestAndLearningEngine` runs on a single input candle array without splitting into distinct Train, Validation, or Out-of-Sample Test holdout sets.

---

## SECTION 4 — WALK-FORWARD VALIDATION

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** No rolling window or walk-forward validation script exists in the active runtime codebase.

---

## SECTION 5 — FractalPatternMemory FORENSICS

1. **Instantiation:** Created inside `MarketMemorySystem.__init__()` (`src/Research/Brain/memory.py:35`).
2. **Setup Reception:** Receives situation signature (`[entry, sl, tp]`) upon trade open.
3. **Outcome Write:** `FractalPatternMemory.record_pattern_outcome()` (`src/Research/Brain/fractal_memory.py:50`).
4. **Fields Written:** `wins`, `losses`, `frequency`, `success_rate`, `confidence_weight`.
5. **Persistence:** Saved to `runtime_logs/brain_memory/patterns_memory.json` (`src/Research/Brain/memory.py:120`).
6. **Reload:** Reloaded during `MarketMemorySystem` initialization (`memory.py:140`).
7. **Future Decision Read:** Queried by `StructureSimilarityEngine.find_similar_structures()` (`src/Intelligence/Execution/similarity.py:40`).
8. **Decision Influence:** Modifies `similarity_score` and confidence weight in `ExecutionIntelligencePlanner`. Does NOT directly alter lot size or bypass risk gates.

---

## SECTION 6 — CAUSAL LEARNING TEST

- **Verification:** Trade $N$ outcome is processed only AFTER trade $N$ closes (`backtest_learning_engine.py:111-137`).
- **Guarantee:** Trade $N$ decision uses `history_candles = candles[:i+1]` prior to trade closure. Trade $N$ outcome updates `MarketMemorySystem` for Trade $N+1$ or later.
- **Classification:** **CAUSALLY VALID & LEAKAGE-FREE**.

---

## SECTION 7 — LEARNING VS STORAGE

| Level | Feature / Mechanism | Implementation File | Status |
| ----- | ------------------- | ------------------- | ------ |
| **Level A: Outcome Storage** | JSON Trade Logs & Experiences | `src/Research/Brain/memory.py:120` | **ACTIVE** |
| **Level B: Statistical Learning** | Pattern Success Rate & Weight Calibration | `src/Research/Brain/fractal_memory.py:76` | **ACTIVE** |
| **Level C: Parameter Adaptation** | Dynamic Re-tuning of Strategy Parameters | N/A | **NOT IMPLEMENTED** |
| **Level D: Strategy Selection Adaptation** | Automatic Switching of Strategy Weights | N/A | **NOT IMPLEMENTED** |
| **Level E: Live Decision Adaptation** | Real-time Pattern Score Calibration | `src/Intelligence/Execution/similarity.py:42` | **ACTIVE** |

---

## SECTION 8 — STRATEGY WEIGHT LEARNING

- **Status:** **NOT FOUND / NOT IMPLEMENTED**.
- **Evidence:** Strategy priority and selection in `StrategyOrchestrator` (`src/Intelligence/Execution/strategy_orchestrator.py:50`) use fixed evaluation order without dynamic weight adjustments based on trade outcomes.

---

## SECTION 9 — CONFIDENCE CALIBRATION

- **Status:** **PARTIALLY IMPLEMENTED (PATTERN-LEVEL)**.
- **Evidence:** `confidence_weight = 0.4 + (success_rate * 0.5)` in `FractalPatternMemory` (`src/Research/Brain/fractal_memory.py:78`). Overall strategy confidence thresholds remain static constants (60%, 65%, 70%).

---

## SECTION 10 — WIN RATE LEARNING

- **Status:** **PARTIALLY IMPLEMENTED**.
- **Evidence:** Backtest engine computes actual closed win rate (`backtest_learning_engine.py:181`), but `ProfessionalRiskEngine` defaults to `win_probability = 0.55` (`src/Risk/Services/professional_risk_engine.py:220`) for Expected Value calculations.

---

## SECTION 11 — PARAMETER OPTIMIZATION

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** Grid search, Bayesian optimization, genetic algorithms, and parameter sweep loops are NOT present in the runtime codebase.

---

## SECTION 12 — REPEATED SELF-IMPROVEMENT

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** The system does not automatically execute iterative backtest-evaluate-mutate-retest loops.

---

## SECTION 13 — RANGE LEARNING

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** `MarketMemorySystem` stores pattern outcomes globally per symbol, but does NOT partition performance statistics by market regime (`RANGING` vs `TRENDING` vs `EXPANSION`).

---

## SECTION 14 — RANGE TRADING CAPABILITY

- **Status:** **IMPLEMENTED IN RESEARCH BRAIN / ADVISORY**.
- **Evidence:** `FractalBaseDetectionEngine` (`src/Research/Brain/fractal_base_detection_engine.py:35`) identifies range high/low/squeeze. `PRICE_ACTION_RTM` strategy (`strategy_orchestrator.py:375`) retests range levels. Target RR 1:2 is evaluated against global Net Real RR >= 1.5.

---

## SECTION 15 — EXPANSION / HIGH-RR LEARNING

- **Status:** **PARTIALLY IMPLEMENTED**.
- **Evidence:** Strategy Orchestrator supports target RR up to 2.5x (`DAY_TRADING` / `JUMP`). Target RR > 2.5x (e.g. 1:4, 1:5) is NOT supported in current strategy rules.

---

## SECTION 16 — EXHAUSTION / REVERSAL LEARNING

- **Status:** **IMPLEMENTED AT STRATEGY / HANDOFF LEVEL**.
- **Evidence:** `ReversalHandoffManager` (`src/Risk/Services/reversal_handoff.py:20`) evaluates post-close non-blind reversal candidates for Fast Scalp / Scalp styles.

---

## SECTION 17 — COST-ADJUSTED PERFORMANCE

- **Status:** **IMPLEMENTED IN RISK ENGINE / PARTIAL IN BACKTEST**.
- **Evidence:** `ProfessionalRiskEngine.evaluate_trade_risk()` (`src/Risk/Services/professional_risk_engine.py:245`) calculates Net Real RR deducting spread, commission ($7/lot), and slippage (0.5 pips). `BacktestAndLearningEngine` computes raw price distance PnL.

---

## SECTION 18 — POSITION SIZING LEARNING

- **Status:** **IMPLEMENTED IN RISK ENGINE**.
- **Evidence:** `ProfessionalRiskEngine.evaluate_equity_risk_and_position_size()` (`professional_risk_engine.py:155`) adjusts lot size inversely to Net SL distance to maintain strict account equity risk (2.0% initial leg / 1.0% add-on leg).

---

## SECTION 19 — OPTIMIZATION OBJECTIVE

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** No multi-objective optimization function exists in static code.

---

## SECTION 20 — OVERFITTING DEFENCE

- **Status:** **NOT IMPLEMENTED**.
- **Evidence:** Parameter sensitivity analysis and train/test divergence checks do not exist in runtime code.

---

## SECTION 21 — RESEARCH MEMORY

- **Status:** **IMPLEMENTED FOR EXPERIENCES / PATTERNS**.
- **Evidence:** Experiences saved to `experiences.json` and patterns to `patterns_memory.json`. Failed backtest experiments are NOT automatically archived to an experiment database.

---

## SECTION 22 — CAPITAL GROWTH METRICS

- **Status:** **PARTIALLY IMPLEMENTED**.
- **Evidence:** `BacktestAndLearningEngine` computes `final_balance`, `net_pnl`, `win_rate_pct`, and `closed_trades`. Sharpe, Sortino, and Risk of Ruin are NOT calculated in the backtest report.

---

## SECTION 23 — FINAL CAPABILITY MATRIX

| Capability | Exists | Partial | Not Implemented | Evidence File & Line |
| ---------- | :---: | :-----: | :-------------: | -------------------- |
| Backtest Engine | **YES** | | | `src/Application/Backtesting/backtest_learning_engine.py:15` |
| Sequential Simulation | **YES** | | | `backtest_learning_engine.py:70` |
| No-Lookahead Protection | **YES** | | | `backtest_learning_engine.py:72` |
| Train/Test Split | | | **NOT IMPLEMENTED** | N/A |
| Walk-Forward Validation | | | **NOT IMPLEMENTED** | N/A |
| Outcome Recording | **YES** | | | `src/Research/Brain/memory.py:250` |
| Pattern Memory | **YES** | | | `src/Research/Brain/fractal_memory.py:50` |
| Pattern Outcome Learning | **YES** | | | `fractal_memory.py:76` |
| Confidence Calibration | | **PARTIAL** | | `fractal_memory.py:78` |
| Win-Rate Learning | | **PARTIAL** | | `backtest_learning_engine.py:181` |
| Strategy-Weight Learning | | | **NOT IMPLEMENTED** | N/A |
| Parameter Optimization | | | **NOT IMPLEMENTED** | N/A |
| Repeated Optimization Loop | | | **NOT IMPLEMENTED** | N/A |
| Range Detection | **YES** | | | `src/Research/Brain/fractal_base_detection_engine.py:35` |
| Regime-Specific Learning | | | **NOT IMPLEMENTED** | N/A |
| Cost Model (Risk Engine) | **YES** | | | `src/Risk/Services/professional_risk_engine.py:245` |
| Risk-Adjusted Position Sizing | **YES** | | | `professional_risk_engine.py:155` |
| Overfitting Defence | | | **NOT IMPLEMENTED** | N/A |

---

## SECTION 24 — FUTURE IMPLEMENTATION BOUNDARY

*Target Architecture for Future Development (Design Only — Do Not Implement in this Task):*
```text
HISTORICAL MARKET DATA
        ↓
REGIME CLASSIFIER (RANGE / BREAKOUT / TREND / REVERSAL)
        ↓
REGIME-SPECIFIC POLICY SELECTOR
        ↓
ZERO LOOK-AHEAD BACKTEST SIMULATOR (WITH COSTS)
        ↓
POST-TRADE OUTCOME FEEDBACK
        ↓
WALK-FORWARD OUT-OF-SAMPLE VALIDATION
        ↓
RETAIN / REJECT POLICY MUTATION
```

---

## SECTION 25 — FINAL QUESTIONS & FORENSIC ANSWERS

1. **Does YarTrader currently learn?**
   *YES.* It records closed trade outcomes into `MarketMemorySystem` and `FractalPatternMemory`, updating pattern success rates and similarity confidence weights.
2. **What exactly does it learn?**
   It learns local pattern match success rates (`wins / frequency`) and adjusts pattern confidence weights (`0.4 + 0.5 * success_rate`).
3. **Is that learning causal and leakage-free?**
   *YES.* Pattern memory updates occur strictly post-close and apply to future bar evaluations.
4. **Does it learn strategy weights?**
   *NO (NOT IMPLEMENTED).* Strategy evaluation sequence in `StrategyOrchestrator` is fixed.
5. **Does it learn confidence?**
   *PARTIALLY.* Pattern similarity weights update dynamically, but base strategy confidence thresholds are static.
6. **Does it learn win probability?**
   *PARTIALLY.* Calculated in backtest reports, but `ProfessionalRiskEngine` defaults to `0.55`.
7. **Does it learn regime behavior?**
   *NO (NOT IMPLEMENTED).* Pattern memory is not partitioned by regime.
8. **Does it optimize parameters automatically?**
   *NO (NOT IMPLEMENTED).* No grid search or parameter optimizer exists.
9. **Can it repeatedly backtest and improve itself?**
   *NO (NOT IMPLEMENTED).* No automated self-improvement loop exists.
10. **Does it have walk-forward validation?**
    *NO (NOT IMPLEMENTED).*
11. **Does it distinguish range from expansion?**
    *YES.* `NarrativeEngine` and `FractalBaseDetectionEngine` classify market regimes.
12. **Can it learn range trading?**
    *PARTIALLY.* Range setups evaluate via `PRICE_ACTION_RTM`, but range-specific memory learning is not partitioned.
13. **Can it optimize RR or stop placement?**
    *NO (NOT IMPLEMENTED).* Stop and TP multipliers are fixed per strategy.
14. **What is the minimum safe next implementation phase?**
    Construct an isolated research script supporting Train/Validation/Test data splitting and parameter grid search without modifying the frozen Trading Core.
