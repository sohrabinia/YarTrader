# TRADEYAR Decision Framework

The Decision Intelligence Framework integrates strategy rankings, research outputs, and risk assessments to produce formalized allocation decision results.

---

## 1. Decision Framework Mission

The core mission of the Decision Framework is to:
* **Synthesize Complex Inputs:** Merge Research, Strategy, and Risk audits into a single DecisionResult.
* **Determine Valid System States:** Map inputs to four clean, non-trading states: Approved, Rejected, ReviewRequired, and NoAction.
* **Explain Decision Reasoning:** Document logical justifications and confidence metrics (`DecisionReasoningFramework`).

---

## 2. Decision Logic Separation

Unlike trading bots that emit BUY/SELL execution signals, the Decision Engine is a **passive planner**:
* It establishes target portfolio allocation weights.
* It contains zero stop-loss, take-profit, or entry/exit triggers.
