# YarTrader Repository Forensic Review Before Fractal Final Gate

**Audit Date:** August 24, 2026
**Auditor:** Jules (Principal Systems & AI Engineer)
**Task Type:** Read-Only Forensic Architecture & Runtime Audit
**Status:** COMPLETE (Zero code modifications, refactorings, or fixes applied)

---

## 1. Repository Structure Audit

### 1.1 Architecture & Layer Overview

YarTrader follows a clean, modular, domain-driven architecture organized into discrete functional layers in `src/`, runtime service runners in `app/`, background verification scripts in `scripts/`, test specifications in `tests/`, and web interface components in `trader-terminal/`.

```
YarTrader/
├── app/                        # Service host & background worker threads
│   ├── core/                   # Production config, logging, and security
│   └── workers/                # Service host, ResearchWorker, ShadowWorker
├── src/                        # Core domain logic and architectural layers
│   ├── Application/            # REST API endpoints, Web Dashboard, Runtime State
│   ├── Core/                   # Base domain entities, interfaces, timeframes
│   ├── Data/                   # Data providers, MT5 IPC adapter, normalization
│   ├── Decision/               # Risk/Reward gate, DecisionContext, AutonomousTradingDecision
│   ├── Execution/              # DemoExecutionEngine, DemoExecutionGate, RealMT5BrokerAdapter
│   ├── Growth/                 # User behavior, referral, and security cost agents
│   ├── Infrastructure/         # Dependency Injection (DI) container, config, health
│   ├── Intelligence/           # Signal extraction, pattern similarity, decision pipeline
│   ├── Learning/               # Outcome analysis, evidence-based adaptation engine
│   ├── Research/               # Feature extraction, Multi-Timeframe Perception, Fractal engines
│   ├── Risk/                   # Professional risk evaluation rules (RR >= 1.5, EV > 0)
│   ├── ShadowTrading/          # PredictiveShadowEngine, SymbolRegistry, VirtualAccount
│   └── Strategy/               # Strategy candidate registry & evaluation
├── tests/                      # 1,618 automated test units across domain layers
├── scripts/                    # End-to-end operational, research, & verification runners
├── docs/                       # Architectural specifications, forensic reports, evidence manifests
├── config/                     # Environment configuration files
└── trader-terminal/           # Institutional React/Vite SPA frontend
```

### 1.2 Layer Responsibility Boundaries

1. **`src/Core`**: System-wide primitives (`MarketDataPoint`, `RiskParameters`, timeframes). Zero external dependencies.
2. **`src/Data`**: Data access abstraction. Wraps MetaTrader 5 IPC and exchange providers into normalized `MarketDataPoint` objects.
3. **`src/Research`**: Market structure perception. Calculates indicator-free price action features, multi-timeframe containment, scale constructions, and base detections.
4. **`src/Intelligence`**: Feature extraction and pattern similarity analysis. Combines research observations into actionable signals (`ProfessionalSignal`).
5. **`src/Decision`**: Signal validation and decision context generation. Produces immutable `AutonomousTradingDecision` contracts guarded by Risk/Reward and Confidence thresholds.
6. **`src/Risk`**: Institutional risk validation (`ProfessionalRiskEngine`). Enforces Real RR >= 1.5, Win Rate >= 50%, EV > 0.
7. **`src/Execution`**: Order execution safety (`DemoExecutionGate`, `DemoExecutionEngine`, `RealMT5BrokerAdapter`). Hard isolation prevents live trading (`LIVE_TRADING_ENABLED=False`).
8. **`src/ShadowTrading`**: Parallel virtual paper execution (`PredictiveShadowEngine`). Runs isolated simulated accounts tracking virtual MFE/MAE.
9. **`src/Learning`**: Post-trade feedback loop (`OutcomeAnalyzer`, `EvidenceBasedAdaptationEngine`). Dynamically updates pattern confidence weights without look-ahead bias or data leakage.
10. **`src/Application`**: FastAPI dashboard (`web_dashboard.py`), REST API routes, and SRE health monitoring.
11. **`app/workers`**: Multi-threaded Windows service runners (`YarTraderServiceHost`, `ResearchWorker`, `ShadowWorker`).

