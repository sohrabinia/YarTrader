# TRADEYAR Strategy Framework

The Strategy Intelligence Framework manages strategy concept definitions, registration workflows, and qualitative suitability evaluations.

---

## 1. Strategy Framework Mission

The core mission of the Strategy Framework is to:
* **Evaluate Concept Candidates:** Rate StrategyCandidates across active qualitative dimensions (Stability, Complexity, Data Intensity, and Risk Compatibility).
* **Compare Concepts:** Select the most suitable strategy configurations cleanly from a candidate pool (`StrategyEvaluationFramework`).
* **Manage Registries:** Record approved concepts under the `StrategyRegistry` for selection by downstream engines.

---

## 2. Decoupling from Trading Signals

This framework does **NOT** generate BUY/SELL orders or entry/exit triggers:
* It outputs an overall quality score rating for a conceptual profile.
* It does not evaluate real-time leverage, margin limits, or position sizes.
