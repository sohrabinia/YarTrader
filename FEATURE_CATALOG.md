# TradeYar AI Machine Learning Feature Catalog

This catalog outlines the formal inventory of features that can be extracted from TradeYar AI's existing data layers and persistence files. These features represent the data inputs required to train and evaluate supervised and sequence modeling algorithms on the platform.

---

## 1. Feature Categories

### Category I: Market Features (Data Ingest & Buffer)
*Source structures: `SymbolTimeContext.tick_buffer`, `MetaTrader5Provider`*

| Feature Name | Data Type | Description | Values / Range |
| :--- | :---: | :--- | :--- |
| `open_price_norm` | float | Normalized current open price relative to previous swing high/low. | $[0.0, 1.0]$ |
| `high_price_norm` | float | Normalized current high price relative to previous swing high/low. | $[0.0, 1.0]$ |
| `low_price_norm` | float | Normalized current low price relative to previous swing high/low. | $[0.0, 1.0]$ |
| `close_price_norm` | float | Normalized current close price relative to previous swing high/low. | $[0.0, 1.0]$ |
| `volume_norm` | float | Current trading volume normalized over 24-hour rolling average. | $[0.0, 10.0]$ |
| `atr_ratio` | float | Current Average True Range (ATR) divided by the 50-period moving average of ATR (volatility state). | $[0.1, 5.0]$ |
| `spread_volatility`| float | Rolling standard deviation of high-frequency price bid-ask spreads. | $\ge 0.0$ |
| `candle_body_ratio`| float | Ratio of the absolute candle body length to the total candle range. | $[0.0, 1.0]$ |
| `upper_wick_ratio` | float | Ratio of the upper candle wick length to the total candle range. | $[0.0, 1.0]$ |
| `lower_wick_ratio` | float | Ratio of the lower candle wick length to the total candle range. | $[0.0, 1.0]$ |
| `compression_state`| boolean | True if price range has compressed below the 20-period historical volatility threshold. | `True`/`False` |

---

### Category II: Research Features (Pattern & Structure)
*Source structures: `ResearchResult`, `BaseNodeDetector`, `MarketObservation`*

| Feature Name | Data Type | Description | Values / Range |
| :--- | :---: | :--- | :--- |
| `base_high_distance`| float | Distance in points/pips from current close price to nearest detected base high. | $\ge 0.0$ |
| `base_low_distance` | float | Distance in points/pips from current close price to nearest detected base low. | $\ge 0.0$ |
| `congested_node_dist`| float | Distance to the highest price volume node in the current lookback. | $\ge 0.0$ |
| `market_regime` | categorical| Current categorized market state (e.g., Accumulation, Expansion, Reversal). | `0` to `4` (encoded) |
| `pattern_cosine_sim`| float | Maximum cosine similarity of the current pattern footprint vs. historical templates. | $[0.0, 1.0]$ |

---

### Category III: Strategy Features (SCM Terminal)
*Source structures: `StrategyCandidate`, `StrategyEvaluation`*

| Feature Name | Data Type | Description | Values / Range |
| :--- | :---: | :--- | :--- |
| `strategy_score` | float | The overall momentum score computed by the StrategyEvaluator. | $[0.0, 1.0]$ |
| `signal_confidence` | float | The raw strategy signal confidence percentage before risk limits. | $[0.0, 100.0]$ |
| `setup_category` | categorical| The identified SCM strategy setup category (e.g. LiquiditySweep, OrderBlock). | string index |

---

### Category IV: Risk Features (Stress Validation)
*Source structures: `RiskAssessment`, `RiskProfile`*

| Feature Name | Data Type | Description | Values / Range |
| :--- | :---: | :--- | :--- |
| `risk_tolerance_lvl`| float | The configured risk tolerance level of the profile. | $[0.0, 1.0]$ |
| `proposed_weight` | float | Sizing allocation percentage proposed for the trade candidate. | $[0.0, 1.0]$ |
| `risk_approved` | boolean | Binary result indicating if the trade successfully cleared risk constraints. | `True`/`False` |
| `drawdown_ratio` | float | Current historical virtual capital drawdown divided by the maximum allowed draw limit. | $[0.0, 1.0]$ |

---

### Category V: Memory Features (Cognitive Tracking)
*Source structures: `MarketMemorySystem`, `PatternMemory`*

| Feature Name | Data Type | Description | Values / Range |
| :--- | :---: | :--- | :--- |
| `historical_win_rate`| float | The historical success rate (`continuation_count / occurrences_count`) of the pattern. | $[0.0, 100.0]$ |
| `sample_size_count` | integer | Total occurrences recorded in the persistent memory database for the pattern. | $\ge 0$ |
| `confidence_mult` | float | Dynamic active confidence multiplier calculated from the sample-size statistical gates. | $[0.90, 1.10]$ |
| `avg_judge_accuracy`| float | Average historical accuracy score awarded to the pattern by the JudgeBrain. | $[0.0, 1.0]$ |

---

## 2. Prediction Target Labels (Models)

To train predictive models, the following targets can be calculated from historical outcomes stored inside `runtime_logs/pattern_outcomes.json` or `runtime_logs/shadow_trades.json`:

| Label Name | Data Type | Description | Purpose |
| :--- | :---: | :--- | :--- |
| `Win_Loss` | binary | `1` if the shadow trade achieved its target (Take Profit), `0` if it hit stop loss or expired. | Trade Quality Classification |
| `Expected_Return` | float | The risk-reward multiple or points achieved during the shadow trade's lifespan. | Yield Estimation |
| `Success_Probability`| float | Calibrated probability of success based on local walk-forward buckets. | Sizing Optimization |
| `Trade_Quality` | multi-class| Classifies trade outcomes into `0` (Structural Loss), `1` (Lucky Win - survived extreme MAE), `2` (Earned Success). | Sizing Filter / High-accuracy execution |