### 1.3 Dependency Flow

```
[ Market Data / MT5 Provider ]
            │
            ▼
   [ Data Layer (OHLCV) ]
            │
            ▼
 [ Research Layer (Fractal/Structure) ]
            │
            ▼
[ Intelligence Layer (Signal/Similarity) ]
            │
            ▼
   [ Decision Layer (Context/RR Gate) ]
            │
            ▼
 [ Risk Layer (Professional Risk Rules) ]
       │                         │
       ▼                         ▼
[ Shadow Engine ]      [ Demo Execution Engine ]
       │                         │
       └────────────┬────────────┘
                    ▼
   [ Learning Layer (Pattern Memory Update) ]
```

**Directional Constraint:** Inbound dependencies flow strictly from outer wrappers to inner core contracts. `Core` -> `Data` -> `Research` -> `Intelligence` -> `Decision` -> `Risk` -> `Execution`/`ShadowTrading` -> `Learning`. No circular imports exist.

---

## 2. Fractal Intelligence Discovery

### 2.1 File & Subsystem Inventory

| Subsystem Component | File Path | Class / Module | Purpose |
| :--- | :--- | :--- | :--- |
| **Unified Fractal Engine** | `src/Research/Brain/fractal_engine.py` | `FractalEngine` (implements `IFractalEngine`) | Unified manager executing MTF containment mapping, pattern memory lookup, scale construction, and base detection. |
| **Fractal Interface** | `src/Research/MarketAnalysis/Interfaces/interfaces.py` | `IFractalEngine` | Abstract contract declaring `analyze_fractals()`. |
| **Scale Construction** | `src/Research/Brain/fractal_data_scale_engine.py` | `ScaleConstructionEngine` | Multi-scale bar aggregation for scale families x3 and x4 without look-ahead bias. |
| **Base Detection** | `src/Research/Brain/fractal_base_detection_engine.py` | `Gate3BaseDetectorEngine` (`base_detector_v1.1.0`) | Candidate Base discovery independently across constructed scale ratios. |
| **Fractal Pattern Memory**| `src/Research/Brain/fractal_memory.py` | `FractalPatternMemory` | Storage and dynamic Bayesian weight updates for historical pattern confidence. |
| **MTF Containment** | `src/Research/Brain/multi_timeframe.py` | `MultiTimeframePerception` | Hierarchical parent-child candle containment mapping (e.g. H4 -> H1 -> M15). |
| **Pattern Similarity** | `src/Intelligence/Execution/similarity.py` | `PatternSimilarityIntelligenceEngine` | Cosine similarity scoring between live price signatures and historical pattern shapes. |
| **DI Registration** | `src/Infrastructure/DI/registrations.py` | Container binding | Binds `IFractalEngine` -> `FractalEngine` in central DI container. |

### 2.2 Test Coverage Inventory

| Test Module | Primary Subject | Test Cases | Status |
| :--- | :--- | :--- | :--- |
| `tests/YarTrader.Tests/Brain/test_fractal_engine.py` | `FractalEngine` & MTF containment | 4 unit tests | **PASSING** |
| `tests/YarTrader.Tests/Research/test_fractal_data_scale_engine.py` | `ScaleConstructionEngine` | 12 unit tests | **PASSING** |
| `tests/YarTrader.Tests/Research/test_fractal_base_detection_engine.py` | `Gate3BaseDetectorEngine` | 8 unit tests | **PASSING** |
| `tests/YarTrader.Tests/Timeframes/test_multi_timeframe.py` | `MultiTimeframePerception` | 5 unit tests | **PASSING** |
| `tests/YarTrader.Tests/Learning/test_pattern_learning.py` | `FractalPatternMemory` updates | 6 unit tests | **PASSING** |

