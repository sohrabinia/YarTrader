# RG_V3 Decision Intelligence Layer (Phase 18)

This documentation presents the architecture, context models, evidence trails, quality scoring models, and safety limits of the Advanced Decision Intelligence Layer.

---

## 1. Core Mission & Design Principles

The **Advanced Decision Intelligence Layer** represents the final analytical synthesis layer within the APES-FIN architecture. Its primary purpose is to integrate market features, research insights, pattern discovery, strategy evaluations, and risk assessments to produce unified, explainable decision context models and reports.

To remain strictly compliant with APES-FIN standards, this layer is **fully passive and non-operational**:
* **No Buy/Sell Action**: It never authorizes, initiates, triggers, or executes trade orders.
* **No Account Access**: It has zero connectivity to brokerage adapters, API endpoints, or transaction handlers.
* **Analytical Classifications Only**: Decision states are descriptive categorization parameters only (Approved, Rejected, ReviewRequired, NoAction, InsufficientData).

---

## 2. Decision Layer Architecture

The advanced decision module resides under `src/Decision/Intelligence/` and is composed of the following components:

1. **`DecisionIntelligenceContext`**: An immutable, frozen context containing structured lists of insights, strategy assessments, and risk evaluations. It implements active keyword scanning to intercept and prevent active transaction data.
2. **`DecisionContextBuilder`**: Normalizes divergent upstream datasets and compiles them into context.
3. **`DecisionAnalyzer`**: Analyzes the structural alignment between strategy scores and research confidence.
4. **`DecisionQualityEvaluator`**: Measures evidence completeness, consistency (e.g. strategy vs. risk bounds compatibility), and reliability.
5. **`DecisionConflictResolver`**: Intercepts and resolves contradictions (e.g., highly confident research with low strategy suitability).
6. **`DecisionEvidenceCollector`**: Collects and seals detailed trail logs to ensure every decision state is fully trace-justified.
7. **`DecisionHistoryRecord`**: Stores local, database-free history tracks of outcomes for future passive parameter optimizations.
8. **`DecisionValidator`**: Acts as a guard, validating context completeness and confidence parameters, failing safely upon detecting contradictions.
9. **`DecisionEngine`**: Orchestrates the entire reasoning lifecycle and creates formalized `DecisionResult` objects.

---

## 3. Decision Quality Scoring

The `DecisionQualityEvaluator` computes a dynamic quality score breakdown:
* **Evidence Quality (`EvidenceQuality`)**: Evaluates the count of research insights and presence of historical scenarios.
* **Consistency (`ConsistencyScore`)**: Highlights anomalies (e.g. high strategy score but rejected risk profile).
* **Reliability (`ReliabilityScore`)**: Represents overall stability of metadata and absence of data uncertainty markers.
* **Overall Quality (`OverallQualityScore`)**: Combined weighted index.

---

## 4. Conflict Handling & Resolution

Discrepancies between upstream engines are handled logically by the `DecisionConflictResolver`:
* **Research vs Strategy Mismatch**: Occurs when research indicators represent high confidence, but strategy compatibility is extremely low. Resolved by raising a discrepancy warning and applying a small confidence degradation.
* **Strategy vs Risk Conflict**: Occurs when a strategy is rated highly, but the risk engine rejects the weight limits. Resolved by applying a heavy confidence penalty and defaulting the analytical state to `Rejected`.

---

## 5. Decision Lifecycle States

Decisions are classified under five analytical states:
* **`Approved`**: Meets all research, strategy, and risk compatibility rules.
* **`Rejected`**: Triggered by a failed risk check or severe conflicts.
* **`ReviewRequired`**: Triggered by active leverage profiles, missing risk reports, or low alignment confidence.
* **`NoAction`**: Recommendations are skipped due to zero allocation weights.
* **`InsufficientData`**: Produced when essential research or strategy inputs are missing.

---

## 6. Safety & Sandboxing Limits

* **Zero Mutation**: Contexts, evidence trails, and reports are fully immutable (`frozen=True`).
* **Active Interception Guard**: The context checks all dictionary values against trade/order execution terms (e.g. `order`, `broker`, `position`, `transaction`, `place_order`, `buy_signal`). If a forbidden term is present, the parser raises a `ValidationException` immediately.
