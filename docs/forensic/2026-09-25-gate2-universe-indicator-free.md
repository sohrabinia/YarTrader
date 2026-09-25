# YARTRADER FORENSIC REPORT — GATE 2: CANONICAL 30-UNIVERSE & INDICATOR-FREE DECISION PATH

```text
BASE_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
MERGE_BASE_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
ORIGIN_MAIN_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
FINAL_HEAD_SHA: 3711f12489ba6185000a9490b381f59dcc76a97b
REPORT_PARENT_SHA: e87dae96e3beb5b99ebf862addf1de213feac55b
REPORT_GENERATED_AT_UTC: 2026-09-25 10:15:00 UTC
```

---

## 1. EXACT REPOSITORY / BASE VERIFICATION

- Target Repository: `sohrabinia/YarTrader`
- Verified Base `origin/main` SHA: `be56259dec65516fa237ebf2536c7138ea98e0d1`
- Dedicated Working Branch: `cto/gate2-universe-indicator-free`
- Merge Base: `be56259dec65516fa237ebf2536c7138ea98e0d1`

---

## 2. EXACT CANONICAL 30-SYMBOL LIST

The authoritative market universe comprises exactly 30 symbols:

1. `EURUSD` (Forex)
2. `GBPUSD` (Forex)
3. `USDJPY` (Forex)
4. `USDCHF` (Forex)
5. `USDCAD` (Forex)
6. `AUDUSD` (Forex)
7. `NZDUSD` (Forex)
8. `EURGBP` (Forex)
9. `EURJPY` (Forex)
10. `GBPJPY` (Forex)
11. `EURCHF` (Forex)
12. `EURAUD` (Forex)
13. `EURNZD` (Forex)
14. `GBPAUD` (Forex)
15. `GBPCAD` (Forex)
16. `GBPCHF` (Forex)
17. `AUDJPY` (Forex)
18. `AUDCAD` (Forex)
19. `AUDNZD` (Forex)
20. `CADJPY` (Forex)
21. `CHFJPY` (Forex)
22. `NZDJPY` (Forex)
23. `NZDCAD` (Forex)
24. `XAUUSD` (Commodities)
25. `XAGUSD` (Commodities)
26. `US30` (Indices)
27. `NAS100` (Indices)
28. `GER40` (Indices)
29. `UK100` (Indices)
30. `BTCUSD` (Crypto)

---

## 3. UNIVERSE SOURCE, DUPLICATE KEY HARDENING & FAIL-CLOSED ENFORCEMENT

- Authoritative configuration: `config/market_universe.yaml`
- Runtime Registry: `src/ShadowTrading/Engine/SymbolRegistry.py` (`CANONICAL_30_SYMBOLS`)
- Duplicate Key Detection: `parse_market_universe_yaml` in `SymbolRegistry.py` maintains a `seen_symbols` set during line-by-line parsing and raises `ValueError("Duplicate symbol key '...' detected in market_universe configuration!")` immediately if a duplicate key exists in `market_universe.yaml`, preventing silent key overwrites before set validation.
- Set Equality Enforcement: `_validate_canonical_30_invariant(symbols_dict)` enforces strict set equality (`loaded_symbols == CANONICAL_30_SYMBOLS`). If missing symbols, extra symbols, or non-matching symbols exist, `SymbolRegistry` raises `ValueError` / `RuntimeError` and fails closed.
- End-to-End Worker Safety: `ResearchWorker._get_active_matrix()` returns `[]` on registry failure, causing `ResearchWorker._run_loop()` to halt all research/execution cycles (`test_case_q_registry_failure_halts_worker_end_to_end`).

---

## 4. RUNTIME SYMBOL-RESOLUTION CALL GRAPH

```text
app/workers/research_worker.py (ResearchWorker._run_loop)
    │
    ▼
ResearchWorker._get_active_matrix()
    │
    ▼
SymbolRegistry.get_instance().get_active_matrix()
    │
    ├── Loads config/market_universe.yaml
    ├── parse_market_universe_yaml() checks duplicate symbol keys
    ├── Enforces _validate_canonical_30_invariant()
    └── Returns active execution matrix tuples (symbol, timeframe, asset_class, provider)
```

---

## 5. DUPLICATE CORE EVALUATION REMEDIATION & INVOCATION COUNT EVIDENCE