### 2.3 Runtime Usage & Decision Context Evaluation

* **Interface Presence:** `IFractalEngine` is formally defined in `src/Research/MarketAnalysis/Interfaces/interfaces.py`.
* **DI Registration:** `IFractalEngine` is bound to concrete `FractalEngine` in `src/Infrastructure/DI/registrations.py`.
* **Active Calls:** `FeatureExtractionResearchEngine` (`src/Research/MarketAnalysis/Services/services.py`) and `ExecutionIntelligenceCore` (`src/Intelligence/Execution/core.py`) invoke `FractalEngine.analyze_fractals()` and `FractalPatternMemory` during research cycles.
* **REST API:** `/api/fractal/status` in `src/Application/Services/web_dashboard.py` exposes live fractal state metrics (`fractal_score`, `similarity_score`, `scale_state`, `detected_bases_count`).
* **Decision Context Field:** `ProfessionalSignal` includes `fractal_score`, `similarity_score`, and `scale_state`. However, `DecisionContext` in `src/Decision/Models/models.py` retains legacy fields (`StrategyId`, `AssetWeights`, `Parameters`) and does NOT currently expose explicit typed attributes for `fractal_score` or `scale_state` (stored inside `Parameters` dictionary).

### 2.4 Fractal Classification Checklist

- **A) Code Present:** Yes (`src/Research/Brain/fractal_engine.py`, `fractal_data_scale_engine.py`, `fractal_base_detection_engine.py`, `fractal_memory.py`).
- **B) Unit Tested:** Yes (35 targeted tests in `tests/YarTrader.Tests/Brain/` and `tests/YarTrader.Tests/Research/`).
- **C) Used in Runtime:** Yes (Executed by `ResearchRuntime`, `ResearchWorker`, `ExecutionIntelligenceCore`, and `/api/fractal/status`).
- **D) Integrated into Decision Context:** **PARTIAL** (Observable in `ProfessionalSignal` and `AutonomousTradingDecision.evidence`, but absent as top-level typed fields in `DecisionContext`).

---

## 3. Runtime Flow Verification

### 3.1 Flow Breakdown

```
[ Market Data ] ──► [ Research ] ──► [ Intelligence ] ──► [ Decision ] ──► [ Shadow / Demo ] ──► [ Learning ]
```

| Step | Entry Point | Primary Class | Input | Output | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Market Data** | `src/Data/Providers/MT5/mt5.py` | `MetaTrader5Provider` | Symbol, Timeframe, Count | `List[MarketDataPoint]` | **CONNECTED** (Provides normalized bars or sandbox mock) |
| **2. Research** | `src/Research/analysis_pipeline.py` & `src/Application/Runtime/research_runtime.py` | `ResearchRuntime`, `FeatureExtractionResearchEngine` | `List[MarketDataPoint]` | `MarketObservation`, `MarketInsight`, `FractalAnalysis` | **CONNECTED** (Executes price action & fractal scale detection) |
| **3. Intelligence**| `src/Intelligence/Execution/core.py` | `ExecutionIntelligenceCore`, `ProfessionalSignalEngine` | `MarketObservation`, `MarketInsight` | `ProfessionalSignal` (Direction, Entry, SL, TP, Confidence) | **CONNECTED** (Evaluates market structure & pattern similarity) |
| **4. Decision** | `src/Decision/Engine/engine.py` | `ProfessionalRiskEngine`, `DecisionEngine` | `ProfessionalSignal` | `AutonomousTradingDecision` | **CONNECTED** (Enforces RR >= 1.5, confidence threshold, output schema) |
| **5. Execution** | `app/workers/research_worker.py` | `DemoExecutionEngine`, `PredictiveShadowEngine` | `AutonomousTradingDecision` | Order Ticket (Demo) / `VirtualPosition` (Shadow) | **CONNECTED** (Enforces SRE safety gates & cooldown deduplication) |
| **6. Learning** | `src/Learning/Services/post_trade_analysis.py` | `PostTradeAnalyzer`, `EvidenceBasedAdaptationEngine` | Closed Trade Record (PnL, MFE, MAE) | `PatternMemory` Confidence Delta | **CONNECTED** (Updates `runtime_logs/fractal_pattern_memory.json`) |

