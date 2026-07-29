# Anti-Hallucination Controls

## 1. Objective
To prevent common conversational AI failures (fabricating patterns, hiding trading mistakes, overestimating confidence) from corrupting research interactions.

---

## 2. Controls & Verification
- **Evidence Verification Layer**: Blocks any text responses that do not map directly to stored dataclasses in Concept, Pattern, or Experience memories.
- **Failures Visibility**: Losses and mistakes are immutable and must be reported with equivalent priority to successes.
- **Calibrated Unknown State**: Insufficient samples (< 3) must force the system to state that evidence is insufficient.
