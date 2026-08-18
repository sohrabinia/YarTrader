# YarTrader Real Execution Reachability Audit

## Executive Conclusion

A comprehensive forensic call-graph analysis of the active production runtime codebase confirms that **the active YarTrader production runtime CANNOT reach `RealMT5BrokerAdapter.send_order_to_broker()` or `mt5.order_send()` under any circumstance**.

`RealMT5BrokerAdapter` and `mt5.order_send()` are **100% unreachable** from the active Windows Service Host (`app/workers/service.py`), `ResearchWorker`, `ShadowWorker`, and web API endpoints (`/api/demo/run`). No dependency injection bindings, dynamic imports, factory handlers, or configuration flags exist that can wire `RealMT5BrokerAdapter` into the active production runtime pipeline.

`RealMT5BrokerAdapter` exists as **DORMANT CODE** in the core application library (`src/Execution/Adapters/mt5_adapter.py`) and is utilized strictly as **TEST_ONLY** infrastructure within standalone validation scripts (`scripts/run_real_mt5_demo_e2e.py`, `scripts/run_mt5_demo_forward.py`, `scripts/run_mt5_forward_observation.py`) and dedicated unit tests (`tests/YarTrader.Tests/Execution/`).

---

## Active Runtime Call Graph

The active 24/7 background runtime is managed by `YarTraderServiceHost` (`app/workers/service.py`), which orchestrates three isolated pathways:

```
Windows Service Process / Console Host
  ├── YarTraderServiceHost.start() [app/workers/service.py:84]
  │     │
  │     ├── [1] ResearchWorker.start() [app/workers/research_worker.py:44]
  │     │     └── ResearchWorker._run_loop() [app/workers/research_worker.py:60]
  │     │           └── ResearchRuntime.run_once() [src/Application/Runtime/research_runtime.py:59]
  │     │                 ├── MetaTrader5Provider.retrieve_market_data() [src/Data/MarketData/Providers/providers.py:82]
  │     │                 │     └── MT5DataProvider.fetch_market_data() [src/Data/Providers/MT5/mt5.py:165] (Read-Only OHLCV Data)
  │     │                 ├── FeatureExtractionResearchEngine.analyze_market() [src/Research/MarketAnalysis/Services/services.py:27]
  │     │                 └── ShadowTradingEngine.handle_decision() [src/ShadowTrading/Engine/ShadowTradingEngine.py:44]
  │     │
  │     ├── [2] ShadowWorker.start() [app/workers/shadow_worker.py:18]
  │     │     └── ShadowWorker._run_loop() [app/workers/shadow_worker.py:32]
  │     │           └── ShadowTradingEngine.tick_update() [src/ShadowTrading/Engine/ShadowTradingEngine.py:155] (In-memory paper balance evaluation)
  │     │
  │     └── [3] Uvicorn FastAPI Web Server [app/workers/service.py:105]
  │           └── FastAPI Routes [src/Application/Services/web_dashboard.py]
  │                 └── POST /api/demo/run [src/Application/Services/web_dashboard.py:4015]
  │                       └── DemoScenarioRunner.run_scenario() [src/Application/Demo/runner.py:82]
  │                             └── Simulated In-Memory Execution (runtime_logs/demo_trades.json)
```

---

## Real Execution Call Graph (Dormant / Standalone Test Only)

The theoretical call path leading to `mt5.order_send()` is fully disconnected from active service startup and HTTP endpoints:

```
[ UNCONNECTED / STANDALONE TEST SCRIPTS ONLY ]
  ├── RealMT5BrokerAdapter [src/Execution/Adapters/mt5_adapter.py:13]
  │     └── send_order_to_broker(request) [src/Execution/Adapters/mt5_adapter.py:164]
  │           ├── verify_safety_and_account(operation_type="DEMO") [src/Execution/Safety/safety_gate.py:50]
  │           │     └── Checks LIVE_TRADING_ENABLED == False
  │           ├── mt5.symbol_info() / mt5.symbol_info_tick()
  │           ├── mt5.order_check(trade_req) [src/Execution/Adapters/mt5_adapter.py:245]
  │           └── mt5.order_send(trade_req) [src/Execution/Adapters/mt5_adapter.py:249]
  │
  └── Invocation Sources (Standalone Validation Scripts & Unit Tests ONLY):
        ├── scripts/run_real_mt5_demo_e2e.py:89 (RealMT5BrokerAdapter(auto_initialize=True))
        ├── scripts/run_mt5_demo_forward.py:44 (RealMT5BrokerAdapter(auto_initialize=True))
        ├── scripts/run_mt5_forward_observation.py:68 (RealMT5BrokerAdapter(auto_initialize=True))
        ├── tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py:27
        └── tests/YarTrader.Tests/Execution/test_real_mt5_adapter.py:13
```

