# TRADEYAR Decision Intelligence Layer Foundation

The Decision Intelligence Layer is the logical orchestrator of the TRADEYAR Autonomous Financial Intelligence Platform. It aggregates strategy rankings and risk audits to finalize standardized target portfolio allocations without generating buy/sell trading signals.

---

## 1. Decision Intelligence Mission

The core mission of the Decision Layer is to:
* **Synthesize Inputs:** Read descriptive strategy candidate rankings and risk profile assessments to formulate a final target model.
* **Determine Valid Workflow States:** Classify decision contexts into strictly non-execution states (`Approved`, `Rejected`, `ReviewRequired`, `NoAction`).
* **Guarantee Strict Decoupling:** Prevent the leak of order placement or trading automation rules into the core decision logic.

---

## 2. Decision States

The engine maps all contexts to four valid, non-trading states:

* **Approved:** The recommended allocation meets all strategy requirements and fully satisfies risk tolerance profiles.
* **Rejected:** The recommended allocation violates leverage, exposure, or volatility constraints.
* **ReviewRequired:** The allocation fits basic rules but features moderate risk markers, requiring human audit or multi-signature verification.
* **NoAction:** Asset scores are too low, or prices are unavailable, so no changes are recommended (maintain current allocations or cash).

---

## 3. Separation from Trading Automation

Unlike traditional trading bots that generate reactive "BUY/SELL" signals, the TRADEYAR Decision Engine is a **passive planner**:
* It produces a structural `DecisionResult` documenting target asset weights and logical reasoning.
* It does not calculate trigger prices, track real-time position sizes, or execute orders on active exchange connections.

---

## 4. Future Extension Points

* **Voting & Consensus Engine:** Easily combine multiple strategy candidate scores using consensus voting algorithms under `IDecisionEngine`.
* **Multi-Signature Handlers:** Integrate review flows where decisions flagged with `ReviewRequired` trigger email or webhook alerts for administrator review.
