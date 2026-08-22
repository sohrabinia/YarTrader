# YarTrader Autonomous Trading Forensic Audit Report

**Date:** 2026-08-22
**Audit Scope:** Autonomous Demo Trading Pipeline, Single Source of Truth, Decision Contract, Risk & Safety Gates, Order Execution, Position Lifecycle, Trade Journal, Learning Engine, Data Leakage & Sample Size Protections, Dashboard Truthfulness, and Storage Compliance.

---

## 1. System Component Classification Matrix

| Component | File Location | Forensic Classification | Audit Findings & Evidence |
| :--- | :--- | :--- | :--- |
| **Research Runtime** | `src/Application/Runtime/research_runtime.py` | **WORKING (EXTEND)** | Successfully fetches real candles, calculates features via `FeatureExtractionResearchEngine`, updates `PredictiveShadowEngine`, and outputs snapshots. Needs direct integration with `ExecutionIntelligenceCore`. |
| **Research Worker** | `app/workers/research_worker.py` | **PARTIAL (EXTEND)** | Polling loop operates continuously across registered symbols x timeframes. Currently uses legacy `signals` dictionary from `Findings` instead of routing through `ExecutionIntelligenceCore` / `ExecutionIntelligencePlanner`. |
| **Execution Intelligence Core** | `src/Intelligence/Execution/core.py` | **WORKING (EXTEND)** | Coordinates Narrative, Liquidity, Zones, Alignment, Similarity, and Portfolio Risk. Produces advisory plan via `ExecutionIntelligencePlanner`. |
| **Execution Intelligence Planner** | `src/Intelligence/Execution/execution_planner.py` | **WORKING (EXTEND)** | Synthesizes technical parameters and portfolio risk to emit `BUY`, `SELL`, `WAIT`, `AVOID` advisory plans. |
| **Decision Intelligence Engine** | `src/Decision/Intelligence/engine.py` | **WORKING (EXTEND)** | Advanced context-aware Decision Intelligence Engine. `src/Decision/engine.py` delegates dynamically to this engine. |
| **Decision Contract / Models** | `src/Decision/Models/models.py` | **PARTIAL (EXTEND)** | Contains basic decision models. Requires standard `AutonomousTradingDecision` contract supporting `decision_id`, `cycle_id`, `action`, `entry`, `stop_loss`, `take_profit`, `volume`, `risk_reward`, `confidence`, `reasoning`, `evidence`, `risk_status`, `execution_status`, `configuration_version`, and `timestamp`. |
| **Demo Execution Engine** | `src/Execution/Services/demo_execution_engine.py` | **WORKING (EXTEND)** | Executes demo decisions on `RealMT5BrokerAdapter` strictly after passing `DemoExecutionGate`. Writes execution telemetry to storage. |
| **Demo Execution Gate** | `src/Execution/Safety/demo_execution_gate.py` | **WORKING (EXTEND)** | Enforces all 9 SRE DEMO safety rules. Fails closed if MT5 terminal is disconnected or non-DEMO. |
| **MetaTrader Safety Gate** | `src/Execution/Safety/safety_gate.py` | **WORKING (REUSE)** | Hard-blocks MT5 Live and MT4 Demo operations while `LIVE_TRADING_ENABLED=False`. |
| **Real MT5 Broker Adapter** | `src/Execution/Adapters/mt5_adapter.py` | **WORKING (REUSE)** | Encapsulates native MT5 IPC calls (`account_info`, `order_check`, `order_send`). |
| **Pattern Memory** | `src/Research/Brain/fractal_memory.py` | **WORKING (EXTEND)** | `FractalPatternMemory` stores and updates pattern frequency, wins/losses, success rate, and confidence weights. |
| **Learning Processor** | `src/Learning/Services/services.py` | **PARTIAL (EXTEND)** | `LearningFramework` processes feedback and outputs suggestions. Requires explicit data leakage protection, sample size protection, versioning, and rollback mechanisms. |
| **Trade Journal** | `runtime_logs/shadow_trades.json` | **PARTIAL (UNIFY)** | Currently records shadow trades. Needs unified immutable Trade Journal for DEMO execution with MFE/MAE excursion tracking. |
| **Dashboard Web Services** | `src/Application/Services/web_dashboard.py` | **WORKING (EXTEND)** | Serves dashboard APIs (`/api/v1/dashboard`, `/api/demo/state`, `/api/shadow/metrics`). Emits null-safe truthful statuses when data is unavailable. |
| **Storage Manager** | `src/Application/Deployment/storage.py` | **WORKING (REUSE)** | `YarTraderStorageManager` strictly roots all logs, runtime files, snapshots, and reports under `TradeYarStorageRoot`. |

