# YarTrader Final Intelligence Architecture

This document describes the unified, canonical production architecture of YarTrader's multi-layered cognitive intelligence system.

---

## 1. Canonical Runtime Flow

All intelligence processes follow exactly **ONE unidirectional execution path**, strictly aligned with clean APES-FIN standards:

```
  [Market Ingest]
         ↓
  [Research Layer]   (Indicator compilation & Pure price action structure)
         ↓
  [Strategy Layer]   (Evaluation of concept suitability & score cand)
         ↓
  [Risk Layer]       (Enforces exposure limits and correlation heat)
         ↓
  [Decision Layer]   (Advanced multi-factor reasoning, XAI summary)
         ↓
  [Learning Layer]   (Feedback analysis, trends, lookback tuning)
         ↓
  [History Store]    (Recorded to cumulative Experience Databases)
```

There are **no competing alternative production pathways**. Simple operations and advanced shadow modes share the exact same upstream logical steps, ensuring complete consistency.

---

## 2. DI Resolution

Dependency injection is managed cleanly via `src/Infrastructure/DI/registrations.py`:
*   `IDecisionEngine` resolves strictly to `AdvancedDecisionEngine` (pointing to `src.Decision.Intelligence.engine.DecisionEngine`).
*   Duplicate old decision classes under `src/Decision/Engine/engine.py` are now thin compatibility wrappers that delegate directly to the canonical engine, eliminating dual execution logic.

---

## 3. Shadow Mode Flow

Shadow Mode orchestrates the unified intelligence pipeline:
1.  Initiates standard `PipelineContext` mapping to a virtual portfolio.
2.  Invokes `IntelligencePipeline.execute_advanced()`.
3.  Evaluates structural changes, resting liquidity pools, sweeps, and Order Blocks.
4.  Processes outcome evaluations to feed parameters back into the local optimization loop.
5.  Persists session states into isolation databases under `runtime_logs/`.

---

## 4. Learning Flow

1.  **Mathematical feedback loops:** Decision outcomes are audited by a classic mathematical parameter optimizer.
2.  **No Neural networks:** Contains strictly 0.0% machine learning weights, neural nets, or speculative prediction models. All calculations are fully explainable, deterministic statistical matrices.
3.  **Optimization Suggestion:** Produces suggestions (such as adjusting max single asset exposure thresholds or expansion of lookback windows) on request-driven triggers.

---

## 5. Worker Architecture

*   **`ResearchWorker` (Enabled):** Polling thread executing MetaTrader5 or Crypto provider analytics every 60 seconds.
*   **`ShadowWorker` (Enabled):** Tracks open simulated positions and updates SL/TP triggers.
*   **`IntelligenceWorker` (DEPRECATED & DECOUPLED):** Background thread completely removed from active service host orchestration. Intelligence calculations are strictly request-driven or event-driven.

---

## 6. Safety Boundaries

*   **Read-Only/Simulation Only:** MT5 orders placement is mocked or deactivated (read-only MT5 stream). Zero actual BUY/SELL broker requests exist.
*   **Leverage Constraints:** Leverage checks are enforced at both Risk and Decision layer boundaries.
*   **Execution Leakage Prevention:** Built-in validation ensures no execution signals ever escape the isolated local sandbox.

---

## 7. Public/Internal Branding Boundary

*   **Public Branding (YarTrader):** Strictly displays the product name `YarTrader` across all web headers, meta structures, login panels, and locales.
*   **Internal Identity (TradeYar):** Preserves `tradeyar_ai`, `TradeYarRuntime`, and associated variables within internal packages, file-paths, and databases to guarantee zero circular dependency or path-finding regressions.
