# RG_V3 Autonomous Financial Intelligence Platform
## Research Intelligence Engine Evolution (Phase 15)

This document specifies the technical design, lifecycle events, pattern detection logic, and safety restrictions of the **Evolved Research Intelligence Engine**.

---

## 1. Engine Layer Architecture

The Research Engine Layer resides under `src/Research/Engine/`. It upgrades the initial research foundation into a fully integrated analytical core capable of transforming raw features into high-level descriptive structures.

```
                    [ ResearchEngine ]
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
  [ ObservationAnalyzer ] [ PatternDetector ] [ InsightGenerator ]
            │                │                │
            └────────────────┼────────────────┘
                             │
                             ▼
                 [ ResearchReportBuilder ]
                             │
                             ▼
                     [ ResearchReport ]
```

### Core Components:

*   **`ObservationAnalyzer`**: Consumes `MarketFeatureSet` and translates relationships among indicators (like volatility thresholds or trend classifiers) into specific `MarketObservation` objects.
*   **`PatternDetector`**: Discovers recurrent historical behavioral patterns from observations, outputting standard `PatternObservation`s.
*   **`InsightGenerator`**: Evaluates active patterns and observations to formulate qualitative, high-confidence `MarketInsight` messages.
*   **`ResearchReportBuilder`**: Dynamically compiles all analytical elements into a consolidated, immutable `ResearchReport` with comprehensive metadata tracking.
*   **`ResearchEngine`**: Coordinates execution flow, manages validation checks, and packages output findings into standard `ResearchResult` structures.

---

## 2. Structured Observations Lifecycle

Market observations follow a deterministic lifecycle:

```
[ Ingest Features ] ──► [ Volatility State ] ──► [ Trend Strength ] ──► [ Range Expansion ] ──► [ MarketObservation ]
```

1.  **State Verification**: The analyzer checks for presence of key indicators (e.g., rolling annualized volatility, range percentage return).
2.  **State Inferences**:
    *   **Increasing Volatility State**: Inferred when `rolling_volatility >= 30%`.
    *   **Range Compression State**: Inferred when `rolling_volatility < 15%`.
    *   **Stable Trend Behavior**: Inferred when `trend_strength_classification` exhibits strong bullish or bearish conditions.
    *   **Market Transition Condition**: Inferred when high-low range expansion exceeds `1.2x`.

---

## 3. Passive Pattern Discovery Model

The `PatternDetector` correlates observations to identify behavioral patterns. These patterns are strictly analytical. **No trading patterns (e.g. cup-and-handle, head-and-shoulders, or buy/sell flags) are introduced.**

| Pattern Name | Inputs Required | Descriptive Analysis | Confidence |
| :--- | :--- | :--- | :--- |
| **Volatility Expansion Breakthrough Pattern** | `Increasing Volatility State` + `Market Transition Condition` | Indicates structural breakout from previous pricing ranges. | 85% |
| **Mean Reversion Structural Pattern** | `Range Compression State` | Predicts standard structural compression preceding standard reversion. | 75% |
| **Strong Directional Momentum Pattern** | `Stable Trend Behavior` | Captures strong directional continuation bias. | 80% |

---

## 4. Qualitative Insight Generation

Insights are derived mathematically from matched patterns, packaging descriptions and exact confidence metadata for downstream pipeline consumption:

*   **Category Classification**: Insights are grouped into specific analytical classes like `VolatilityState`, `TrendAnalysis`, and `MarketRegime`.
*   **Confidence Calibration**: Standard confidence scores (ranging from 0.0 to 1.0) represent pattern detection strength and empirical evidence.

---

## 5. Structural Report Schema

The `ResearchReport` packages descriptive telemetry:

```json
{
  "report_id": "rpt-AAPL-4a5f8e32",
  "asset_id": "AAPL",
  "start_time": "2026-03-01T09:00:00",
  "end_time": "2026-03-01T13:00:00",
  "observations_count": 3,
  "patterns_count": 1,
  "insights_count": 1,
  "observations": [
    {
      "condition": "Stable Trend Behavior",
      "description": "Asset AAPL exhibits a stable strong_bullish trend"
    }
  ],
  "patterns": [
    {
      "name": "Strong Directional Momentum Pattern",
      "confidence": 0.80
    }
  ],
  "insights": [
    {
      "category": "TrendAnalysis",
      "description": "Descriptive Insight: Stable trend direction supported..."
    }
  ]
}
```

---

## 6. Safety Boundaries

The Evolved Research Engine enforces strict safety limits to comply with the research-only mandate:

*   **No Price Forecasting**: No predictive model weights, price forecasts, or neural networks exist in this layer.
*   **No Execution Hooks**: Scans confirm total absence of order placement trigger keys (e.g. `buy_signal`, `sell_signal`, `execute_order`).
*   **Environment Safety**: The standard simulation mode guard remains fully active.