---

## Shadow Execution Call Graph

The Shadow Execution engine operates strictly in memory on virtual paper balances ($10,000 baseline) and has zero connection to broker order APIs:

```
ShadowTradingEngine [src/ShadowTrading/Engine/ShadowTradingEngine.py:15]
  ├── handle_decision() [src/ShadowTrading/Engine/ShadowTradingEngine.py:44]
  │     └── PositionManager.open_virtual_position() [src/ShadowTrading/Engine/PositionManager.py:32]
  │           └── VirtualAccount.add_position() [src/ShadowTrading/Domain/VirtualAccount.py:48]
  │
  ├── update_market_price() [src/ShadowTrading/Engine/ShadowTradingEngine.py:89]
  │     └── PositionManager.update_prices_and_evaluate() [src/ShadowTrading/Engine/PositionManager.py:75]
  │           └── TradeEvaluator.evaluate_and_memorize() [src/ShadowTrading/Services/TradeEvaluator.py:25]
  │                 ├── JudgeBrain.evaluate_trade() [src/Research/Brain/judge.py:40]
  │                 └── MarketMemorySystem.update_memory() [src/Research/Brain/memory.py:65]
  │
  └── Zero Broker Dependencies:
        ├── No import of RealMT5BrokerAdapter
        ├── No import of IBrokerAdapter
        └── No import/call of mt5.order_send()
```

---

## Adapter Instantiation Evidence

A complete scan of every `IBrokerAdapter` implementation across the entire repository reveals:

1. **`RealMT5BrokerAdapter`** (`src/Execution/Adapters/mt5_adapter.py:13`):
   - `src/Execution/Adapters/__init__.py:5` (Export)
   - `src/Execution/__init__.py:7` (Export)
   - `scripts/run_real_mt5_demo_e2e.py:89` (**Instantiated in standalone test script**)
   - `scripts/run_mt5_demo_forward.py:44` (**Instantiated in standalone test script**)
   - `scripts/run_mt5_forward_observation.py:68` (**Instantiated in standalone test script**)
   - `tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py:27, 41` (**Instantiated in unit test**)
   - `tests/YarTrader.Tests/Execution/test_real_mt5_adapter.py:13` (**Instantiated in unit test**)
   - **`src/` or `app/` production runtime: 0 instantiations.**

2. **`MT5AdapterPlaceholder`** (`src/Execution/Adapters/adapters.py:6`):
   - `src/Execution/Adapters/__init__.py:2` (Export)
   - `src/Execution/__init__.py:5` (Export)
   - `tests/test_integration_and_production.py:28` (**Instantiated in integration test**)
   - **`src/` or `app/` production runtime: 0 instantiations.**

3. **`GenericBrokerAdapterPlaceholder`** (`src/Execution/Adapters/adapters.py:22`):
   - `src/Execution/Adapters/__init__.py:3` (Export)
   - `src/Execution/__init__.py:6` (Export)
   - `tests/test_integration_and_production.py:7` (**Imported in integration test**)
   - **`src/` or `app/` production runtime: 0 instantiations.**

---

## `order_send` Reachability Evidence

Every occurrence of `order_send` in the codebase was audited:

- `src/Execution/Adapters/mt5_adapter.py:249`: `res = mt5.order_send(trade_req)` (Direct call inside `RealMT5BrokerAdapter.send_order_to_broker()`).
- `scripts/run_real_mt5_demo_e2e.py:193`: Standalone test evidence logging for MT5 Demo verification.
- `scripts/run_mt5_demo_forward.py:221`: Standalone test evidence logging for MT5 Demo forward operation.
- `tests/YarTrader.Tests/Shadow/test_virtual_capital_safety.py:89`: Safety test asserting `mock_mt5.order_send.call_count == 0`.
- `tests/YarTrader.Tests/Runtime/test_research_runtime.py:284`: Compliance test asserting `order_send` is forbidden in research runtime.

