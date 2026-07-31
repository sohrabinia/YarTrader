# TRADEYAR Scenario Simulation Engine

This document outlines the architecture, scenario lifecycle, pipeline integration, safety guard model, and extension points of the **TRADEYAR Autonomous Scenario Simulation Engine**.

---

## 1. Simulation Architecture

The Simulation Engine provides a fully isolated, offline sandbox to validate the autonomous intelligence pipeline using historical or synthetic market scenarios. It acts as an evaluation harness, observing system behaviors under diverse conditions without placing real-world trades or establishing actual broker/exchange connections.

```
┌──────────────────────────────────────────────────────────────┐
│                      ScenarioRunner                          │
│                                                              │
│  [ Scenario Input ]                                          │
│         │                                                    │
│         ▼                                                    │
│  [ SimulationEnvironmentGuard ] (Enforce Safety)             │
│         │                                                    │
│         ▼                                                    │
│  [ ScenarioMarketDataProvider ] (Serve Price Data)            │
│         │                                                    │
│         ▼                                                    │
│  [ IntelligencePipeline ] ─────────────────────────────────┐ │
│         │                                                  │ │
│         ▼                                                  │ │
│    Decision Result ────► Learning Feedback                 │ │
│         │                                                  │ │
│         ▼                                                  │ │
│  [ ScenarioResult ]                                        │ │
│         │                                                  │ │
│         └──────────────────────────────────────────────────┼─┘
│                                                            │
▼                                                            ▼
[ SimulationReport ]                                [ Execution Blocked ]
(Summarized Audit Trace)                            (If active order attempted)
```

---

## 2. Scenario Lifecycle

The validation process follows a clear state transition lifecycle:

1. **Definition & Loading:** A `MarketScenario` is defined with specific assets, date ranges, types (Trending, Ranging, High Volatility, Low Liquidity, Market Shock), and loaded price data series.
2. **Safety Check Execution:** The `ScenarioRunner` triggers the `SimulationEnvironmentGuard.verify_safety()` to guarantee no active or live mode parameters are configured.
3. **Data Injection:** Price data from the scenario is loaded into a local `ScenarioMarketDataProvider` conforming to the `IMarketDataProvider` contract.
4. **Unidirectional pipeline run:** The orchestration pipeline is executed sequentially using `PipelineContext`, flowing strictly from data, research analysis, strategy, risk limits verification, and decision reasoning to learning feedback.
5. **Telemetry Collection & Processing:** The resulting outputs are captured, and feedback metrics are passed to the mathematical learning processor.
6. **Reporting & Cleanup:** A comprehensive `SimulationReport` is compiled, summarizing findings, rating approvals, and safety preservation logs.

---

## 3. Pipeline Integration

The simulation engine is fully integrated with the APES-FIN clean architecture layers:
* **Data Intelligence Integration:** Ingests pre-loaded or synthetic `MarketDataPoint` series directly into the pipeline through mock provider abstractions.
* **Research & Indicators Verification:** Validates that passive qualitative and mathematical analyzers receive, parse, and score scenario observations correctly.
* **Risk Engine Response:** Tests limits and boundary assertions (e.g. restrictive leverage limits or volatile periods) to ensure that the risk layer responds correctly (approves or blocks target portfolio weights).
* **Decision Synthesis:** Orchestrates decision status approvals, overrides, and confidence scores based on scenario parameters.
* **Continuous Feedback Loops:** Automatically triggers `ILearningEngine` feedback telemetry on the simulation outputs to log drift tracking.

---

## 4. Safety Guard Model

Absolute isolation from financial actions is maintained via a zero-tolerance model:

* **Allowed Operations:**
  * ✅ Processing historical price series (synthetic or real)
  * ✅ Conducting research and indicator evaluation
  * ✅ Generating ratings and strategy suitability scores
  * ✅ Performing portfolio audit calculations
  * ✅ Generating target allocations and reasoning logs
  * ✅ Recording feedback and optimization suggerstions

* **Forbidden Operations (Strictly Intercepted):**
  * ❌ Making actual broker or MT5 client connection attempts
  * ❌ Creating, modifying, or routing trade orders
  * ❌ Performing financial executions or routing to real money environments
  * ❌ Triggering active signals for trading execution

* **SimulationEnvironmentGuard Verification:**
  * If the platform status attempts to execute real-world operations or if `verify_safety()` flags an active execution mode, the guard immediately throws `ExecutionBlockedError`.
  * The guard's `block_active_execution(action)` method blocks transaction routing at the adapter level.

---

## 5. Extension Points

The Scenario Simulation Engine can be modularly extended:
* **Alternative Data Providers:** New scenario formatters can feed historical CSV, JSON, or databases through the `ScenarioMarketDataProvider` interface.
* **Advanced Synthetic Generator:** Dynamic mathematical models (e.g., Brownian motion, mean reverting processes, shock injection engines) can generate scenarios and yield them to the scenario runner.
* **Custom Reporting Formatters:** Different output formats (e.g., JSON, CSV, PDF, or console logs) can be easily plugged into the `generate_report` method for pipeline metrics tracking.