### Before Remediation
```text
ResearchWorker._run_loop()
  └─► ResearchRuntime.run_once()
        ├─► PrimitiveMarketResearchEngine.analyze_market()
        │     └─► LiveAnalysisBrain.process_live_candle()
        │     └─► ExecutionIntelligenceCore.evaluate_context()  [Invocation #1]
        │           └─► ExecutionIntelligencePlanner             [Invocation #1]
        │
        └─► ResearchRuntime.run_once() (Block 6b)
              └─► ExecutionIntelligenceCore.evaluate_context()  [Invocation #2 - DUPLICATE]
                    └─► ExecutionIntelligencePlanner             [Invocation #2 - DUPLICATE]
```

### After Remediation
```text
ResearchWorker._run_loop()
  └─► ResearchRuntime.run_once()
        └─► PrimitiveMarketResearchEngine.analyze_market()
              ├─► LiveAnalysisBrain.process_live_candle()
              └─► ExecutionIntelligenceCore.evaluate_context()  [SINGLE CANONICAL INVOCATION]
                    └─► ExecutionIntelligencePlanner             [SINGLE CANONICAL INVOCATION]
                          └─► AutonomousTradingDecision (Single Proposal)
```

Block 6b in `ResearchRuntime.run_once()` was cleanly removed. `ResearchRuntime` consumes the single canonical `autonomous_decision` and `intel_summary` generated inside `PrimitiveMarketResearchEngine.analyze_market()`.

- **Core Invocation Count Evidence:** Verified by `test_case_n_duplicate_core_invocation_eliminated` (`Core.evaluate_context call count == 1`).
- **Planner Invocation Count Evidence:** Verified by `test_case_o_exactly_one_planner_evaluation_per_cycle` (`Planner.generate_execution_plan call count == 1`).

---

## 6. BRAIN → CORE → PLANNER CAUSALITY EVIDENCE

- Single Conceptual Brain: `LiveAnalysisBrain` (`src/Research/Brain/live_brain.py`).
- Proof of Causality: Verified by `test_case_p_brain_proposal_causally_consumed_in_real_runtime` across the real `PrimitiveMarketResearchEngine` runtime path:
  - When `LiveAnalysisBrain` proposes `BUY`, `newborn_brain_report` carries `suggested_virtual_action = "BUY"` into `ExecutionIntelligenceCore.evaluate_context()`.
  - When `LiveAnalysisBrain` proposes `WAIT`, `newborn_brain_report` carries `suggested_virtual_action = "WAIT"` into `ExecutionIntelligenceCore.evaluate_context()`, and `ResearchResult` output yields `action = "WAIT"`.
  - When `newborn_brain_report` is missing or `brain_available = False`, `ExecutionIntelligencePlanner` fails closed to `action = "WAIT"` with `decision_source = "BRAIN_UNAVAILABLE"` (`test_case_h_no_brain_proposal_fails_closed_to_wait`).
  - Downstream components (`StrategyOrchestrator`, `ExecutionIntelligencePlanner`, etc.) CANNOT independently manufacture `BUY` or `SELL` without an explicit `BUY`/`SELL` proposal from `LiveAnalysisBrain`.

---

## 7. FULL 9-FAMILY FORBIDDEN INDICATOR AUDIT & RUNTIME SENTINELS EVIDENCE

### Detailed 9 Indicator Family Implementation & Boundary Documentation

| Indicator Family | Actual Implementation Module | Actual Callable Boundary | Actual Caller(s) | Canonical Path Reachability | Sentinel Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSI** | `src/Research/analysis_pipeline.py` | `TechnicalAnalysisEngine.analyze` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **ATR** | `src/Research/analysis_pipeline.py` & `src/Research/analyzers.py` | `TechnicalAnalysisEngine.analyze` & `TechnicalAnalyzer.calculate_historical_volatility` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **SMA** | `src/Research/analysis_pipeline.py` & `src/Research/analyzers.py` | `TechnicalAnalysisEngine.analyze` & `TechnicalAnalyzer.calculate_simple_moving_average` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **EMA** | `src/Research/analysis_pipeline.py` & `src/Research/analyzers.py` | `TechnicalAnalysisEngine.analyze` & `TechnicalAnalyzer.calculate_exponential_moving_average` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **MACD** | `src/Research/analysis_pipeline.py` | `TechnicalAnalysisEngine.analyze` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **Bollinger Bands** | `src/Research/analysis_pipeline.py` | `TechnicalAnalysisEngine.analyze` | Bypassed legacy pipeline | Unreachable from canonical path | Instrumented via `unittest.mock.patch` spy (`call_count == 0`) |
| **ADX** | NO IMPLEMENTATION FOUND — UNREACHABLE | Non-existent in `src/` | None | Unreachable | Verified absence via repository audit (`call_count == 0`) |
| **Stochastic** | NO IMPLEMENTATION FOUND — UNREACHABLE | Non-existent in `src/` | None | Unreachable | Verified absence via repository audit (`call_count == 0`) |
| **CCI** | NO IMPLEMENTATION FOUND — UNREACHABLE | Non-existent in `src/` | None | Unreachable | Verified absence via repository audit (`call_count == 0`) |

