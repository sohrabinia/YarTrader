# YARTRADER FORENSIC REPORT — GATE 2: CANONICAL 30-UNIVERSE & INDICATOR-FREE DECISION PATH

```text
BASE_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
MERGE_BASE_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
ORIGIN_MAIN_SHA: be56259dec65516fa237ebf2536c7138ea98e0d1
AUDITED_IMPLEMENTATION_HEAD_SHA: b59b5cd99029b625d8cbf767bcb97ab85960e9f9
REPORT_PARENT_SHA: b59b5cd99029b625d8cbf767bcb97ab85960e9f9
REPORT_GENERATED_AT_UTC: 2026-09-25 21:30:00 UTC
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
- Duplicate Key Detection: `parse_market_universe_yaml` in `SymbolRegistry.py` maintains a `seen_symbols` set during parsing and raises `ValueError("Duplicate symbol key '...' detected in market_universe configuration!")` if a duplicate key exists in `market_universe.yaml`, preventing silent dictionary key overwrites.
- Set Equality Enforcement: `_validate_canonical_30_invariant(symbols_dict)` enforces strict set equality (`loaded_symbols == CANONICAL_30_SYMBOLS`). If missing symbols, extra symbols, or non-matching symbols exist, `SymbolRegistry` raises `ValueError` / `RuntimeError` and fails closed.
- End-to-End Worker Safety: `ResearchWorker._get_active_matrix()` returns `[]` on registry failure, causing `ResearchWorker._run_loop()` to skip all cycles without generating research requests or trading proposals.

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

## 5. DUPLICATE CORE EVALUATION REMEDIATION (BEFORE vs. AFTER)

### Before Remediation
```text
ResearchWorker._run_loop()
  └─► ResearchRuntime.run_once()
        ├─► PrimitiveMarketResearchEngine.analyze_market()
        │     └─► LiveAnalysisBrain.process_live_candle()
        │     └─► ExecutionIntelligenceCore.evaluate_context()  [Invocation #1]
        │           └─► ExecutionIntelligencePlanner
        │
        └─► ResearchRuntime.run_once() (Block 6b)
              └─► ExecutionIntelligenceCore.evaluate_context()  [Invocation #2 - DUPLICATE]
                    └─► ExecutionIntelligencePlanner
```

### After Remediation
```text
ResearchWorker._run_loop()
  └─► ResearchRuntime.run_once()
        └─► PrimitiveMarketResearchEngine.analyze_market()
              ├─► LiveAnalysisBrain.process_live_candle()
              └─► ExecutionIntelligenceCore.evaluate_context()  [SINGLE CANONICAL INVOCATION]
                    └─► ExecutionIntelligencePlanner
                          └─► AutonomousTradingDecision (Single Proposal)
```

Block 6b in `ResearchRuntime.run_once()` was cleanly removed. `ResearchRuntime` consumes the single canonical `autonomous_decision` and `intel_summary` generated inside `PrimitiveMarketResearchEngine.analyze_market()`. `ExecutionIntelligenceCore.evaluate_context()` is invoked exactly ONCE per research cycle, as verified by `test_case_n_duplicate_core_invocation_eliminated`.

---

## 6. FULL INDICATOR SEARCH INVENTORY & CLASSIFICATION

Repository-wide search for `RSI`, `ATR`, `SMA`, `EMA`, `MACD`, `Bollinger`, `ADX`, `Stochastic`, `CCI`:

| Component / Path | Classification | Justification |
| :--- | :--- | :--- |
| `PrimitiveMarketResearchEngine` (`src/Research/MarketAnalysis/Services/services.py`) | **A. CANONICAL EXECUTABLE** | Default engine invoked in production worker path; uses 0 technical indicators. |
| `ExecutionIntelligenceCore` (`src/Intelligence/Execution/core.py`) | **A. CANONICAL EXECUTABLE** | Orchestrates market narrative, liquidity, zones, alignment, similarity, portfolio, strategy, and planner; uses 0 technical indicators. |
| `ExecutionIntelligencePlanner` (`src/Intelligence/Execution/execution_planner.py`) | **A. CANONICAL EXECUTABLE** | Formulates proposal parameters; uses 0 technical indicators. |
| `LiveAnalysisBrain` (`src/Research/Brain/live_brain.py`) | **A. CANONICAL EXECUTABLE** | Single decision authority; uses 0 technical indicators. |
| `StrategyOrchestrator` (`src/Intelligence/Execution/strategy_orchestrator.py`) | **A. CANONICAL EXECUTABLE** | Evaluates 6 strategy profiles on raw price structure; uses 0 technical indicators. Candidate outputs are non-authoritative. |
| `FeatureExtractionResearchEngine` (`src/Research/MarketAnalysis/Services/services.py`) | **B. NON-CANONICAL LEGACY** | Preserved for explicit opt-in legacy consumers; bypassed by default production path. |
| `TechnicalAnalysisEngine` (`src/Research/analysis_pipeline.py`) | **B. NON-CANONICAL LEGACY** | Bypassed by `PrimitiveMarketResearchEngine`. |
| `TechnicalAnalyzer` (`src/Research/analyzers.py`) | **E. DEAD / UNREACHABLE** | Historical utility functions not invoked in runtime loop. |
| `MarketSessionEngine` (`src/Execution/Services/market_session_engine.py`) | **B. NON-CANONICAL LEGACY** | String comments in TP feasibility docstrings. |
| `ProfessionalSignalEngine` (`src/Decision/Intelligence/professional_signal_engine.py`) | **B. NON-CANONICAL LEGACY** | Isolated advisory engine; disconnected from research worker loop. |

**Canonical Executable Path Status: 100% INDICATOR FREE.**

---

## 7. DECISION AUTHORITY & BRAIN CAUSALITY ANALYSIS

- Single Conceptual Brain: `LiveAnalysisBrain` (`src/Research/Brain/live_brain.py`).
- Brain Causality: `ExecutionIntelligencePlanner` transforms and validates `LiveAnalysisBrain` proposals.
- Proof of Causality:
  - If `newborn_brain_report` is missing or `brain_available = False`, `planner` outputs `action = "WAIT"` with `decision_source = "BRAIN_UNAVAILABLE"`.
  - If Brain proposes `WAIT` or `AVOID`, final canonical decision MUST be `WAIT` or `AVOID`.
  - If Brain proposes `BUY` or `SELL` with contradicting market structure, final canonical decision defaults to `WAIT`.
  - Downstream components (`StrategyOrchestrator`, `ExecutionIntelligencePlanner`, etc.) CANNOT independently manufacture `BUY` or `SELL` without an explicit `BUY`/`SELL` proposal from `LiveAnalysisBrain`.

---

## 8. EXECUTION SEPARATION

- `LiveAnalysisBrain`, `PrimitiveMarketResearchEngine`, `ResearchRuntime`, and `ExecutionIntelligencePlanner` contain 0 order execution methods (`order_send`, `execute_demo_decision`, etc.).
- Order dispatch occurs strictly downstream in `ResearchWorker._run_loop()` under fail-closed safety gates (`AUTONOMOUS_DEMO_TRADING_ENABLED`, 0.5% risk limit, daily loss kill switch, RR threshold, cooldown).

---

## 9. EXACT FOCUSED TEST COMMANDS AND OUTPUT

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
collecting ... collected 15 items

tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_a_exact_canonical_30_universe PASSED [  6%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_b_missing_symbol_fails_closed PASSED [ 13%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_c_extra_symbol_fails_closed PASSED [ 20%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_d_malformed_universe_fails_closed PASSED [ 26%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_e_duplicate_configuration_entry_fails_closed PASSED [ 33%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_f_real_worker_path_reaches_canonical_brain PASSED [ 40%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_g_all_9_forbidden_indicators_zero_calls PASSED [ 46%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_h_no_brain_proposal_fails_closed_to_wait PASSED [ 53%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_i_brain_wait_cannot_become_buy_or_sell PASSED [ 60%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_j_brain_avoid_cannot_become_buy_or_sell PASSED [ 66%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_k_brain_buy_incompatible_structure_defaults_to_wait PASSED [ 73%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_l_brain_sell_incompatible_structure_defaults_to_wait PASSED [ 80%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_m_strategy_orchestrator_cannot_override_brain PASSED [ 86%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_n_duplicate_core_invocation_eliminated PASSED [ 93%]
tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py::TestGate2UniverseAndIndicatorFree::test_case_o_brain_and_research_layer_cannot_execute_orders PASSED [100%]

============================== 15 passed in 0.84s ==============================
```

---

## 10. EXACT FULL-SUITE COMMAND AND OUTPUT

```bash
python3 -m pytest -v
```

```text
===== 1948 passed, 1253 warnings, 17 subtests passed in 279.33s (0:04:39) ======
```

---

## 11. GIT DIFF STATISTICS

```text
 app/workers/research_worker.py                                          |   2 +-
 config/market_universe.yaml                                             |  40 +++---
 src/Application/Runtime/research_runtime.py                           |  87 -------------
 src/ShadowTrading/Engine/SymbolRegistry.py                             |  20 ++-
 tests/YarTrader.Tests/Gate2/test_gate2_universe_and_indicator_free.py  | 305 ++++++++++++++++++++++++++++++++++++++++++++
 tests/YarTrader.Tests/Universe/test_data_boundary_and_memory.py        |  10 +-
 6 files changed, 347 insertions(+), 117 deletions(-)
```

---

## 12. DEFERRED GATE 3 FINDINGS

- Position risk percentages, daily loss kill switch thresholds, Risk/Reward minimums, DEMO/LIVE trading policies, and broker execution credentials remain untouched for Gate 3 evaluation.

---

## 13. FINAL REMEDIATION STATUS SUMMARY

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

GATE 2 REMEDIATION COMPLETE — PR #309 OPEN — AWAITING CTO FORENSIC REVIEW.
