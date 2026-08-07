# TradeYar AI Machine Learning Feature Catalog & Architecture Audit

This document is the official, evidence-based Machine Learning Feature Catalog compiled by the Principal AI Architect of **TradeYar AI (YarTrader)**. It presents an exhaustive code and runtime audit of the existing data structures, technical indicators, pattern parameters, and risk states, mapping their complete end-to-end operational lifecycles.

---

## 1. Feature Lifecycle Framework

The lifecycle of all data elements across the TradeYar AI platform adheres to a strict unidirectional flow:

```
[Input Layer] ➔ [Processing Layer] ➔ [Storage Layer] ➔ [Decision / Inference Layer]
```

### End-to-End Pipeline Phases:

1. **Input Layer**: Raw tick-level price streams and order parameters are ingested from MetaTrader 5 or historical backtest CSV sources.
2. **Processing Layer**: High-frequency calculators, detectors, and evaluators extract technical indicators, swing ranges, and statistical metrics.
3. **Storage Layer**: Processed values are serialized atomically using thread-safe, validation-secured files (JSON structures under `runtime_logs/`).
4. **Decision / Inference Layer**: The `PredictiveShadowEngine` and `DecisionEngine` consume the stored patterns and historical win rates to adjust signal confidence weights and scale dynamic active multipliers.

---

## 2. Technical Classification & Feature Catalog

This catalog details every feature actively present, simulated, or defined in the codebase.

---

### Category A: Price Features

#### Feature 1: `price_change`
- **Feature Name**: `price_change`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temp in-memory `FeatureValue` structures, promoted to `ExperienceMemory` in `runtime_logs/brain_memory/experiences_memory.json`.
- **Consumed By**: `MarketMemorySystem` & `OutcomeEvaluationEngine` for cosine similarity matching.
- **Runtime Evidence**: Verified via unit test suite execution of `PriceFeatureCalculator` in `tests/test_feature_extraction.py`.

#### Feature 2: `percentage_return`
- **Feature Name**: `percentage_return`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temp in-memory `FeatureValue` metrics.
- **Consumed By**: `TrendFeatureCalculator.calculate()` to classify trend strength.
- **Runtime Evidence**: Verified via unit test suite execution of `PriceFeatureCalculator`.

#### Feature 3: `price_range`
- **Feature Name**: `price_range`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temp in-memory `FeatureValue` boundaries.
- **Consumed By**: System metrics loggers and strategy candidate scorers.
- **Runtime Evidence**: Fully functional in current test fixtures under `test_feature_extraction.py`.

#### Feature 4: `candle_body_size`
- **Feature Name**: `body_size` (Pre-trade candle body ratio)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.candle_structure` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Real-time decision logs and SRE telemetry dashboard interfaces.
- **Runtime Evidence**: Serialized atomically upon shadow trade execution events.

#### Feature 5: `candle_wick_ratio`
- **Feature Name**: `wick_ratio`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.candle_structure` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Dashboard API endpoints and diagnostic query lookups.
- **Runtime Evidence**: Populated inside `pre_trade_context` JSON outputs.

---

### Category B: Volatility Features

#### Feature 1: `rolling_volatility`
- **Feature Name**: `rolling_volatility`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` structures.
- **Consumed By**: `VolatilityFeatureCalculator.calculate()` for volatility state classification.
- **Runtime Evidence**: Verified under `test_feature_extraction.py` test suite.

#### Feature 2: `range_expansion`
- **Feature Name**: `range_expansion`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` bounds.
- **Consumed By**: Dynamic strategy scoring thresholds.
- **Runtime Evidence**: Fully covered under the standard features test suite.

#### Feature 3: `volatility_state`
- **Feature Name**: `volatility_state` (Categorical: high, medium, low)
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` parameters.
- **Consumed By**: Dynamic risk limit evaluation routines.
- **Runtime Evidence**: Operational in features test pipelines.

#### Feature 4: `atr_state`
- **Feature Name**: `atr_state` (Categorical volatility representation)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.volatility_metrics` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Cognitive learning metrics, pattern summaries, and SRE reports.
- **Runtime Evidence**: Generated dynamically after shadow position completion.

---

### Category C: Volume Features

#### Feature 1: `volume_norm`
- **Feature Name**: `volume_norm` / `volume` (Standardized volume metric)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py` & `src/Research/Brain/multi_timeframe.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()` & `MultiTimeframePerception.generate_hierarchical_context()`
- **Storage**: In-memory buffers, persisted in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Cosine similarity algorithms and multi-timeframe perception metrics.
- **Runtime Evidence**: Present in real-time JSON dumps of the pattern outcomes database.

#### Feature 2: `volume_spike`
- **Feature Name**: `volume_spike` (Boolean indicator)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.volatility_metrics` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: SRE monitoring and predictive alignment modules.
- **Runtime Evidence**: Captured in pre-trade context records.

---

### Category D: Pattern Features

#### Feature 1: `base_boundary`
- **Feature Name**: `BaseStructure` (high and low boundary points)
- **Source File**: `src/ShadowTrading/Engine/BaseNodeDetector.py`
- **Generator**: `BaseNodeDetector.detect_base()`
- **Storage**: Appended to SymbolTimeContext bases and persisted in `runtime_logs/base_memory.json`.
- **Consumed By**: `PredictiveShadowEngine` for active entry breakout detection.
- **Runtime Evidence**: Real-time logging outputs: `"Automatically detected Base for [SYMBOL] @ high=..., low=..."`.

