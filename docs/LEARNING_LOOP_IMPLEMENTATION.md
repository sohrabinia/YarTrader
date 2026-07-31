# TradeYar AI — Learning Loop Implementation

This document details the complete design, architecture, and behavior of the completed **TradeYar AI Cognitive Learning Loop v2**.

## Architecture Overview

The cognitive workflow transitions from descriptive-analytical observations to self-improving persistent intelligence:

```
[Simulated Decision]
        │
        ▼
[Shadow Trading Engine]
        │
        ▼
[Judge Brain Evaluation]
        │
        ▼
[Experience Memory] (Raw / Unvalidated)
        │
        ▼
[validate_experience()] (Validated Experience)
        │
        ▼
[promote_experiences_to_patterns()]
        │
        ▼
[Pattern Memory] (Aggregated Situations & Outcomes)
        │
        ▼
[consolidate_patterns_to_concepts()]
        │
        ▼
[Concept Memory] (Vetted by Judge, sufficient samples)
```

## 1. Experience Promotion Pipeline

1. **Raw Experience**: Raw results of Virtual Positions / Shadow trades logged in Experience Memory.
2. **Validated Experience**: Experience vetted for presence of conclusive results (`SUCCESS` or `FAILURE`), marked as `is_validated = True` inside the experience metadata.
3. **Pattern Memory**: Experiences with highly similar Price-Action signatures (cosine similarity $\ge 0.85$) are consolidated into specific pattern identifiers, accumulating occurrence counters, continuation rates, and reversal metrics.
4. **Concept Memory**: Patterns that accumulate $\ge 5$ occurrences with stability/consistency $\ge 75\%$ are consolidated into Concept Memory blocks with Judge-vetted accuracy scores.

## 2. Confidence Decay & Forgetting Rate

To prevent overfitting to outdated market conditions, TradeYar AI implements an adaptive forgetting utility calculating active situational weights:

$$\text{Weight} = \text{Age Factor} + \text{Success Factor} + \text{Similarity Factor}$$

* **Age Factor**: Decays exponentially relative to the elapsed timeframe. Half-life is calibrated to 7 days ($604,800$ seconds).
* **Success Factor**: Rewards high-confidence positive feedback loops ($1.0$ for `SUCCESS`, $0.8$ for `NEUTRAL`, and $0.5$ for `FAILURE`).
* **Similarity Factor**: Dot product similarity score between current signature and historical reference, scaling between $0.0$ and $1.0$ (defaults to $0.5$).

## 3. Dynamic Learning Statistics

Dynamic monitors track performance across all memory tiers:
* `total_experiences`
* `patterns_created`
* `concepts_learned`
* `successful_patterns` (accuracy rate $\ge 60\%$)
* `failed_patterns` (accuracy rate $\le 40\%$)
* `last_learning_update`
