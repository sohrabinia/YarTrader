# YarTrader Machine Learning Feature Catalog

This catalog outlines the formal inventory of features that can be extracted from TradeYar AI's existing data layers and persistence files. These features represent the data inputs required to train and evaluate supervised and sequence modeling algorithms on the platform.

---

## 1. Purpose and Scope
This document represents the single authoritative, evidence-based Machine Learning Feature Catalog for the TradeYar AI platform (**YarTrader**). It registers the complete set of data structures, indicators, patterns, and safety limits available across the active platform, classifying each element according to its actual implementation and code-backed verification.

---

## 2. Feature Lifecycle Framework

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

## 3. Technical Classification & Feature Catalog

Every feature listed in this catalog is annotated with its exact **Evidence Classification** based on code-level audit verification.

### Evidence Classification Tiers:
*   **OPERATIONAL**: Directly implemented in production/runtime code and supported by concrete evidence.
*   **TEST/DEVELOPMENT EVIDENCE**: Exists in code/tests but production runtime usage is not proven.
*   **SIMULATED**: Exists only in replay, sandbox, fixtures, or tests.
*   **DEFINED/DERIVABLE**: Can be calculated from existing data but is not currently an active production ML feature.
*   **MISSING**: Not implemented.

---

### Category A: Price Features

#### Feature 1: `price_change`
- **Feature Name**: `price_change`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temporary in-memory `FeatureValue` structures, promoted to `ExperienceMemory` in `runtime_logs/brain_memory/experiences_memory.json`.
- **Consumed By**: `MarketMemorySystem` & `OutcomeEvaluationEngine` for cosine similarity matching.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified via unit test suite execution of `PriceFeatureCalculator` in `tests/test_feature_extraction.py`.

#### Feature 2: `percentage_return`
- **Feature Name**: `percentage_return`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temporary in-memory `FeatureValue` metrics.
- **Consumed By**: `TrendFeatureCalculator.calculate()` to classify trend strength.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified via unit test suite execution of `PriceFeatureCalculator` in `tests/test_feature_extraction.py`.

#### Feature 3: `price_range`
- **Feature Name**: `price_range`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `PriceFeatureCalculator.calculate()`
- **Storage**: Temporary in-memory `FeatureValue` boundaries.
- **Consumed By**: System metrics loggers and strategy candidate scorers.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Fully functional in current test fixtures under `tests/test_feature_extraction.py`.

#### Feature 4: `candle_body_size` (also known as `candle_body_ratio`)
- **Feature Name**: `body_size` / `candle_body_ratio`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.candle_structure` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Real-time decision logs and SRE telemetry dashboard interfaces.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Serialized atomically upon shadow trade execution events.

#### Feature 5: `candle_wick_ratio` (includes `upper_wick_ratio` & `lower_wick_ratio`)
- **Feature Name**: `wick_ratio` / `upper_wick_ratio` / `lower_wick_ratio`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.candle_structure` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Dashboard API endpoints and diagnostic query lookups.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Populated inside `pre_trade_context` JSON outputs.

#### Feature 6: Normalized Candlesticks (`open_price_norm`, `high_price_norm`, `low_price_norm`, `close_price_norm`)
- **Feature Name**: `open_price_norm`, `high_price_norm`, `low_price_norm`, `close_price_norm`
- **Source File**: `src/Research/Features/calculators.py` & `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: Custom indicators or pre-trade context normalizations.
- **Storage**: In-memory `FeatureValue` / `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Machine learning pipeline inputs (Candidate Targets).
- **Evidence Classification**: **DEFINED/DERIVABLE**
- **Runtime Evidence**: Calculated dynamically but not actively consumed by any live production ML inference loop.

---

### Category B: Volatility Features

#### Feature 1: `rolling_volatility`
- **Feature Name**: `rolling_volatility`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` structures.
- **Consumed By**: `VolatilityFeatureCalculator.calculate()` for volatility state classification.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified under `tests/test_feature_extraction.py` test suite.

#### Feature 2: `range_expansion`
- **Feature Name**: `range_expansion`
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` bounds.
- **Consumed By**: Dynamic strategy scoring thresholds.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Fully covered under the standard features test suite.