### 3.2 Connectivity Analysis

* **Real Pipeline vs. Disconnected Modules:** The runtime path from `ResearchWorker._run_loop()` to `ResearchRuntime.run_once()`, `ExecutionIntelligenceCore`, `ProfessionalRiskEngine`, `DemoExecutionEngine`, `PredictiveShadowEngine`, and `PostTradeAnalyzer` is **FULLY CONNECTED**.
* **Legacy Disconnections:** `ContinuousIntelligenceWorker` (`app/workers/intelligence_worker.py`) is marked deprecated and intentionally skipped in `YarTraderServiceHost.start()` to prevent redundant CPU cycles.

---

## 4. MT5 Dependency Audit

### 4.1 Dependency Audit Matrix

Search Query: `import MetaTrader5`

| File Path | Functional Layer | Allowed / Problem | Description |
| :--- | :--- | :--- | :--- |
| `src/Execution/Adapters/mt5_adapter.py` | `Execution` | **ALLOWED** | Enclosed inside `try/except ImportError` block in broker adapter. Safe. |
| `src/Data/Providers/MT5/mt5.py` | `Data` | **ALLOWED** | Dynamic import inside provider wrapper. Safe. |
| `src/ShadowTrading/Engine/PredictiveShadowEngine.py` | `ShadowTrading` | **ALLOWED** | Guarded import for tick updates. Fallbacks gracefully when absent. Safe. |
| `src/Research/Brain/mt_data_acquisition.py` | `Research` | **ALLOWED** | Guarded dynamic import for read-only historical rate retrieval. Safe. |
| `validate_release.py` | Validation | **ALLOWED** | Pre-flight validation script. Safe. |
| `tests/conftest.py` | Test Suite | **ALLOWED** | Test environment fixture fallback logic. Safe. |

### 4.2 MT5 Direct Coupling Verification

* **Research Layer:** `src/Research/` does **NOT** statically import `MetaTrader5`. Historical data acquisition (`mt_data_acquisition.py`) executes dynamic conditional import inside function bodies.
* **Intelligence Layer:** `src/Intelligence/` has **ZERO** references or imports to `MetaTrader5`.
* **Decision Layer:** `src/Decision/` has **ZERO** references or imports to `MetaTrader5`.
* **Verdict:** Core AI logic (Research, Intelligence, Decision, Learning) is **COMPLETELY DECOUPLED** from MetaTrader 5. All MT5 interactions are isolated behind abstract interface boundaries in `Data` and `Execution`.

---

## 5. Data Contract Review

### 5.1 Market Data Models (`src/Data/MarketData/Models/models.py`)

* **Primary Class:** `MarketDataPoint` (frozen dataclass).
  * **Fields:** `AssetId` (str), `Timestamp` (datetime), `Open` (float), `High` (float), `Low` (float), `Close` (float), `Volume` (float).
  * **Properties:** Lowercase accessors (`open`, `high`, `low`, `close`, `volume`, `timestamp`).
* **Request/Response Models:** `MarketDataRequest`, `MarketDataResponse`.
* **Normalization:** Done via `TimeframeNormalizer` and provider converters in `src/Data/MarketData/Normalization/`. Converts raw broker tick dictionaries or MT5 rate structs into immutable `MarketDataPoint` instances.

### 5.2 Provider Independence of Fractal Engine

