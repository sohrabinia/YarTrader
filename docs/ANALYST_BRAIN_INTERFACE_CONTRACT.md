# Analyst Brain Interface Contract

## 1. Allowed / Forbidden Operations
The conversational layer operates under a strict read-only interface contract.

### Allowed
- `READ` (Query Memory records, inspect Concept memories)
- `QUERY` (Inspect active curiosity questions or hypotheses)
- `REPORT` (Expose simulated trade outcomes and judge scores)

### Forbidden
- `MEMORY WRITE` (No modification of events, patterns, or experiences)
- `CONCEPT UPDATE` (No direct modifications of verified concepts)
- `CONFIDENCE UPDATE` (No manual edits to confidence scores)
- `LEARNING MANIPULATION` (No direct modification of loop results)
- `ORDER EXECUTION` (No coupling to live order execution)

---

## 2. Replay Compatibility
The `KnowledgeQueryInterface` is designed to consume historical replay outputs, simulated outcomes, and learning feedback gateway updates seamlessly without requiring future architectural modifications.