#### Feature 3: `volatility_state`
- **Feature Name**: `volatility_state` (Categorical: high, medium, low)
- **Source File**: `src/Research/Features/calculators.py`
- **Generator**: `VolatilityFeatureCalculator.calculate()`
- **Storage**: In-memory `FeatureValue` parameters.
- **Consumed By**: Dynamic risk limit evaluation routines.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Operational in features test pipelines.

#### Feature 4: `atr_state` (and `atr_ratio`)
- **Feature Name**: `atr_state` / `atr_ratio`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.volatility_metrics` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Cognitive learning metrics, pattern summaries, and SRE reports.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Generated dynamically after shadow position completion.

#### Feature 5: `spread_volatility`
- **Feature Name**: `spread_volatility`
- **Source File**: `src/Data/MarketData/Providers/providers.py`
- **Generator**: Can be processed from MT5 bid-ask streams.
- **Storage**: In-memory logs.
- **Consumed By**: SRE diagnostic tools.
- **Evidence Classification**: **DEFINED/DERIVABLE**
- **Runtime Evidence**: Read from tick stream but not actively utilized in active trading decisions.

---

### Category C: Volume Features

#### Feature 1: `volume_norm`
- **Feature Name**: `volume_norm` / `volume` (Standardized volume metric)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py` & `src/Research/Brain/multi_timeframe.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()` & `MultiTimeframePerception.generate_hierarchical_context()`
- **Storage**: In-memory buffers, persisted in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: Cosine similarity algorithms and multi-timeframe perception metrics.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Present in real-time JSON dumps of the pattern outcomes database.

