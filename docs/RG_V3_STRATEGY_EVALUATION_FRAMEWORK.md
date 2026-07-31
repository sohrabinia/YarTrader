# TRADEYAR Strategy Intelligence Evaluation Framework (Phase 16)

This documentation outlines the architecture, scoring models, and integration of the Strategy Intelligence Evaluation Framework.

---

## 1. Introduction & Mission

The **Strategy Intelligence Evaluation Framework** is a passive analytical layer within the APES-FIN architecture. Its sole purpose is to evaluate, score, and rank **Strategy Candidates** without generating trading decisions, triggers, orders, or connecting to live broker accounts.

---

## 2. Evaluation Architecture

The framework consists of five core components:

1. **`StrategyEvaluationContext`**: An immutable, framework-independent context containing research insights, market observations, historical scenario context, and risk parameters. It strictly prevents execution leakage by executing deep keyword scanning to intercept active trading fields.
2. **`StrategyScorer`**: A deterministic scoring system that assesses strategy candidates against multiple dimensions.
3. **`StrategyComparator`**: Ranks multiple strategy candidates based on their scores, identifying the highest-quality candidate configuration.
4. **`EvaluationReportBuilder`**: Compiles evaluation results, scoring breakdowns, comparison details, and research evidence into a unified audit report (`StrategyEvaluationReport`).
5. **`StrategyEvaluator`**: The entry point coordinating candidates and contexts, generating complete `StrategyEvaluation` outputs.

---

## 3. Scoring Model

The scorer evaluates strategies across four core dimensions:
* **Research Alignment (`ResearchAlignment`)**: Measures how closely the strategy candidate aligns with structured market research and confidence from research insights.
* **Historical Compatibility (`HistoricalCompatibility`)**: Rates how well the strategy is predicted to perform against historical conditions based on scenario success rates.
* **Risk Compatibility (`RiskCompatibility`)**: Checks conformity with active risk mandates and profile limits.
* **Stability Score (`Stability`)**: Assesses historical return-rate variance and consistency indicators.

### Scoring Adjustments
* **Research Insights Impact**: High-confidence insights automatically increase both the Research Alignment and Stability scores, while low-confidence insights degrade them.
* **Risk Limits Impact**: Stricter risk tolerance limits dynamically lower the Risk Compatibility score if candidate indicators show elevated variance.
* **Scenario Performance Impact**: Higher historical success rates in synthetic or offline scenarios increase the Historical Compatibility rating.

---

## 4. Strategy Lifecycle & Research Integration

The strategy candidate lifecycle progresses through the following states:
1. **Creation**: A draft conceptual definition (`StrategyDefinition`) is prepared with metadata.
2. **Analysis**: Structural validation guarantees no trading execution rules or triggers exist (`StrategyAnalyzer`).
3. **Promotion to Candidate**: When promoted for study, a `StrategyCandidate` is initialized.
4. **Context Enrichment**: The pipeline combines current `MarketObservations` and `MarketInsight` findings from the Research Engine into a `StrategyEvaluationContext`.
5. **Evaluation & Scored Feedback**: The evaluator runs the candidate through the scorer, producing a `StrategyEvaluation`.
6. **Comparison & Report Compilation**: Multiple candidates are ranked, and a comprehensive evaluation report is archived.

---

## 5. Safety & Sandboxing Limits

To preserve absolute safety:
* **Strict Immutability**: All contexts and reports are frozen/immutable.
* **Zero Trading Logic**: There are no functions, methods, or parameters referencing orders, positions, trade triggers, or broker adapters.
* **Strict Keyword Interceptor**: Deep-scan validation checks candidate attributes and context dictionaries for forbidden keywords (e.g., `place_order`, `buy_signal`, `sell_signal`, `live_trade`, `broker_connection`). Attempting to pass execution-related terms raises a `ValidationException` immediately.