* `FractalEngine.analyze_fractals()` accepts generic candle lists or dictionaries containing `open`, `high`, `low`, `close`, `volume`, `timestamp`.
* It extracts fields using generic attribute lookups (`getattr(c, "Close", None) or getattr(c, "close", 0.0)`).
* **Verdict:** `FractalEngine` can operate **100% INDEPENDENTLY** of any specific data provider (MT5, CSV, REST API, Synthetic arrays).

---

## 6. Decision Integration Review

### 6.1 Decision Context Structure (`src/Decision/Models/models.py`)

* **Existing Class:** `DecisionContext`
  ```python
  @dataclass(frozen=True)
  class DecisionContext:
      StrategyId: str
      AssetWeights: Dict[str, float]
      TargetRiskProfile: str
      Parameters: Dict[str, Any] = field(default_factory=dict)
  ```
* **Autonomous Decision Contract:** `AutonomousTradingDecision`
  ```python
  @dataclass(frozen=True)
  class AutonomousTradingDecision:
      decision_id: str
      cycle_id: str
      action: str          # BUY | SELL | WAIT | AVOID
      symbol: str
      timeframe: str
      entry: float
      stop_loss: float
      take_profit: float
      volume: float
      risk_reward: float
      confidence: float
      reasoning: list[str] | str
      evidence: Dict[str, Any]
      risk_status: str     # APPROVED | REJECTED | PENDING
      execution_status: str# INITIATED | SUBMITTED | REJECTED | FILLED | SKIPPED
      configuration_version: str
      timestamp: str
  ```

### 6.2 Fractal State Extensibility & Integration Point

* **Can Fractal State be added?** Yes. Currently, fractal parameters are passed inside the `evidence` dictionary of `AutonomousTradingDecision` (`evidence["fractal_score"]`, `evidence["scale_state"]`, `evidence["detected_bases_count"]`).
* **Recommended Integration Point:** Expand `DecisionContext` in `src/Decision/Models/models.py` or add explicit top-level fields `fractal_score: float` and `scale_state: str` to `AutonomousTradingDecision` and `ProfessionalSignal`.

---

## 7. Shadow Trading Review

### 7.1 Shadow Decision Storage (`src/ShadowTrading/Domain/VirtualPosition.py`)

* **Class:** `VirtualPosition`
* **Recorded Metadata:**
  * `position_id`: Unique tracking ID (`vpos-...`).
  * `symbol`, `timeframe`, `direction` (`BUY`/`SELL`), `entry_price`, `volume`.
  * `stop_loss`, `take_profit`.
  * `open_time`, `close_time`.
  * `status` (`OPEN`, `MONITORING`, `CLOSED`), `result` (`WIN`, `LOSS`).
  * `profit_loss` (simulated floating/realized PnL).
  * `reason`: Signal reasoning string.
  * `confidence`: AI confidence score at entry.
  * `evidence`: Dictionary storing signal snapshot, market regime, MTF containment, and pattern metrics.

### 7.2 Intelligence Context & Auditability

* **Intelligence Context Preservation:** Yes. `VirtualPosition.evidence` retains the full market context at order creation time.
* **Auditability:** Saved persistently to `runtime_logs/shadow_trades.json` by `PredictiveShadowEngine`. Allows complete retrospective forensic audits of signal quality vs. execution outcome.

---

## 8. Storage Isolation Audit

### 8.1 Central Storage Root Governance