#### Feature 2: `volume_spike`
- **Feature Name**: `volume_spike` (Boolean indicator)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized in `evidence.pre_trade_context.volatility_metrics` in `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: SRE monitoring and predictive alignment modules.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Captured in pre-trade context records.

---

### Category D: Pattern / Structure Features

#### Feature 1: `base_boundary` (and distances: `base_high_distance`, `base_low_distance`)
- **Feature Name**: `BaseStructure` (high and low boundary points)
- **Source File**: `src/ShadowTrading/Engine/BaseNodeDetector.py`
- **Generator**: `BaseNodeDetector.detect_base()`
- **Storage**: Appended to SymbolTimeContext bases and persisted in `runtime_logs/base_memory.json`.
- **Consumed By**: `PredictiveShadowEngine` for active entry breakout detection.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Real-time logging outputs: `"Automatically detected Base for [SYMBOL] @ high=..., low=..."`.

#### Feature 2: `node_boundary` (and `congested_node_dist`)
- **Feature Name**: `NodeStructure` (price level metrics)
- **Source File**: `src/ShadowTrading/Engine/BaseNodeDetector.py`
- **Generator**: `BaseNodeDetector.detect_node()`
- **Storage**: Appended to SymbolTimeContext nodes and persisted in `runtime_logs/node_memory.json`.
- **Consumed By**: Breakout/reaction limit mapping checks inside the `PredictiveShadowEngine`.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Real-time logging outputs: `"Automatically detected Node for [SYMBOL] @ price=..."`.

#### Feature 3: `pattern_key` (and `pattern_cosine_sim`)
- **Feature Name**: `pattern_key` (Multi-dimensional context representation)
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Serialized to `runtime_logs/pattern_outcomes.json`.
- **Consumed By**: FastAPI `/api/intelligence/learning-matrix` web endpoint to fetch active confidence statistics.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Loaded dynamically to render the front-end AI Learning matrix.

#### Feature 4: `market_regime`
- **Feature Name**: `market_regime`
- **Source File**: `src/Research/MarketAnalysis/Models/models.py`
- **Generator**: Evaluators.
- **Storage**: In-memory context models.
- **Consumed By**: Strategy scorers.
- **Evidence Classification**: **DEFINED/DERIVABLE**
- **Runtime Evidence**: No active production ML model leverages this as a trained feature.

---

### Category E: Strategy Features

#### Feature 1: `strategy_score`
- **Feature Name**: `strategy_score`
- **Source File**: `src/Strategy/Evaluation/evaluation.py`
- **Generator**: `StrategyEvaluator.evaluate()`
- **Storage**: Temporary in-memory evaluation models.
- **Consumed By**: Risk analyzers and decision engines.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Covered under `tests/TRADEYAR_AI.Tests/Execution/test_execution_endpoints.py`.

#### Feature 2: `signal_confidence`
- **Feature Name**: `signal_confidence`
- **Source File**: `src/Strategy/Evaluation/evaluation.py`
- **Generator**: `StrategyEvaluator` scoring rules.
- **Storage**: Temporary evaluation structs.
- **Consumed By**: Direct routing limits.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Present in real-time execution signal payloads.

#### Feature 3: `setup_category`
- **Feature Name**: `setup_category`
- **Source File**: `src/Strategy/Models/models.py`
- **Generator**: Strategy configuration categories.
- **Storage**: Memory arrays.
- **Consumed By**: Explanation and reporting engines.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Fully verified under SCM strategy setup checks.

---

### Category F: Risk Features

#### Feature 1: `risk_approved`
- **Feature Name**: `risk_approved` / `IsApproved` (Boolean)
- **Source File**: `src/Risk/Services/services.py` & `src/Application/Pipeline/pipeline.py`
- **Generator**: `RiskAnalyzer.analyze_risk()`
- **Storage**: Temporary in-memory `RiskAssessment` attributes.
- **Consumed By**: `DecisionEngine` to decide whether to evaluate allocations or trigger immediate rejection fallback.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified via `tests/test_risk.py` and `tests/test_full_intelligence_validation.py`.

#### Feature 2: `proposed_weight` / `max_single_asset_exposure`
- **Feature Name**: `SuggestedValue` (of MaxSingleAssetExposure parameter)
- **Source File**: `src/Learning/Services/services.py`
- **Generator**: `OptimizationEngine.optimize_exposure()`
- **Storage**: Outputted dynamically inside `ImprovementSuggestion` memory logs.
- **Consumed By**: FastAPI learning-report endpoint for supervisor review.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified under `tests/test_learning_optimization.py`.

#### Feature 3: `drawdown_ratio` (and `risk_tolerance_lvl`)
- **Feature Name**: `drawdown_ratio` / `risk_tolerance_lvl`
- **Source File**: `src/Risk/Models/models.py`
- **Generator**: Current profile constraints.
- **Storage**: Memory configuration settings.
- **Consumed By**: Stress evaluation limits.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Evaluated and logged dynamically within risk assessment cycles.

---

## Category G: Memory-derived Features

#### Feature 1: `historical_win_rate_pct` (also known as `historical_win_rate`)
- **Feature Name**: `historical_win_rate_pct` / `win_rate_pct` / `historical_win_rate`
- **Source File**: `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `PredictiveShadowEngine._record_pattern_outcome_context()`
- **Storage**: Persisted inside the `patterns_outcomes.json` database.
- **Consumed By**: The dynamic active confidence scaling logic when next matching pattern occurs.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: In-memory calculations loaded dynamically for similarity adjustments.

#### Feature 2: `active_confidence_multiplier` (also known as `confidence_mult` and `confidence_multiplier`)
- **Feature Name**: `active_confidence_multiplier` / `confidence_mult`
- **Source File**: `src/Application/Services/web_dashboard.py` & `src/ShadowTrading/Engine/PredictiveShadowEngine.py`
- **Generator**: `web_dashboard.get_learning_matrix()` (Heuristic-driven shift calculations: 30-100 occurrences $=\pm0.02$, 100-500 $=\pm0.05$, 500+ $=\pm0.10$).
- **Storage**: Dynamically computed and exposed over REST APIs.
- **Consumed By**: React Single Page Application frontend `/learning` interface.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified under the SRE Telemetry dashboard checks.

#### Feature 3: `sample_size_count`
- **Feature Name**: `sample_size_count` / `sample_count`
- **Source File**: `src/Research/Brain/memory.py`
- **Generator**: `MarketMemorySystem` occurrences calculation.
- **Storage**: Persisted in brain JSON memory layers.
- **Consumed By**: Dynamic statistical gate decisions.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Verified via cognitive memory tests.

