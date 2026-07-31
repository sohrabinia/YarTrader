# Conversation Intelligence Design
*TradeYar AI — Strategic Architecture & Capability Audit*

---

## 1. Product Vision

A key commercial value proposition of TradeYar AI is **Explainability**. To build trust, the AI must not act as a silent black-box signal generator. It must explain its logical reasoning, its statistical evidence base, its known limits, and its errors directly to human traders.

This document details the conversational response structures that map directly to the system's underlying memory systems (`query.py` and `memory.py`).

---

## 2. Structured Response Architectures

### Question 1: "Why did you open this trade?"
* **Triggers on**: Active `BUY` or `SELL` decisions.
* **Underlying Query**: Scans `KnowledgeQueryInterface` for the currently matched `PatternMemory` footprint and its historical outcomes.
* **Expected Response Format**:
```
Decision:
BUY

Reason:
420 similar historical situations found

Results:
276 successful
144 failed

Confidence:
65%

Risk:
High volatility environment
```

---

### Question 2: "Why did you NOT trade?"
* **Triggers on**: `WAIT` decisions where the market is active but no hypothesis is triggered, or when confidence fails validation filters.
* **Underlying Query**: Queries the `HypothesisEngine`. Shows that either no patterns were matched, or a matched pattern had high uncertainty (50/50 split) or insufficient historical sample sizes.
* **Expected Response Format**:
```
I avoided this trade.

Reason:
Only 20 historical examples found.
Confidence insufficient (52% consistency ratio is below the required 75% threshold).
```

---

### Question 3: "What did you learn?"
* **Triggers on**: Concept promotions or learning cycle summaries.
* **Underlying Query**: Queries `MarketMemorySystem.get_concepts()` and lists newly promoted Concepts approved by the Judge.
* **Expected Response Format**:
```
This behavior appeared 215 times.

Success:
143

Failure:
72

Knowledge updated: Promoted to Approved Concept 'Consolidated Pattern pat-09a1'.
```

---

### Question 4: "Why were you wrong?"
* **Triggers on**: Completed `FAILURE` outcomes.
* **Underlying Query**: Scans `ExperienceMemory` where `outcome_result == "FAILURE"` and retrieves the independent `JudgeBrain` feedback and MAE (Max Adverse Excursion).
* **Expected Response Format**:
```
Prediction:
Continuation

Reality:
Reversal

Lesson:
Similar cases failed during high volatility. Spread widened to 3.5 pips, causing a stop-loss trigger before price direction aligned.
```

---

### Question 5: "What do you not know?"
* **Triggers on**: High uncertainty environments or small sample patterns flagged by `ActiveLearningEngine`.
* **Underlying Query**: Scans the database via `ActiveLearningEngine.analyze_weaknesses_and_set_priorities()` and pulls pattern IDs with `occurrences_count < 3`.
* **Expected Response Format**:
```
Insufficient evidence.

Only 8 historical examples exist for the current sequence signature [1.5, -2.1, 0.4]. Research priority has been set to HIGH to acquire more observations in similar market environments.
```