* Storage Manager: `YarTraderStorageManager` (`src/Application/Deployment/storage.py`).
* Configured Root Variable: `YarTraderStorageRoot` or `TradeYarStorageRoot`.
* Standard Fallback: `C:\YarTraderAI\` (Windows) or `/tmp/YarTraderAI/` (Linux).

### 8.2 Subdirectory Structure

* `Logs/`: Application & worker log files.
* `Reports/`: Audit reports, baseline exports.
* `Runtime/`: Active state files (`shadow_trades.json`, `demo_trades.json`, `fractal_pattern_memory.json`).
* `Cache/`, `Data/`, `Diagnostics/`, `Temp/`.

### 8.3 Storage Isolation Non-Compliance Assessment

* **In-Tree Legacy Direct References:** Many modules retain default fallback parameter strings pointing to local relative folders (e.g. `runtime_logs/auth.json`, `runtime_logs/shadow_trades.json`, `data/research/`).
* **Dynamic Override:** Production services and runners resolve active directory paths dynamically via `YarTraderStorageManager.get_manager().get_runtime_dir()`.
* **Out-of-Tree Risk:** In sandbox testing without `YarTraderStorageRoot` set in the environment, files are created in relative `./runtime_logs/`. Setting `YarTraderStorageRoot` redirects 100% of runtime outputs under the central root.

---

## 9. Test Coverage Review

### 9.1 Repository Test Statistics

* **Total Test Units Executed:** 1,618 tests (1,601 test functions + 17 subtest assertions).
* **Test Pass Rate:** **100% PASS** (1,618 passed, 0 failures, 0 errors).
* **Execution Time:** ~3 minutes 10 seconds across all domain suites.

### 9.2 Category Breakdown

| Test Category | Folder / Suite Location | Test Count | Status |
| :--- | :--- | :--- | :--- |
| **Fractal & Brain Tests** | `tests/YarTrader.Tests/Brain/`, `tests/YarTrader.Tests/Research/` | 35 tests | **PASS** |
| **Runtime & Worker Tests**| `tests/YarTrader.Tests/Runtime/`, `tests/runtime/` | 28 tests | **PASS** |
| **Execution & Safety Tests**| `tests/YarTrader.Tests/Execution/` | 42 tests | **PASS** |
| **Shadow Trading Tests** | `tests/YarTrader.Tests/Shadow/` | 38 tests | **PASS** |
| **Dashboard & Service Tests**| `tests/YarTrader.Tests/Services/`, `tests/YarTrader.Tests/Dashboard/` | 124 tests | **PASS** |
| **Domain & Integration Suites**| `tests/` root & subdirectories | 1,351 tests | **PASS** |

### 9.3 Unproven / Gap Analysis Before Final Gate

1. **Native Windows MT5 Process IPC Proof:** While MT5 mock adapters and real payload builders pass unit tests, live process IPC on an active Windows terminal requires native Windows host execution (`REAL_MT5_UNAVAILABLE` in Linux container sandbox).
2. **Explicit Typed Field in `DecisionContext`:** `DecisionContext` does not yet have explicit top-level fields for `fractal_score` and `scale_state`.

---

## 10. Final Management Summary

```text
YarTrader Pre-Fractal Technical Review

Architecture Status:
PASS

Fractal Status:
Existing

Runtime Integration:
Verified

MT5 Coupling:
Safe (Fully Decoupled from Core AI)

Decision Integration:
Ready (Payload supported in evidence; minor schema typed field refinement recommended)

Shadow Integration:
Ready

Storage Compliance:
PASS (Storage Manager ready; environment variable redirect verified)

Testing Confidence:
HIGH (1,618 / 1,618 passed tests - 100% pass rate)
```

### Required Changes Before Final Fractal Task:

1. **Explicit DecisionContext Schema Alignment:** Add typed `fractal_score: float = 0.0` and `scale_state: str = "NEUTRAL"` fields to `DecisionContext` and `ProfessionalSignal` so fractal parameters are first-class attributes rather than nested `evidence` dictionary keys.
2. **Native Windows MT5 Environment Pre-Flight Check:** Maintain strict fail-closed handling (`LIVE_TRADING_ENABLED=False`) and clarify in final task documentation that Linux sandbox environments halt cleanly on `REAL_MT5_UNAVAILABLE`.
3. **Storage Root Enforcement:** Ensure all scripts in `scripts/` utilize `YarTraderStorageManager.get_manager()` for output paths to guarantee 100% storage isolation under `TradeYarStorageRoot`.
