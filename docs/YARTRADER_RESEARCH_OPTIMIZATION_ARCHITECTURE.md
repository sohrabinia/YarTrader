# YARTRADER RESEARCH OPTIMIZATION ARCHITECTURE

**Isolated Research & Optimization Layer Specification for YarTrader**
**Classification: RESEARCH INFRASTRUCTURE DOCUMENTATION**
**Repository Version / Commit SHA:** `9475c9383e2da017d23d8c11e74fec25aa1cc6c8`
**Baseline Forensic Audit Reference:** `docs/YARTRADER_BACKTEST_LEARNING_FORENSIC_AUDIT.md`

---

## 1. ARCHITECTURE OVERVIEW

The YarTrader Research Optimization Engine provides an isolated, scientific laboratory surrounding the frozen Trading Core. It enables parameter space grid search, chronological Train/Validation/Test dataset splitting, cost-adjusted multi-objective evaluation, Walk-Forward Optimization (WFO), overfitting diagnostics, and experiment provenance recording.

```text
HISTORICAL MARKET DATA
          │
          ▼
DATASET SPLITTER (TRAIN / VALIDATION / TEST)
          │
          ▼
PARAMETER SPACE GRID SEARCH (CARTERSIAN PRODUCT)
          │
          ▼
ZERO LOOK-AHEAD BACKTEST SIMULATOR (WITH COSTS)
          │
          ▼
MULTI-OBJECTIVE EVALUATOR (PNL, WIN RATE, EXPECTANCY, DRAWDOWN)
          │
          ▼
WALK-FORWARD OPTIMIZER (WFO)
          │
          ▼
OVERFITTING DIAGNOSTICS (TRAIN/VAL DIVERGENCE & SENSITIVITY)
          │
          ▼
EXPERIMENT PROVENANCE & REPORTING (JSON & MARKDOWN)
          │
          X  <--- STRICT RESEARCH-ONLY BOUNDARY
          │
   NO AUTOMATIC PRODUCTION PROMOTION
```

---

## 2. ABSOLUTE SAFETY & ISOLATION BOUNDARIES

1. **Trading Core Freeze:** The live decision and execution engines (`DecisionEngine`, `ProfessionalSignalEngine`, `StrategyOrchestrator`, `ProfessionalRiskEngine`, `DemoExecutionEngine`, `DemoExecutionGate`) remain strictly **READ-ONLY** and untouched.
2. **Zero Broker / Order Interaction:** The research optimization runner operates on historical bar arrays without invoking MetaTrader 5 IPC or broker order placement APIs.
3. **No Automatic Promotion:** Optimized research parameter configurations produce `RESEARCH_CANDIDATE` objects for analysis and report generation. They **NEVER** replace live, demo, or production system configurations automatically.

---

## 3. CORE COMPONENTS

### 3.1 Parameter Space Abstraction (`src/Application/Research/optimization/parameter_space.py`)
Provides generic abstraction for defining parameter ranges (`ParameterSpace`). Generates deterministic Cartesian products of all parameter combinations without mutating global state.

### 3.2 Dataset Splitter (`src/Application/Research/optimization/dataset_splitter.py`)
Splits historical candle data strictly chronologically (default 60% Train, 20% Validation, 20% Test) without random shuffling or future data leakage. Generates SHA-256 hashes for dataset identity verification.

### 3.3 Cost-Adjusted Cost Model (`src/Application/Research/optimization/cost_model.py`)
Calculates transaction costs deducting spread (1.0 pip default), commission ($7.00/lot default), and slippage (0.5 pips default), outputting both Gross PnL and Net PnL.

### 3.4 Multi-Objective Evaluator (`src/Application/Research/optimization/objective.py`)
Calculates comprehensive metrics (Net PnL, Win Rate %, Profit Factor, Expectancy, Max Drawdown %, Average R-multiple, Objective Score). Penalizes candidates with insufficient trade sample size (< 5 trades) or excessive drawdown (> 15%).

### 3.5 Grid Search Engine (`src/Application/Research/optimization/grid_search.py`)
Executes exhaustive parameter sweeps against backtest simulations with built-in failure isolation so individual configuration errors do not crash the optimization run.

### 3.6 Walk-Forward Optimizer (`src/Application/Research/optimization/walk_forward.py`)
Implements chronological Walk-Forward Optimization (WFO) across rolling windows, evaluating best training candidates on unseen Out-of-Sample (OOS) data blocks and aggregating WFO stability metrics.

### 3.7 Overfitting Diagnostics (`src/Application/Research/optimization/overfitting.py`)
Detects Train vs Validation and Validation vs Test metric degradation (> 40% degradation triggers overfitting flag). Evaluates parameter sensitivity and trade count stability.

### 3.8 Baseline Evaluator (`src/Application/Research/optimization/baseline.py`)
Establishes a frozen baseline control group (`DEFAULT_FROZEN_CORE`) and compares research candidate performance against the baseline.

### 3.9 Experiment Provenance & Reporting (`src/Application/Research/optimization/provenance.py` & `report.py`)
Records immutable provenance data (Experiment ID, commit SHA, dataset hash, configuration hash, metrics, overfitting status) and formats JSON/Markdown summary reports.

---

## 4. VERIFICATION & REPRODUCIBILITY

1. **Zero Look-Ahead Guarantee:** Backtest simulations pass slice `candles[:i+1]` to decision evaluation functions, preventing future candle access.
2. **Deterministic Output:** Rerunning optimization runs with identical commit SHA, dataset, parameters, and splits produces identical PnL, trade counts, and objective scores.
