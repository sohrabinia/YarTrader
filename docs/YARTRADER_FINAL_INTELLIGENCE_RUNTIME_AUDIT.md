# YarTrader Final Intelligence Runtime Audit

This document records the strict technical audit of YarTrader's intelligence, decision, pipeline, worker, and learning architectures prior to consolidation.

---

## A. Runtime Entry Points

1. **Production Service Host:** `app/workers/service.py`
   - Orchestrates background workers (`ResearchWorker`, `ShadowWorker`, and formerly `IntelligenceWorker`) and launches the FastAPI Web Management Server on a background thread. Supports Windows Service integration.
2. **FastAPI Web Server:** `src/Application/Services/web_dashboard.py`
   - Spawns the main web server, hosts the public/admin/user routers, serves React SPA assets, and maintains a passive `run_research_background_loop` thread for continuous symbol polling (60s interval).
3. **Acceptance CLI Runner:** `validate_release.py`
   - Used by SRE pipelines to run automated testing suites and output persistent JSON reports.

---

## B. Intelligence Entry Points

*   **Research:** Triggered by `ResearchRuntime.run_once()` in `src/Application/Runtime/research_runtime.py`, continuous symbol thread polling in `web_dashboard.py`, and `IntelligencePipeline.execute() / execute_advanced()`.
*   **Strategy:** Evaluated via `StrategyEvaluator.evaluate()` in `src/Strategy/Evaluation/evaluation.py` on strategy candidates.
*   **Risk:** Analyzed by `RiskAnalyzer.analyze_risk()` in `src/Risk/Services/services.py`.
*   **Decision:** Finalized using `IDecisionEngine` evaluations during pipeline iterations and sandbox scenarios.
*   **Learning:** Triggered by feedback processing loops: `LearningProcessor.process_feedback()` and `AdvancedLearningProcessor.process_feedback_record()`.
*   **Shadow:** Driven by `ShadowModeEngine.execute_tick()` in `src/Application/Shadow/engine.py` on periodic heartbeats.

---

## C. Decision Engine Inventory

| Engine | File | Interface | Direct Callers | DI Registration | Runtime Usage | Test Usage | Production Status | Keep/Merge/Compatibility/Remove Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`AutonomousDecisionEngine`** | `src/Decision/engine.py` | `IDecisionService` | None (direct) | None | Passive asset scoring ranking | `tests/test_decision.py` | Experimental / Legacy | **Keep as a thin compatibility/adapter class** |
| **`DecisionEngine`** | `src/Decision/Engine/engine.py` | `IDecisionEngine` | `DecisionReasoningFramework` | None | Basic leverage constraint check | `tests/test_platform_integration.py`, `tests/test_integration_and_production.py` | Legacy Production Path | **Consolidate! Replace duplicate implementation with alias pointing to the canonical Advanced DecisionEngine** |
| **`DecisionEngine`** | `src/Decision/Intelligence/engine.py` | `IDecisionEngine` | `IntelligencePipeline.execute_advanced()`, `ShadowModeEngine` | `IDecisionEngine` -> `AdvancedDecisionEngine` | Full context-aware reasoning, validation, quality and conflict resolving | Many tests in `tests/TRADEYAR_AI.Tests` | **Canonical Production Path** | **Keep as Single Canonical Decision Engine** |

---

## D. Pipeline Inventory

*   `execute(context)`: Used by legacy simulation scripts and unit tests. Relies on simple `evaluate_decision()`.
*   `execute_advanced(context)`: Used by Shadow Mode and advanced cognitive testing suites. Relies on multi-factor `evaluate_intelligence_context()`.
*   *Consolidation Strategy:* Extracted steps 1–4 (Data acquisition, Research, Strategy, Risk checks) into a single private helper `_execute_common_steps` to eliminate any duplicated pipeline logic.

---

## E. Worker Inventory

1. **`ResearchWorker` (Active):** Periodic Gold/Crypto MT5 analysis thread.
2. **`ShadowWorker` (Active):** Handles Virtual Accounts and position tracking loops.
3. **`IntelligenceWorker` (Deprecated):** Obsolete periodic loop thread. Does not perform real intelligence operations; it merely sleeps and logs status. Will be deprecated and removed from runtime startup.

---

## F. DI Inventory

*   `IDecisionEngine` maps to `AdvancedDecisionEngine` (aliasing `src.Decision.Intelligence.engine.DecisionEngine`) as registered inside `src/Infrastructure/DI/registrations.py`. No hidden alternative decision engines are registered in the DI container.

---

## G. Learning Inventory

*   `LearningProcessor` (`src/Learning/Services/services.py`): Performs standard mathematical parameter optimization.
*   `AdvancedLearningProcessor` (`src/Learning/Optimization/services.py`): Examines quality, deviation, and provides lookback suggestions.
*   They are complementary. Standard optimization handles simple exposure boundaries, whereas advanced optimization produces deep explainable parameter logs. Both are used in `execute_advanced()`.

---

## H. Shadow Inventory

*   **Verified:** Shadow Mode operates strictly read-only and simulation-only, enforcing `SimulationMode = True`. No order placement or broker transactions exist.

---

## I. Branding Inventory

*   **Public Brand:** Strictly consolidated to `YarTrader` across all HTML metadata, browser titles, pricing cards, locales, and user-facing dashboards.
*   **Internal Identity:** Technical identifiers (`tradeyar_ai`, `TradeYarRuntime`, `TRADEYAR_SERVICE_RUN`, etc.) are left completely untouched to prevent circular imports or system crash regressions.