#### Feature 4: `avg_judge_accuracy`
- **Feature Name**: `avg_judge_accuracy`
- **Source File**: `src/Research/Brain/memory.py` & `src/Research/Brain/judge.py`
- **Generator**: `JudgeBrain` scoring metrics.
- **Storage**: Layered memory databases.
- **Consumed By**: Concept validation gates.
- **Evidence Classification**: **OPERATIONAL**
- **Runtime Evidence**: Active in memory-promotion pipeline checks.

---

## 4. Structural Reality Separation

To ensure absolute system compliance and transparency, we explicitly separate features into three operational states:

### 1. Existing Operational Features
These are fully functional, implemented, persisted to files, tested, and actively utilized by the runtime engines:
- **Price Features**: `price_change`, `percentage_return`, `price_range`, `candle_body_size`, `candle_wick_ratio`.
- **Volatility Features**: `rolling_volatility`, `range_expansion`, `volatility_state`, `atr_state`.
- **Volume Features**: `volume_norm`, `volume_spike`.
- **Pattern Features**: `BaseStructure` (base boundaries), `NodeStructure` (node congestion levels), `pattern_key`.
- **Risk Features**: `risk_approved` (allocation status), `max_single_asset_exposure` limits.
- **Memory-derived Features**: `historical_win_rate_pct`, `active_confidence_multiplier` shifts.

### 2. Simulated / Test-only Features
These features are generated programmatically inside sandboxed simulation loops or replay environments to test cognitive intelligence limits:
- **`expected_scenario`**: Part of `SimulatedDecision` and `Hypothesis` structures used inside `CognitiveReplayLoop` to test directional expectations against historical ticks.
  - **Evidence Classification**: **SIMULATED**
- **`judge_vetted_accuracy`**: Simulated inside `test_full_memory_promotion_pipeline.py` by appending mock accuracy coefficients (e.g. `0.85`) to verify memory promotion criteria.
  - **Evidence Classification**: **SIMULATED**

### 3. Missing Machine Learning Features
These features are currently absent from the production codebase and represent required developments once a live ML modeling layer (such as LightGBM or XGBoost) is introduced:
- **`shap_feature_importance`**: SHAP value matrices representing the exact local contribution of each feature to the model's output probability.
  - **Evidence Classification**: **MISSING**
- **`feature_drift_coefficient`**: Metric representing the covariate drift of input distributions over time.
  - **Evidence Classification**: **MISSING**
- **`probabilistic_sizing_score`**: Calibrated probability output representing trade-quality likelihood used directly for real-time order sizing.
  - **Evidence Classification**: **MISSING**

---

## 5. Prediction Target Labels (Candidate Design)

The following labels are candidates for future machine learning models but are **NOT** currently used as trained model outputs:

| Target Name | Data Type | Description | Evidence Classification | Purpose / Use Case |
| :--- | :---: | :--- | :---: | :--- |
| `Win_Loss` | binary | `1` if the shadow trade achieved its target (Take Profit), `0` if it hit stop loss or expired. | **DEFINED/DERIVABLE** | Trade Quality Classification |
| `Expected_Return` | float | The risk-reward multiple or points achieved during the shadow trade's lifespan. | **DEFINED/DERIVABLE** | Yield Estimation |
| `Success_Probability`| float | Calibrated probability of success based on local walk-forward buckets. | **MISSING** | Sizing Optimization |
| `Trade_Quality` | multi-class| Classifies trade outcomes into `0` (Structural Loss), `1` (Lucky Win - survived extreme MAE), `2` (Earned Success). | **DEFINED/DERIVABLE** | Sizing Filter / High-accuracy execution |

---

## 6. Audit Status

**Current Implementation State Audit**:
This Machine Learning Feature Catalog serves as a specification of potential, derivable, and operational parameters. It **does NOT** certify or imply the existence of an active, trained production machine learning model, nor does it guarantee that automated backpropagation is live in production.

Furthermore, any dashboard statistics (such as *Win-rate: 66.7%*, *Win-rate: 100.0%*, *Avg R:R: 2.5 R*, *Avg R:R: 3.1 R*) are **not derived** from real-time ML-trained inference, but are hardcoded aesthetic and synthetic UI elements inside the React client dashboard terminal (`trader-terminal/src/App.jsx`) to represent structural capability indicators.

- **Lead AI Systems Engineer & ML Auditor**
- **TradeYar AI Architecture Board**
- **Date of Audit**: August 2026
