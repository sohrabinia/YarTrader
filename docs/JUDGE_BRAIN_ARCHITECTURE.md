# Judge Brain Architecture

## 1. Overview
The **Independent Judge Brain** (`IJudgeEngine`) acts as an objective, decoupled evaluator.

---

## 2. Evidence & Reasoning Scores
Rather than evaluating decisions based purely on trade profits, the Judge analyzes:
- **Observation Quality**: Did the AI parse the state correctly?
- **Hypothesis Quality**: Was the discovered pattern relation real or accidental?
- **Decision Quality**: Was the action logical based on available evidence?
- **Outcome Quality**: Was success due to structural understanding or luck?

---

## 3. Judge Outputs
- `Decision Quality Score`
- `Evidence Quality Score`
- `Pattern Accuracy Score`
- `Failure Classification`
- `Learning Recommendation`