#### Feature 2: `node_boundary`
- **Feature Name**: `NodeStructure` (price level metrics)
- **Source File**: `src/ShadowTrading/Engine/BaseNodeDetector.py`
- **Generator**: `BaseNodeDetector.detect_node()`
- **Storage**: Appended to SymbolTimeContext nodes and persisted in `runtime_logs/node_memory.json`.
- **Consumed By**: Breakout/reaction limit mapping checks inside the `PredictiveShadowEngine`.
- **Runtime Evidence**: Real-time logging outputs: `"Automatically detected Node for [SYMBOL] @ price=..."`.

#### Feature 3: `pattern_key`
- **Feature Name**: `pattern_key` (Multi-dimensional context representation)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized to `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: FastAPI `/api/intelligence/learning-matrix` web endpoint to fetch active confidence statistics.
- **Runtime Evidence**: Loaded dynamically to render the front-end AI Learning matrix.

---

### Category E: Risk Features

#### Feature 1: `risk_approved`
- **Feature Name**: `risk_approved` / `IsApproved` (Boolean)
- **Source File**: `src/Risk/Services/services.py` & `src/Application/Pipeline/pipeline.py`
- **Generator**: `RiskAnalyzer.analyze_risk()`
- **Storage**: Temporary in-memory `RiskAssessment` attributes.
- **Consumed By**: `DecisionEngine` to decide whether to evaluate allocations or trigger immediate rejection fallback.
- **Runtime Evidence**: Verified via `test_risk.py` and `test_full_intelligence_validation.py`.

#### Feature 2: `max_single_asset_exposure`
- **Feature Name**: `SuggestedValue` (of MaxSingleAssetExposure parameter)
- **Source File**: `src/Learning/Services/services.py`
- **Generator**: `OptimizationEngine.optimize_exposure()`
- **Storage**: Outputted dynamically inside `ImprovementSuggestion` memory logs.
- **Consumed By**: FastAPI learning-report endpoint for supervisor review.
- **Runtime Evidence**: Verified under `test_learning_optimization.py`.

---

### Category F: Memory-derived Features

#### Feature 1: `historical_win_rate_pct`
- **Feature Name**: `historical_win_rate_pct` / `win_rate_pct`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Persisted inside the `patterns_outcomes.json` database.
- **Consumed By**: The dynamic active confidence scaling logic when next matching pattern occurs.
- **Runtime Evidence**: In-memory calculations loaded dynamically for similarity adjustments.

#### Feature 2: `active_confidence_multiplier`
- **Feature Name**: `active_confidence_multiplier` (Dynamic scaling parameter)
- **Source File**: `src/Application/Services/web_dashboard.py` & `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `web_dashboard.get_learning_matrix()` (Heuristic-driven shift calculations: 30-100 occurrences $=\pm0.02$, 100-500 $=\pm0.05$, 500+ $=\pm0.10$).
- **Storage**: Dynamically computed and exposed over REST APIs.
- **Consumed By**: React Single Page Application frontend `/learning` interface.
- **Runtime Evidence**: Verified under the SRE Telemetry dashboard checks.

---

## 3. Structural Reality Separation

To ensure absolute system compliance and transparency, we explicitly separate features into three operational states:

### 1. Existing Operational Features
These are fully functional, implemented, persisted to files, tested, and actively utilized by the runtime engines:
- **Price Features**: `price_change`, `percentage_return`, `price_range`, `candle_body_size`, `candle_wick_ratio`.
- **Volatility Features**: `rolling_volatility`, `range_expansion`, `volatility_state`, `atr_state`.
- **Volume Features**: `volume_norm`, `volume_spike`.
- **Pattern Features**: `BaseStructure` (base boundaries), `NodeStructure` (node congestion levels), `pattern_key`.
- **Risk Features**: `risk_approved` (allocation status), `max_single_asset_exposure` limits.
- **Memory-derived Features**: `historical_win_rate_pct`, `active_confidence_multiplier` shifts.

### 2. Simulated Features
These features are generated programmatically inside sandboxed simulation loops or replay environments to test cognitive intelligence limits:
- **`expected_scenario`**: Part of `SimulatedDecision` and `Hypothesis` structures used inside `CognitiveReplayLoop` to test directional expectations against historical ticks.
- **`judge_vetted_accuracy`**: Simulated inside `test_full_memory_promotion_pipeline.py` by appending mock accuracy coefficients (e.g. `0.85`) to verify memory promotion criteria.

### 3. Missing Machine Learning Features
These features are currently absent from the production codebase and represent required developments once a live ML modeling layer (such as LightGBM or XGBoost) is introduced:
- **`shap_feature_importance`**: SHAP value matrices representing the exact local contribution of each feature to the model's output probability.
- **`feature_drift_coefficient`**: Metric representing the covariate drift of input distributions over time.
- **`probabilistic_sizing_score`**: Calibrated probability output representing trade-quality likelihood used directly for real-time order sizing.

---
### Auditor Certification
**Principal AI Architect**
*TradeYar AI Architecture Board*
*Date of Audit: August 2026*
