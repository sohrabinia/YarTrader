# APES-FIN Advanced Decision Intelligence Layer (Phase 18)

This document provides a comprehensive technical guide and architectural breakdown of the **Advanced Decision Intelligence Layer** within the RG_V3 Autonomous Financial Intelligence Platform.

---

## 1. Decision Architecture

The Advanced Decision Intelligence Layer acts as the final analytical synthesis node of the APES-FIN clean pipeline. It aggregates outputs from:
1. **Market Feature Extraction & Research Intelligence Engine (Phases 14, 15)**
2. **Strategy Evaluation Framework (Phase 16)**
3. **Advanced Risk Intelligence Layer (Phase 17)**

The architecture follows a strict, unidirectional dependency pattern. Under no circumstances does the decision layer feedback or alter prior calculations; instead, it synthesizes these layers into explainable, non-executable, analytical recommendations.

```text
Historical Data
      ↓
Feature Extraction
      ↓
Research Intelligence
      ↓
Strategy Evaluation
      ↓
Risk Intelligence
      ↓
Decision Intelligence [YOU ARE HERE]
```

---

## 2. Context Model (`DecisionIntelligenceContext`)

The `DecisionIntelligenceContext` is an immutable, frozen data model that compiles multi-factor insights, observations, and metadata into a standardized structure.

### Context Composition
- **Research Insights**: Curated passive analytical output of trend direction or volatility characteristics.
- **Pattern Observations**: Passive detected historical structural trends and price shapes.
- **Strategy Evaluations**: Scored and ranked multi-factor strategy evaluations under evaluation.
- **Risk Assessments**: Evaluated risk exposure boundaries and portfolios checks.
- **Market Conditions**: Key environmental parameters.
- **Metadata**: Additional tracking parameters.

### Simulation Safety
Following strict APES-FIN guidelines, `DecisionIntelligenceContext` incorporates an auto-scanning protection system within `__post_init__` to inspect all nested fields (recursively scanning lists, dictionaries, strings, and class properties) for forbidden execution-related keywords:
- `order`
- `position`
- `broker`
- `trade_command`
- `buy_signal`
- `sell_signal`
- `execute`

If any of these keywords are detected, the context fails immediately by raising a `ValidationException`, preventing live-trading leakages.

---

## 3. Evidence System (`DecisionEvidenceCollector` & `DecisionEvidenceTrail`)

For every generated decision, a detailed and immutable audit trail is compiled.

- **`DecisionEvidenceCollector`** aggregates all data fields from the active context.
- **`DecisionEvidenceTrail`** stores the snapshot of:
  - Research evidence snapshot
  - Feature snapshots
  - Pattern snapshots
  - Strategy evaluation snapshot
  - Risk assessment snapshot

This guarantees that every decision made by the system is fully audit-trail compliant, explainable, and trace-backable.

---

## 4. Quality Scoring (`DecisionQualityEvaluator` & `DecisionQualityScore`)

The `DecisionQualityEvaluator` analyzes the integrity and alignment of the decision inputs across three standard pillars:

1. **Evidence Quality**: Measures how complete, deep, and informative the underlying research insights, patterns, and market metrics are.
2. **Consistency**: Measures the semantic alignment of indicators. (e.g., does high strategy scoring match positive market sentiment? Is strategy compatibility fully matching the risk assessment?)
3. **Reliability**: Measures the overall confidence stability and statistical boundaries of the information.

### Quality Score Model (`DecisionQualityScore`)
Outputs a standardized score object:
- `OverallScore` (0.0 to 1.0)
- `EvidenceQuality` (0.0 to 1.0)
- `Consistency` (0.0 to 1.0)
- `Reliability` (0.0 to 1.0)
- Detailed underlying metrics dictionary.

---

## 5. Conflict Handling (`DecisionConflictResolver` & `ConflictResolutionResult`)

In complex real-world financial conditions, multi-layer inputs may contradict each other. For example:
- **Research Engine** indicates a strong positive uptrend.
- **Strategy Evaluator** yields a very low scoring rating.
- **Risk Intelligence** rejects the portfolio allocation due to exposure limit violations.

The `DecisionConflictResolver` detects these contradictions and outputs a structured **`ConflictResolutionResult`**:
- **`ConflictDetected`**: Boolean flag.
- **`ConflictType`**: Categorized conflict type (e.g., `Research_vs_Strategy`, `Strategy_vs_Risk`, or triple conflict).
- **`ConflictingSources`**: List of the source components that triggered the conflict.
- **`ResolutionExplanation`**: Explanatory textual summary.
- **`ConfidenceImpact`**: Quantitative degradation value (penalty subtracted from overall confidence).

This conflict handling is purely descriptive and does *not* auto-execute corrective trade overrides.

---

## 6. Decision Lifecycle & Analytical States

Every run evaluates inputs to output a `DecisionIntelligenceReport` which is assigned one of the five core analytical states:

1. **`Approved`**: High-quality inputs, risk limits fully respected, high multi-factor consistency.
2. **`Rejected`**: Failed risk limits or extreme safety violation thresholds.
3. **`ReviewRequired`**: Triggered under insufficient context data, low confidence levels, or severe conflicts.
4. **`NoAction`**: Generated if target weights or strategy allocations are zero.
5. **`InsufficientData`**: Explicit state indicating essential contextual telemetry is missing.

---

## 7. Safety Boundaries & Execution Prevention

The Decision Intelligence Layer is strictly analytical and **non-executable**:
- ❌ No order placement mechanics or endpoints.
- ❌ No direct broker connectivity or adapter access.
- ❌ No active financial balance tracking or transaction capabilities.
- ❌ No BUY/SELL execution signals are generated.
- ❌ No automated portfolio modification of active assets.
- ❌ Zero reliance on active machine learning model inference or live weights adjustments.

All decisions are logged securely as read-only **`DecisionHistoryRecord`**s for subsequent historical review and offline reinforcement optimization.