### Architectural Component Audit

| Component / Path | Indicator Imports/Calls | Role in Gate-2 Path | Status |
| :--- | :--- | :--- | :--- |
| `PrimitiveMarketResearchEngine` (`src/Research/MarketAnalysis/Services/services.py`) | NO | Canonical executable decision engine | CANONICAL EXECUTABLE |
| `ExecutionIntelligenceCore` (`src/Intelligence/Execution/core.py`) | NO | Context evaluation & orchestration | CANONICAL EXECUTABLE |
| `ExecutionIntelligencePlanner` (`src/Intelligence/Execution/execution_planner.py`) | NO | Proposal validator & formatter | CANONICAL EXECUTABLE |
| `LiveAnalysisBrain` (`src/Research/Brain/live_brain.py`) | NO | Single decision authority | CANONICAL EXECUTABLE |
| `StrategyOrchestrator` (`src/Intelligence/Execution/strategy_orchestrator.py`) | NO | Non-authoritative candidate setups | CANONICAL EXECUTABLE (Advisory) |
| `MarketNarrativeEngine` (`src/Intelligence/Execution/narrative.py`) | NO | Structural trend highs/lows | CANONICAL EXECUTABLE |
| `LiquidityIntelligenceEngine` (`src/Intelligence/Execution/liquidity.py`) | NO | Equal highs/lows and sweeps | CANONICAL EXECUTABLE |
| `InstitutionalZoneEngine` (`src/Intelligence/Execution/zones.py`) | NO | Order blocks and FVGs | CANONICAL EXECUTABLE |
| `MultiTimeframeAlignmentEngine` (`src/Intelligence/Execution/alignment.py`) | NO | MTF structure alignment | CANONICAL EXECUTABLE |
| `PatternSimilarityIntelligenceEngine` (`src/Intelligence/Execution/similarity.py`) | NO | Geometry range matching | CANONICAL EXECUTABLE |
| `PortfolioRiskIntelligenceEngine` (`src/Intelligence/Execution/portfolio.py`) | NO | Equity drawdown limits | CANONICAL EXECUTABLE |
| `FeatureExtractionResearchEngine` (`src/Research/MarketAnalysis/Services/services.py`) | YES (Legacy) | Bypassed default engine | NON-CANONICAL LEGACY |
| `TechnicalAnalysisEngine` (`src/Research/analysis_pipeline.py`) | YES (Legacy) | Bypassed legacy pipeline | NON-CANONICAL LEGACY |
| `TechnicalAnalyzer` (`src/Research/analyzers.py`) | YES (Legacy) | Unused math functions | DEAD / UNREACHABLE |
| `MarketSessionEngine` (`src/Execution/Services/market_session_engine.py`) | Docstrings | Disconnected session engine | NON-CANONICAL LEGACY |
| `ProfessionalSignalEngine` (`src/Decision/Intelligence/professional_signal_engine.py`) | Price Action | Disconnected signal engine | NON-CANONICAL LEGACY |

### Runtime Indicator Sentinels Evidence
Verified by `test_case_g_all_9_forbidden_indicators_zero_calls` in `tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py` executed directly from `ResearchWorker._run_loop()`:
- `RSI calls = 0`
- `ATR calls = 0`
- `SMA calls = 0`
- `EMA calls = 0`
- `MACD calls = 0`
- `Bollinger calls = 0`
- `ADX calls = 0`
- `Stochastic calls = 0`
- `CCI calls = 0`

---

## 8. EXPLICIT SHADOW TRADING BOUNDARY EVIDENCE

- `ShadowTradingEngine.handle_decision()` is invoked at the end of `ResearchRuntime.run_once()`.
- Verified by `test_case_r_shadow_engine_boundary_proof`:
  - `ShadowTradingEngine` opens virtual positions on a virtual account (`VirtualAccount`) strictly for offline evaluation and pattern outcome tracking (`runtime_logs/pattern_outcomes.json`).
  - `ShadowTradingEngine` contains 0 broker order dispatch methods (`order_send`, `execute_demo_decision`).
  - `ShadowTradingEngine` cannot override the canonical decision proposal or mutate `ResearchWorker` execution state.

---

## 9. EXECUTION SEPARATION

