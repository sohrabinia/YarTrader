# TradeYar AI — Memory Governance & Lifecycles

This document describes the hierarchical division of TradeYar AI's memory and the lifecycle constraints (retention, promotion, and pruning) of each layer.

```
       +--------------------------------------------+
       |                  RAW MEMORY                |  (High volume, short retention)
       |   Raw observations, Tick & M1 bar state    |
       +--------------------------------------------+
                             |
                             v  (Validation & Events)
       +--------------------------------------------+
       |              EXPERIENCE MEMORY             |  (Episodic logs of simulated decisions)
       |   Situation -> Decision -> Outcome -> Lesson|
       +--------------------------------------------+
                             |
                             v  (Pattern Generalization)
       +--------------------------------------------+
       |               CONCEPT MEMORY               |  (Persistent structural rules / Concepts)
       |   Highly-recurrent similarity structures    |
       +--------------------------------------------+
```

## 1. Memory Tier Definitions

### 1.1 Raw Memory (Observations & Sequences)
- **Content:** Every individual candle bar and raw mathematical delta sequence.
- **Retention Policy:** Short-term cache. Raw Tick and M1 states are rotated or cleared after 500 records to prevent memory bloat.

### 1.2 Experience Memory (Episodic)
- **Content:** Chronological logs of simulated decisions, entry/exit points, excursions, and Judge evaluations.
- **Retention Policy:** Medium-term. Kept persistently up to a maximum of 5,000 episodic logs before archiving. Failed cases are NEVER deleted, as they represent the highest value lessons to prevent repeating bad decisions.

### 1.3 Concept Memory (Tested Concepts)
- **Content:** General scale-invariant patterns with high recurrence and verified statistical outcomes.
- **Retention Policy:** Permanent. Concepts are modified or refined only through long-term reinforcement learning updates.

## 2. Promotion Rules

1. **No Concept Without Evidence:** A pattern cannot be elevated to Concept Memory unless it has been validated in at least 10 unique historical episodes with a success probability $> 60\%$.
2. **Failure Dominance:** If a concept exhibits a sudden drift or consecutive failures ($> 3$ failures in a row), it is demoted back to raw Pattern Memory for re-evaluation.