---

## Configuration & Dependency Injection (DI) Analysis

1. **Dependency Injection Registry** (`src/Infrastructure/DI/registrations.py`):
   - Registers `IMarketDataProvider` -> `MetaTrader5Provider`
   - Registers `IResearchEngine` -> `ResearchProcessor`
   - Registers `IStrategyEvaluator` -> `StrategyEvaluator`
   - Registers `IRiskEngine` -> `RiskAnalyzer`
   - Registers `IDecisionEngine` -> `AdvancedDecisionEngine`
   - Registers `ILearningEngine` -> `LearningProcessor`
   - **`IBrokerAdapter` is NOT registered in the DI Container.**

2. **Configuration Settings** (`app/core/config.py`, `src/Infrastructure/Configuration/config.py`):
   - Config contains flags like `workers_research=True`, `workers_intelligence=False`, `workers_shadow=True`.
   - No configuration parameter switches runtime execution mode to real MT5 order submission.
   - `LIVE_TRADING_ENABLED` defaults to `False` across system limits and is hard-enforced by `MetaTraderSafetyGate` (`src/Execution/Safety/safety_gate.py:50`).

3. **Dynamic Import / Reflection Inspection**:
   - Zero use of `importlib`, `getattr`, or string-based reflection to dynamically load `RealMT5BrokerAdapter` or `send_order_to_broker`.

---

## Demo Endpoint Analysis (`/api/demo/run`)

The `/api/demo/run` route defined in `src/Application/Services/web_dashboard.py:4015` behaves as follows:

1. Accepts scenario payload (`scenario_id`, `asset`).
2. Instantiates `DemoScenarioRunner` (`src/Application/Demo/runner.py:82`).
3. Uses `DemoMarketDataProvider` with simulated candle data (`src/Application/Demo/runner.py:38`).
4. Runs through Feature Extraction, Research, Strategy Evaluation, Risk Analysis, Decision Intelligence, Compliance Audit, and Explainability generation.
5. Constructs a simulated trade dictionary (`simulated_trade`) with `mode: "DEMO"` and appends it to `runtime_logs/demo_trades.json` (`src/Application/Services/web_dashboard.py:4050`).
6. **Zero connection to `RealMT5BrokerAdapter`, `IBrokerAdapter`, or `mt5.order_send()`**.

---

## Risk & Path Classification

| Runtime Component / Pathway | Target Method / Module | Assigned Classification | Reachability to `mt5.order_send()` |
| :--- | :--- | :--- | :--- |
| **Windows Service Host** | `app/workers/service.py` | `READ_ONLY_RESEARCH` & `ACTIVE_SHADOW_EXECUTION` | **UNREACHABLE (0%)** |
| **ResearchWorker / ResearchRuntime** | `app/workers/research_worker.py` | `READ_ONLY_RESEARCH` | **UNREACHABLE (0%)** |
| **ShadowWorker / ShadowTradingEngine** | `app/workers/shadow_worker.py` | `ACTIVE_SHADOW_EXECUTION` | **UNREACHABLE (0%)** |
| **Demo Trading Endpoint** | `POST /api/demo/run` | `ACTIVE_SHADOW_EXECUTION` | **UNREACHABLE (0%)** |
| **RealMT5BrokerAdapter Class** | `src/Execution/Adapters/mt5_adapter.py` | `DORMANT_CODE` | **UNREACHABLE from 24/7 service** |
| **Standalone Demo Validation Scripts** | `scripts/run_real_mt5_demo_e2e.py` | `TEST_ONLY` | Reachable strictly in manual CLI runs under SRE Safety Gate |

---

## Exact Files + Line Numbers Matrix

