# RG_V3 Autonomous Financial Intelligence Platform
## Market Intelligence Feature Extraction Foundation (Phase 14)

This document specifies the technical design, pipeline integration, validation, and safety constraints of the **Market Intelligence Feature Extraction Layer** of the RG_V3_AI platform.

---

## 1. Feature Layer Architecture

The Feature Ingestion & Extraction Layer is located under `src/Research/Features/`. It decouples raw market OHLCV bars into structured, normalized analytical descriptors designed for high-fidelity Research Engine interpretation.

```
                    [ FeatureRegistry ]
                             │
                             ▼
[ MarketDataPoint ] ──► [ FeaturePipeline ] ──► [ MarketFeatureSet ]
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     [ PriceCalc ]     [ VolatilityCalc ]  [ TrendCalc ] etc.
```

### Core Components:

*   **`FeatureDefinition`**: Metadata tracking a feature's structural scope, category, and calculation constraints.
*   **`FeatureValue`**: Standardized immutable representation of an calculated observation (e.g. name, value, timestamp, and context dictionary).
*   **`MarketFeatureSet`**: Packaged multi-feature series representation containing parsed calculations across an asset time range.
*   **`FeatureRegistry`**: Singleton/registry managing feature discovery, metadata validation, and calculator bindings.
*   **`FeaturePipeline`**: Central orchestration class that triggers registered calculators on input `MarketDataPoint` lists to build a `MarketFeatureSet`.

---

## 2. Calculated Descriptors (Initial Support)

All features calculated are purely descriptive and retro-analytical. Forecasting, predictions, or buy/sell signal structures are strictly prohibited.

### A. Price Features (`PriceFeatureCalculator`)
*   **Price Change**: `latest_close - oldest_close`.
*   **Percentage Return**: `(latest_close - oldest_close) / oldest_close`.
*   **Price Range**: Max period high minus min period low.

### B. Volatility Features (`VolatilityFeatureCalculator`)
*   **Rolling Volatility**: Annualized standard deviation of daily log returns over the period.
*   **Range Expansion**: `(latest_high - latest_low) / avg_period_range`.
*   **Volatility State**: Standard classification mapping rolling volatility into `"low"`, `"medium"`, or `"high"` states.

### C. Trend Features (`TrendFeatureCalculator`)
*   **Directional Movement**: Numeric sign mapping overall period trend direction (`1.0` bullish, `-1.0` bearish, `0.0` neutral).
*   **Trend Strength Classification**: Analytical classification of strength: `"strong_bullish"`, `"weak_bullish"`, `"neutral"`, `"weak_bearish"`, `"strong_bearish"`.

### D. Statistical Features (`StatisticalFeatureCalculator`)
*   **Mean**: Simple arithmetic mean of close prices.
*   **Standard Deviation**: Standard deviation of close prices.
*   **Skewness**: Fisher-Pearson standard third standardized moment measuring asymmetry.

---

## 3. Extraction & Calculation Lifecycle

```
[ MarketDataPoint Series ]
            │
            ▼
┌──────────────────────────────────────────┐
│ Validate Data Length (>= 1, non-empty)   │
└───────────┬──────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────┐
│ Dispatch to Price/Vol/Trend/Stat Calcs   │
└───────────┬──────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────┐
│ Aggregate FeatureValues into FeatureSet  │
└───────────┬──────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────┐
│ Build Unified MarketObservation Object   │
└──────────────────────────────────────────┘
```

---

## 4. Pipeline Integration

To integrate natively into the existing APES-FIN unidirectional flow without modifying preexisting orchestration pipelines, we implement the **adapter/decorator pattern** via **`FeatureExtractionResearchEngine`**:

```
[ HistoricalDataAdapter ] ──► [ FeatureExtractionResearchEngine ] ──► [ PipelineResult ]
                                           │
                                           ├─► Runs [ FeaturePipeline ]
                                           └─► Enriches [ ResearchProcessor ] Context
```

*   `FeatureExtractionResearchEngine` wraps any `IResearchEngine` implementation.
*   Upon `analyze_market(...)`, it uses its `IMarketDataProvider` to resolve underlying data points, extracts the `MarketFeatureSet` through the `FeaturePipeline`, converts it to a standard `MarketObservation`, and injects the extracted analytical telemetry directly inside the context of the underlying research task.

---

## 5. Safety Limitations and Restrictions

As an autonomous platform strictly meant for research and simulation validation, the Feature Ingestion & Extraction Layer enforces the following boundaries:

*   **No Predictive Logic**: No forecasting metrics, neural networks, or predictive modeling parameters are included.
*   **No Active Trading Hooks**: Explicit safety tests verify that the codebase is completely free of execution keywords (e.g., `buy_signal`, `sell_signal`, `place_order`, `execute_trade`, `broker_connection`, `position_tracker`).
*   **Simulation Guard**: If `SimulationMode` is disabled in the orchestration pipeline, the system raises a `ValueError` immediately, protecting boundaries against live money risk.