---

## 2. Identified Architecture Gaps & Disconnections

1. **Disconnected Decision Brain in Autonomous Loop (Root Cause):**
   `ResearchWorker` evaluates actionable signals using `res.Findings.get("pipeline_outputs", {}).get("signals", {})` instead of executing `ExecutionIntelligenceCore.evaluate_context()` and `ExecutionIntelligencePlanner.generate_execution_plan()`. This creates a path disconnection between the core intelligence engine and order dispatching.

2. **Incomplete Decision Contract Serialization:**
   Decisions dispatched to `DemoExecutionEngine` rely on ad-hoc parameters rather than an immutable, traceable `AutonomousTradingDecision` instance with a unique `cycle_id` and `decision_id`.

3. **Order Check & Retcode Handling Refinement:**
   `DemoExecutionEngine` must explicitly perform `adapter.order_check()` prior to `order_send()`, classify MT5 return codes (e.g. `10018 MARKET_CLOSED`, `10013 INVALID_STOPS`, `10014 INVALID_VOLUME`), and treat `10018 MARKET_CLOSED` as a safe market rejection rather than a system failure.

4. **Data Leakage & Sample Size Protections in Learning:**
   The learning adaptation path must enforce:
   - **Sample Size Gate:** Require `minimum_learning_sample_size` (N >= 5) before permitting parameter adaptation; single trade outcomes remain in `OBSERVE_ONLY` mode.
   - **Data Leakage Protection:** Ensure features and decisions use strict snapshot timestamps (`decision_timestamp`) so post-trade metrics cannot pollute past research contexts.
   - **Safety Boundary Isolation:** Strictly prohibit learning algorithms from modifying live trading flags (`LIVE_TRADING_ENABLED`), safety gates (`DemoExecutionGate`, `MetaTraderSafetyGate`), or Kill Switches (`autonomous_demo_trading_enabled`).

5. **Kill Switch & Autonomous Loop Controls:**
   Need an immediate, auditable Kill Switch flag (`autonomous_demo_trading_enabled = False`) that halts autonomous execution instantly while maintaining research monitoring.

---

## 3. Minimal Dependency-Ordered Implementation Plan

1. **Contract Standardisation:** Enhance `AutonomousTradingDecision` in `src/Decision/Models/models.py`.
2. **Unified Decision Source:** Update `ResearchRuntime` and `ResearchWorker` to evaluate signals via `ExecutionIntelligenceCore` and `ExecutionIntelligencePlanner`.
3. **Decision & Risk Gates:** Implement comprehensive pre-order validation (RR >= minimum_rr, confidence >= minimum_confidence, portfolio risk, duplicate check, cooldown, Kill Switch, MT5 connectivity, DemoExecutionGate).
4. **Order Execution & Retcode Classifier:** Update `DemoExecutionEngine` with pre-check validation and MT5 retcode handling (`10018 MARKET_CLOSED` recovery).
5. **Position Lifecycle & Trade Journal:** Extend position monitoring, SL/TP exit detection, and immutable trade journal persistence with real MFE/MAE calculations.
6. **Outcome Analyzer & Pattern Memory:** Integrate post-trade outcome classification and update `FractalPatternMemory`.
7. **Versioned Learning with Protection Gates:** Implement `LearningEngine` with Data Leakage Protection, Sample Size Protection, Versioned Adaptation, and Rollback support.
8. **Dashboard Truthfulness & Storage Compliance:** Ensure all telemetry routes query live runtime state and resolve paths via `YarTraderStorageManager`.
9. **Verification & Evidence Generation:** Execute tests, pre-commit steps, and generate runtime evidence artifacts.

---

## 4. Final Verdict

Forensic audit complete. Existing working components will be extended and re-wired strictly without rewriting or duplicating working code.