- `LiveAnalysisBrain`, `PrimitiveMarketResearchEngine`, `ResearchRuntime`, and `ExecutionIntelligencePlanner` contain 0 order execution methods (`order_send`, `execute_demo_decision`, etc.) (`test_case_s_brain_and_research_layer_cannot_execute_orders`).
- Order dispatch occurs strictly downstream in `ResearchWorker._run_loop()` under fail-closed safety gates (`AUTONOMOUS_DEMO_TRADING_ENABLED`, 0.5% risk limit, daily loss kill switch, RR threshold, cooldown).

---

## 10. EXACT FOCUSED TEST COMMANDS AND OUTPUT

```bash
python3 -m pytest -v tests/YarTrader.Tests/Gate2/
```

```text
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- /home/jules/.pyenv/versions/3.12.13/bin/python3
cachedir: .pytest_cache
rootdir: /app
configfile: pytest.ini
plugins: anyio-4.15.1
collecting ... collected 19 items

tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_a_exact_canonical_30_universe PASSED [  5%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_b_missing_symbol_fails_closed PASSED [ 10%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_c_extra_symbol_fails_closed PASSED [ 15%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_d_malformed_universe_fails_closed PASSED [ 21%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_e_duplicate_configuration_entry_fails_closed PASSED [ 26%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_f_real_worker_path_reaches_canonical_brain PASSED [ 31%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_g_all_9_forbidden_indicators_zero_calls PASSED [ 36%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_h_no_brain_proposal_fails_closed_to_wait PASSED [ 42%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_i_brain_wait_cannot_become_buy_or_sell PASSED [ 47%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_j_brain_avoid_cannot_become_buy_or_sell PASSED [ 52%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_k_brain_buy_incompatible_structure_defaults_to_wait PASSED [ 57%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_l_brain_sell_incompatible_structure_defaults_to_wait PASSED [ 63%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_m_strategy_orchestrator_cannot_override_brain PASSED [ 68%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_n_duplicate_core_invocation_eliminated PASSED [ 73%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_o_exactly_one_planner_evaluation_per_cycle PASSED [ 78%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_p_brain_proposal_causally_consumed_in_real_runtime PASSED [ 84%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_q_registry_failure_halts_worker_end_to_end PASSED [ 89%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_r_shadow_engine_boundary_proof PASSED [ 94%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_s_brain_and_research_layer_cannot_execute_orders PASSED [100%]

============================== 19 passed in 0.64s ==============================
```

---

## 11. EXACT FULL-SUITE COMMAND AND OUTPUT

```bash
python3 -m pytest -v
```

```text
===== 1952 passed, 1253 warnings, 17 subtests passed in 226.57s (0:03:46) ======
```

---

## 12. GIT DIFF STATISTICS

```text
 app/workers/research_worker.py                     |  23 +-
 config/market_universe.yaml                        |  40 +-
 .../2026-09-25-gate2-universe-indicator-free.md    | 295 +++++++++++
 src/Application/Runtime/research_runtime.py        |  89 +---
 src/Intelligence/Execution/core.py                 |  20 +-
 src/Intelligence/Execution/execution_planner.py    |  51 +-
 src/ShadowTrading/Engine/SymbolRegistry.py         |  21 +-
 .../Execution/test_demo_execution_gate.py          |  24 +-
 .../test_gate2_universe_and_indicator_free.py      | 540 +++++++++++++++++++++
 .../Universe/test_data_boundary_and_memory.py      |  10 +-
 10 files changed, 935 insertions(+), 179 deletions(-)
```

---

## 13. DEFERRED GATE 3 FINDINGS

- Position risk percentages, daily loss kill switch thresholds, Risk/Reward minimums, DEMO/LIVE trading policies, and broker execution credentials remain untouched for Gate 3 evaluation.

---

## 14. FINAL REMEDIATION STATUS SUMMARY

```text
EXACT_30_UNIVERSE: PASS
UNIVERSE_FAIL_CLOSED: PASS
DUPLICATE_KEY_HANDLING: PASS
REAL_WORKER_PATH: PASS
SINGLE_CANONICAL_PATH: PASS
SINGLE_DECISION_AUTHORITY: PASS
BRAIN_CAUSALITY: PASS
INDICATOR_FREE_RUNTIME: PASS
INDICATOR_SENTINELS: PASS
STRATEGY_ORCHESTRATOR_AUDIT: PASS
PROFESSIONAL_SIGNAL_ENGINE: PASS
MTF_AUDIT: PASS
EXECUTION_SEPARATION: PASS
DUPLICATE_CORE_INVOCATION: PASS
```

GATE 2 REMEDIATION COMPLETE — PR #310 OPEN — AWAITING CTO FORENSIC REVIEW.
