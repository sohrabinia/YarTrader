# 07. Knowledge Platform

## 1. Overview
The **Intelligence Knowledge Base** indexes facts, observations, and relationships across agents and pipelines structurally without using machine learning.

```
+─────────────────────────────────────────────+
|               Knowledge Graph               |
|                                             |
|    +─────────+   CORRELATES   +─────────+   |
|    |  Asset  |───────────────>|  Asset  |   |
|    +────┬────+                +────┬────+   |
|         │                          │        |
|         │ INGESTS                  │ VALIDATES
|         v                          v        |
|    +─────────+                +─────────+   |
|    |  Metric |                |  Regime |   |
|    +─────────+                +─────────+   |
+─────────────────────────────────────────────+
```

---

## 2. Core Modules

### EvidenceRepository
Stores raw evidence records (`EvidenceRecord`) linked to unique IDs. All payloads are scanned for forbidden keywords to prevent execution leakage.

### KnowledgeGraph
Semantic network of `KnowledgeNodes` (Asset, Metric, Regime, Agent) and `KnowledgeEdges` (`CORRELATES`, `VALIDATES`, `INGESTS`).

### KnowledgeIndex
Maintains tag-based maps enabling fast queries.

### Historical Intelligence Storage
Enables caching of compiled multi-agent reports for long-term trace comparisons.

---

## 3. Cross References
*   [05_AGENT_ARCHITECTURE.md](05_AGENT_ARCHITECTURE.md)
*   [08_DECISION_ENGINE.md](08_DECISION_ENGINE.md)