- **Service Entrypoint**: `app/workers/service.py` (lines 84, 105, 155)
- **Research Worker**: `app/workers/research_worker.py` (lines 44, 60, 100)
- **Research Runtime**: `src/Application/Runtime/research_runtime.py` (lines 59, 100, 138)
- **Read-Only MT5 Data Provider**: `src/Data/MarketData/Providers/providers.py` (line 82)
- **Read-Only MT5 Terminal Connector**: `src/Data/Providers/MT5/mt5.py` (line 165)
- **Shadow Trading Worker**: `app/workers/shadow_worker.py` (lines 18, 32)
- **Shadow Trading Engine**: `src/ShadowTrading/Engine/ShadowTradingEngine.py` (lines 15, 44, 89, 155)
- **Demo Endpoint Route**: `src/Application/Services/web_dashboard.py` (line 4015)
- **Demo Scenario Runner**: `src/Application/Demo/runner.py` (lines 38, 82)
- **DI Service Registration**: `src/Infrastructure/DI/registrations.py` (lines 18–50)
- **Real MT5 Broker Adapter**: `src/Execution/Adapters/mt5_adapter.py` (lines 13, 164, 249)
- **MetaTrader Safety Gate**: `src/Execution/Safety/safety_gate.py` (line 50)

---

## Answers to Required Questions

### A. Can the currently running Windows Service invoke `mt5.order_send()`?
**NO.** The Windows Service Host (`app/workers/service.py`) starts `ResearchWorker`, `ShadowWorker`, and FastAPI. None of these components instantiate `RealMT5BrokerAdapter` or invoke `mt5.order_send()`.

### B. Can `ResearchWorker` invoke `mt5.order_send()`?
**NO.** `ResearchWorker` delegates strictly to `ResearchRuntime` (`src/Application/Runtime/research_runtime.py`) and `MetaTrader5Provider`, which performs read-only candle data retrieval. It contains zero execution methods or order sending logic.

### C. Can `ShadowWorker` invoke `mt5.order_send()`?
**NO.** `ShadowWorker` delegates strictly to `ShadowTradingEngine` (`src/ShadowTrading/Engine/ShadowTradingEngine.py`), which manages paper accounts and virtual positions entirely in memory. It has zero dependencies on `RealMT5BrokerAdapter` or `mt5.order_send()`.

### D. Can `/api/demo/run` invoke `mt5.order_send()`?
**NO.** `/api/demo/run` delegates to `DemoScenarioRunner` (`src/Application/Demo/runner.py`), which executes in-memory scenario simulations and writes trade records to `runtime_logs/demo_trades.json`. It never instantiates `RealMT5BrokerAdapter` or calls `mt5.order_send()`.

### E. Is `RealMT5BrokerAdapter` instantiated anywhere in production code?
**NO.** `RealMT5BrokerAdapter` is instantiated **0 times** in production application code (`src/` or `app/`). It is instantiated solely in standalone test scripts (`scripts/run_real_mt5_demo_e2e.py`, `scripts/run_mt5_demo_forward.py`, `scripts/run_mt5_forward_observation.py`) and unit tests (`tests/YarTrader.Tests/Execution/`).

### F. Is there any configuration flag capable of switching production runtime to real execution?
**NO.** No configuration setting or environment variable dynamically wires `RealMT5BrokerAdapter` into the production service pipeline or bypasses `MetaTraderSafetyGate`. `LIVE_TRADING_ENABLED` is `False` by default and fail-closed.

### G. Is there any indirect/dynamic import or factory path that bypasses static search?
**NO.** DI registrations in `src/Infrastructure/DI/registrations.py` do not bind `IBrokerAdapter`. No reflection, `getattr`, `importlib`, or factory mechanisms exist that dynamically load or instantiate `RealMT5BrokerAdapter` at runtime.

---

## Git History Analysis

Git log investigation confirms that `RealMT5BrokerAdapter` (`src/Execution/Adapters/mt5_adapter.py`) was introduced as dedicated execution layer infrastructure to support end-to-end MT5 Demo account validation and forward observation testing under strict SRE Safety Gate control (`LIVE_TRADING_ENABLED=False`).

It has **never** been wired into the active 24/7 `YarTraderServiceHost` production runtime, remaining strictly dormant during production server execution while serving standalone MT5 Demo test scripts.

---

## Remaining Unknowns

**NONE.** The call graph trace across static source code, DI containers, worker loops, API routes, configuration files, and git history is 100% complete and verified with repository evidence.

---

## Final Verdict

**REAL EXECUTION REACHABILITY VERDICT: UNREACHABLE (GUARANTEED SAFE)**

The active production runtime is **100% isolated** from real broker execution. `RealMT5BrokerAdapter` and `mt5.order_send()` are completely unreachable from the running Windows Service Host and all web endpoints.
