# RG_V3 Research Intelligence Layer Foundation

The Research Intelligence Layer is responsible for transforming raw, normalized market data into structured research observations, statistics, and qualitative market insights across the RG_V3 Autonomous Financial Intelligence Platform. This layer operates completely under passive analytical principles.

---

## 1. Research Intelligence Mission

The core mission of the Research Intelligence Layer is to:
* **Perform Deep Passive Analysis:** Translate plain transaction/bar records into multi-dimensional market states (volatility limits, trend indices, historical correlations).
* **Decouple Raw Data from Logical Decision-Making:** Shield strategy and decision models from raw series handling by packaging mathematical metrics into standard research request/result models.
* **Abstract Indicator Rules:** Standardize indicator schemas (e.g. SMA, EMA, MACD, Volatility ranges) as pure parameters to ensure indicators remain completely descriptive and logic-free.

---

## 2. Role in the APES-FIN Pipeline

Under the APES-FIN architecture standard, processing moves in a unidirectional, single-responsibility stream:

```text
  [ Market Data Ingestion ] (Data Layer)
             ↓
  [ Research Intelligence ] (Research Layer)   <-- Translates raw bars to descriptive states
             ↓
  [ Market Understanding ] (Research Layer)    <-- Grouping observations into insights
             ↓
  [ Strategy Evaluation ] (Strategy Layer)     <-- Score suitability (No buy/sell signals)
```

By placing the Research Layer immediately after Data Ingestion, we ensure all downstream strategies evaluate pre-processed, statically checked, and high-confidence research results.

---

## 3. Difference Between Research Engine and Trading Bot

The RG_V3 Research Engine is strictly **NOT** a trading bot:

| Characteristic | RG_V3 Research Engine | Traditional Trading Bot |
| :--- | :--- | :--- |
| **Primary Goal** | Structured Market Description | Actionable Trade Generation |
| **Output Type** | Observations, Insights, Reports, and Indicators | BUY / SELL execution triggers and Orders |
| **Risk Handling** | Descriptive assessment and safety auditing | Active leverage adjustments, Stop-Loss orders |
| **Logic Type** | Passive statistical & analytical frameworks | Reactive trade automation & execution loops |

The Research Engine contains absolutely zero trigger parameters, no stop-loss/take-profit boundaries, and no event listeners designed to send transactions to standard brokers.

---

## 4. Data Flow

Data processing flows linearly:

1. **Research Request (`ResearchRequest`):** Downstream components query the research layer for an asset, timeframe, and research context.
2. **Indicator & Analyzer Evaluation:** The engine coordinates pure analyzers (e.g. `TechnicalAnalyzer`) and abstract indicators to calculate descriptive values over the requested timeframe.
3. **Observation Grouping (`MarketObservation`):** Calculated indicators are wrapped with temporal and source markers as an observed state.
4. **Insight Synthesis (`MarketInsight`):** The `MarketAnalysisEngine` classifies observations into categories (e.g. Trend, Volatility) with a standardized `Confidence` score.
5. **Research Result (`ResearchResult`):** The final structured reports containing synthesized insights and metadata are stored and returned.

---

## 5. Separation From Strategy Layer

To maintain clean architectural boundaries and prevent coupling:
* **Research Layer** only describes "what the market state is". It has zero concept of portfolios, asset allocation weights, scoring priorities, or strategy goals.
* **Strategy Layer** consumes research results and applies ranking rules to score the assets for allocation. The strategy layer is an active observer of the research layer, but the research layer remains completely unaware of how its descriptive findings are prioritized or scored.

---

## 6. Future Extension Points

The Research Layer features clear contracts to allow easy extension:
* **Custom Indicator Providers (`IIndicatorProvider`):** Easily add support for mathematical indicators (e.g., custom RSI, Bollinger Band limits) by implementing `IIndicatorProvider`.
* **Deep Statistical Analyzers (`IMarketAnalyzer`):** Integrate advanced statistical/econometric model analysis or alternative observation engines by implementing `IMarketAnalyzer`.
* **State Preservation (`IResearchRepository`):** Swap local memory storage of reports for external timeseries databases or cloud repositories with zero impact on the analytical engine.
