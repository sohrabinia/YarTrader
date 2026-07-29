# Active Learning Design

## 1. Overview
The **Research Priority Engine** (`IResearchPriorityEngine`) dynamically calculates what the AI should study next, prioritizing learning efforts based on knowledge gaps and weaknesses.

---

## 2. Priority Metrics
The engine prioritizes:
- **Repeated Failure Patterns**: High failure rates.
- **Unknown Market Conditions**: Insufficient historical samples.
- **Low Confidence Concepts**: Calibrated confidence score is low.
- **Contradictory Behaviors**: Conflict-ridden signatures.
